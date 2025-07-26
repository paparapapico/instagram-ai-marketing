# scheduler.py - 수정된 백그라운드 스케줄러
import schedule
import time
import sqlite3
import json
from datetime import datetime, timedelta
import logging
import os
import sys

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결"""
    return sqlite3.connect("instagram_marketing.db")

def process_scheduled_posts():
    """예정된 포스트 처리"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 현재 시간 기준으로 처리할 포스트 조회
        now = datetime.now().isoformat()
        cursor.execute('''
            SELECT cs.id, cs.business_id, cs.content_id, c.caption, c.image_url, c.hashtags
            FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            WHERE cs.scheduled_datetime <= ? AND cs.status = 'pending'
        ''', (now,))
        
        pending_posts = cursor.fetchall()
        
        if not pending_posts:
            logger.info("처리할 예정된 포스트가 없습니다.")
            return
        
        # Instagram 포스터 임포트 시도
        try:
            from instagram_auto_poster import InstagramAutoPoster
            poster_system = InstagramAutoPoster()
        except ImportError:
            logger.error("instagram_auto_poster 모듈을 가져올 수 없습니다.")
            return
        
        for post in pending_posts:
            schedule_id, business_id, content_id, caption, image_url, hashtags = post
            
            try:
                # 비즈니스 정보 가져오기
                cursor.execute("SELECT business_name, industry FROM businesses WHERE id = ?", (business_id,))
                business_info = cursor.fetchone()
                
                if business_info:
                    business_data = {
                        'name': business_info[0],
                        'industry': business_info[1],
                        'caption': caption,
                        'image_url': image_url,
                        'hashtags': hashtags
                    }
                    
                    # Instagram에 포스팅 시도
                    logger.info(f"포스팅 시도: 비즈니스 {business_id}, 콘텐츠 {content_id}")
                    post_id = poster_system.post_to_instagram(
                        business_data, 
                        custom_caption=caption,
                        custom_image_url=image_url
                    )
                    
                    if post_id:
                        # 성공적으로 포스팅됨
                        cursor.execute('''
                            UPDATE content_schedule 
                            SET status = 'completed', post_id = ?, completed_at = ?
                            WHERE id = ?
                        ''', (str(post_id), datetime.now().isoformat(), schedule_id))
                        
                        cursor.execute('''
                            UPDATE content 
                            SET status = 'published', published_at = ?
                            WHERE id = ?
                        ''', (datetime.now().isoformat(), content_id))
                        
                        logger.info(f"포스팅 성공: 콘텐츠 {content_id}, 포스트 ID {post_id}")
                    else:
                        # 포스팅 실패
                        cursor.execute('''
                            UPDATE content_schedule 
                            SET status = 'failed', retry_count = retry_count + 1,
                                error_message = 'Instagram posting failed'
                            WHERE id = ?
                        ''', (schedule_id,))
                        
                        logger.error(f"포스팅 실패: 콘텐츠 {content_id}")
                else:
                    logger.error(f"비즈니스 정보 없음: ID {business_id}")
                
            except Exception as e:
                # 개별 포스트 처리 실패
                cursor.execute('''
                    UPDATE content_schedule 
                    SET status = 'failed', retry_count = retry_count + 1,
                        error_message = ?
                    WHERE id = ?
                ''', (str(e), schedule_id))
                
                logger.error(f"포스트 처리 오류 {content_id}: {str(e)}")
        
        conn.commit()
        logger.info(f"처리 완료: {len(pending_posts)}개 포스트")
            
    except Exception as e:
        logger.error(f"process_scheduled_posts 오류: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def generate_daily_content():
    """일일 콘텐츠 자동 생성"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 활성 비즈니스 목록 조회
        cursor.execute('''
            SELECT b.id, b.business_name, b.industry, b.target_audience, b.brand_voice
            FROM businesses b
            JOIN users u ON b.user_id = u.id
            WHERE u.is_active = 1
        ''')
        
        businesses = cursor.fetchall()
        
        if not businesses:
            logger.info("활성 비즈니스가 없습니다.")
            return
        
        # Instagram 포스터 임포트
        try:
            from instagram_auto_poster import InstagramAutoPoster
            poster_system = InstagramAutoPoster()
        except ImportError:
            logger.error("instagram_auto_poster 모듈을 가져올 수 없습니다.")
            return
        
        for business in businesses:
            business_id, name, industry, target_audience, brand_voice = business
            
            # 오늘 생성된 콘텐츠가 있는지 확인
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM content 
                WHERE business_id = ? AND DATE(created_at) = ?
            ''', (business_id, today))
            
            today_content_count = cursor.fetchone()[0]
            
            # 하루에 최대 3개까지만 자동 생성
            if today_content_count < 3:
                try:
                    business_info = {
                        'name': name,
                        'industry': industry,
                        'target_audience': target_audience or '',
                        'brand_voice': brand_voice or ''
                    }
                    
                    # AI 콘텐츠 생성
                    content = poster_system.generate_content_with_ai(business_info)
                    image_url = poster_system.generate_image_with_dalle(f"{industry} marketing content")
                    
                    # 데이터베이스에 저장
                    cursor.execute('''
                        INSERT INTO content (
                            business_id, title, caption, hashtags, image_url, 
                            content_type, platform, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        business_id, f"Auto-generated content for {name}",
                        content['caption'], json.dumps(content.get('hashtags', [])), 
                        image_url, 'post', 'instagram', 'draft',
                        datetime.now().isoformat()
                    ))
                    
                    logger.info(f"일일 콘텐츠 생성 완료: 비즈니스 {business_id}")
                    
                except Exception as e:
                    logger.error(f"콘텐츠 생성 오류 (비즈니스 {business_id}): {str(e)}")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"generate_daily_content 오류: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def cleanup_old_data():
    """오래된 데이터 정리"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 30일 이상 된 완료된 스케줄 삭제
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('''
            DELETE FROM content_schedule 
            WHERE status = 'completed' AND completed_at < ?
        ''', (cutoff_date,))
        
        deleted_schedules = cursor.rowcount
        
        # 90일 이상 된 비활성 세션 삭제
        session_cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        cursor.execute('''
            DELETE FROM user_sessions 
            WHERE is_active = 0 AND created_at < ?
        ''', (session_cutoff,))
        
        deleted_sessions = cursor.rowcount
        
        conn.commit()
        
        if deleted_schedules > 0 or deleted_sessions > 0:
            logger.info(f"데이터 정리 완료: 스케줄 {deleted_schedules}개, 세션 {deleted_sessions}개 삭제")
        
    except Exception as e:
        logger.error(f"cleanup_old_data 오류: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def update_analytics():
    """분석 데이터 업데이트"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 각 비즈니스의 오늘 분석 데이터 생성/업데이트
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("SELECT id FROM businesses")
        businesses = cursor.fetchall()
        
        for (business_id,) in businesses:
            # 오늘 분석 데이터가 있는지 확인
            cursor.execute('''
                SELECT id FROM analytics 
                WHERE business_id = ? AND date = ?
            ''', (business_id, today))
            
            existing = cursor.fetchone()
            
            # 실제 데이터 기반 분석 (Instagram API 연동 시 사용)
            # 현재는 가상 데이터 생성
            import random
            followers = random.randint(1000, 10000)
            engagement_rate = round(random.uniform(2.0, 8.0), 2)
            reach = random.randint(500, 5000)
            impressions = random.randint(1000, 15000)
            likes = random.randint(50, 500)
            comments = random.randint(5, 50)
            
            if existing:
                # 업데이트
                cursor.execute('''
                    UPDATE analytics 
                    SET followers_count = ?, engagement_rate = ?, 
                        reach = ?, impressions = ?, likes = ?, comments = ?
                    WHERE business_id = ? AND date = ?
                ''', (followers, engagement_rate, reach, impressions, 
                      likes, comments, business_id, today))
            else:
                # 새로 생성
                cursor.execute('''
                    INSERT INTO analytics (
                        business_id, date, followers_count, engagement_rate,
                        reach, impressions, likes, comments, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (business_id, today, followers, engagement_rate, 
                      reach, impressions, likes, comments, 
                      datetime.now().isoformat()))
        
        conn.commit()
        logger.info("분석 데이터 업데이트 완료")
        
    except Exception as e:
        logger.error(f"update_analytics 오류: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def health_check():
    """스케줄러 상태 확인"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 데이터베이스 연결 확인
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        # 오늘 처리된 작업 수 확인
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM content_schedule 
            WHERE DATE(completed_at) = ? AND status = 'completed'
        ''', (today,))
        
        completed_today = cursor.fetchone()[0]
        
        logger.info(f"스케줄러 상태 정상 - 사용자: {user_count}, 오늘 완료: {completed_today}")
        
    except Exception as e:
        logger.error(f"health_check 오류: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def setup_scheduler():
    """스케줄러 설정"""
    try:
        # 매 5분마다 예정된 포스트 확인
        schedule.every(5).minutes.do(process_scheduled_posts)
        
        # 매일 오전 9시에 콘텐츠 자동 생성
        schedule.every().day.at("09:00").do(generate_daily_content)
        
        # 매일 자정에 분석 데이터 업데이트
        schedule.every().day.at("00:00").do(update_analytics)
        
        # 매주 일요일 자정에 데이터 정리
        schedule.every().sunday.at("00:00").do(cleanup_old_data)
        
        # 매시간 상태 확인
        schedule.every().hour.do(health_check)
        
        logger.info("스케줄러 설정 완료")
        
    except Exception as e:
        logger.error(f"스케줄러 설정 오류: {str(e)}")

def main():
    """메인 스케줄러 실행"""
    logger.info("🚀 Instagram Marketing Scheduler 시작")
    
    # 데이터베이스 초기화 확인
    try:
        from database.init_db import init_database
        init_database()
    except ImportError:
        logger.warning("데이터베이스 초기화 모듈을 찾을 수 없습니다.")
    
    # 스케줄러 설정
    setup_scheduler()
    
    # 초기 상태 확인
    health_check()
    
    logger.info("⏰ 스케줄된 작업 실행 중...")
    logger.info("종료하려면 Ctrl+C를 누르세요")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    except KeyboardInterrupt:
        logger.info("🛑 스케줄러가 사용자에 의해 중단되었습니다")
    except Exception as e:
        logger.error(f"스케줄러 실행 중 오류: {str(e)}")
    finally:
        logger.info("스케줄러 종료")

if __name__ == "__main__":
    main()