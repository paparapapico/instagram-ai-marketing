# scheduler.py - 백그라운드 작업 스케줄러

import schedule
import time
import sqlite3
import asyncio
from datetime import datetime, timedelta
import logging
from complete_automation_system import InstagramMarketingBusiness
from instagram_auto_poster import InstagramAutoPoster

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 시스템 초기화
business_system = InstagramMarketingBusiness()
poster_system = InstagramAutoPoster()

def process_scheduled_posts():
    """예정된 포스트 처리"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
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
                    
                    # Instagram에 포스팅
                    post_id = poster_system.post_to_instagram(business_data)
                    
                    if post_id:
                        # 성공적으로 포스팅됨
                        cursor.execute('''
                            UPDATE content_schedule 
                            SET status = 'completed', post_id = ?, completed_at = ?
                            WHERE id = ?
                        ''', (post_id, datetime.now().isoformat(), schedule_id))
                        
                        cursor.execute('''
                            UPDATE content 
                            SET status = 'published', published_at = ?
                            WHERE id = ?
                        ''', (datetime.now().isoformat(), content_id))
                        
                        logger.info(f"Successfully posted content {content_id} for business {business_id}")
                    else:
                        # 포스팅 실패
                        cursor.execute('''
                            UPDATE content_schedule 
                            SET status = 'failed', retry_count = retry_count + 1,
                                error_message = 'Instagram posting failed'
                            WHERE id = ?
                        ''', (schedule_id,))
                        
                        logger.error(f"Failed to post content {content_id} for business {business_id}")
                
            except Exception as e:
                # 개별 포스트 처리 실패
                cursor.execute('''
                    UPDATE content_schedule 
                    SET status = 'failed', retry_count = retry_count + 1,
                        error_message = ?
                    WHERE id = ?
                ''', (str(e), schedule_id))
                
                logger.error(f"Error processing post {content_id}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        if pending_posts:
            logger.info(f"Processed {len(pending_posts)} scheduled posts")
            
    except Exception as e:
        logger.error(f"Error in process_scheduled_posts: {str(e)}")

def generate_daily_content():
    """일일 콘텐츠 자동 생성"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 활성 비즈니스 목록 조회
        cursor.execute('''
            SELECT b.id, b.business_name, b.industry, b.target_audience, b.brand_voice
            FROM businesses b
            JOIN users u ON b.user_id = u.id
            WHERE u.is_active = TRUE
        ''')
        
        businesses = cursor.fetchall()
        
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
                business_info = {
                    'name': name,
                    'industry': industry,
                    'target_audience': target_audience,
                    'brand_voice': brand_voice
                }
                
                # AI 콘텐츠 생성
                content = poster_system.generate_content_with_ai(business_info)
                image_url = poster_system.generate_image_with_dalle(f"{industry} marketing content")
                
                # 데이터베이스에 저장
                cursor.execute('''
                    INSERT INTO content (
                        business_id, title, caption, hashtags, image_url, 
                        content_type, platform, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    business_id, f"Auto-generated content for {name}",
                    content['caption'], json.dumps(content['hashtags']), 
                    image_url, 'post', 'instagram', 'draft'
                ))
                
                logger.info(f"Generated daily content for business {business_id}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in generate_daily_content: {str(e)}")

def cleanup_old_data():
    """오래된 데이터 정리"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 30일 이상 된 완료된 스케줄 삭제
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('''
            DELETE FROM content_schedule 
            WHERE status = 'completed' AND completed_at < ?
        ''', (cutoff_date,))
        
        # 90일 이상 된 비활성 세션 삭제
        session_cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        cursor.execute('''
            DELETE FROM user_sessions 
            WHERE is_active = FALSE AND created_at < ?
        ''', (session_cutoff,))
        
        conn.commit()
        conn.close()
        
        logger.info("Completed data cleanup")
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {str(e)}")

def update_analytics():
    """분석 데이터 업데이트"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
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
            
            # 가상 분석 데이터 생성 (실제로는 Instagram API에서 가져옴)
            import random
            followers = random.randint(1000, 10000)
            engagement_rate = round(random.uniform(2.0, 8.0), 2)
            reach = random.randint(500, 5000)
            impressions = random.randint(1000, 15000)
            
            if existing:
                # 업데이트
                cursor.execute('''
                    UPDATE analytics 
                    SET followers_count = ?, engagement_rate = ?, 
                        reach = ?, impressions = ?
                    WHERE business_id = ? AND date = ?
                ''', (followers, engagement_rate, reach, impressions, business_id, today))
            else:
                # 새로 생성
                cursor.execute('''
                    INSERT INTO analytics (
                        business_id, date, followers_count, engagement_rate,
                        reach, impressions
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (business_id, today, followers, engagement_rate, reach, impressions))
        
        conn.commit()
        conn.close()
        
        logger.info("Updated analytics data")
        
    except Exception as e:
        logger.error(f"Error in update_analytics: {str(e)}")

# 스케줄 설정
def setup_scheduler():
    """스케줄러 설정"""
    # 매 5분마다 예정된 포스트 확인
    schedule.every(5).minutes.do(process_scheduled_posts)
    
    # 매일 오전 9시에 콘텐츠 자동 생성
    schedule.every().day.at("09:00").do(generate_daily_content)
    
    # 매일 자정에 분석 데이터 업데이트
    schedule.every().day.at("00:00").do(update_analytics)
    
    # 매주 일요일 자정에 데이터 정리
    schedule.every().sunday.at("00:00").do(cleanup_old_data)
    
    logger.info("Scheduler setup completed")

def main():
    """메인 스케줄러 실행"""
    setup_scheduler()
    
    logger.info("🚀 Instagram Marketing Scheduler Started")
    logger.info("⏰ Running scheduled tasks...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    main()
