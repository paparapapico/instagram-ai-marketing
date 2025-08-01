# complete_automation_system.py - 완전한 Instagram 마케팅 자동화 시스템
import sqlite3
import json
import schedule
import time
from datetime import datetime, timedelta
from instagram_auto_poster import InstagramAutoPoster
import logging
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstagramMarketingBusiness:
    def __init__(self):
        self.poster = InstagramAutoPoster()
        self.db_path = "instagram_marketing.db"
        self.init_business_database()
    
    def init_business_database(self):
        """비즈니스 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 비즈니스 설정 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS business_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id INTEGER,
                    auto_post_enabled BOOLEAN DEFAULT TRUE,
                    post_frequency INTEGER DEFAULT 1,
                    preferred_times TEXT DEFAULT '["09:00", "12:00", "18:00"]',
                    content_themes TEXT DEFAULT '["product", "lifestyle", "behind_scenes"]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 콘텐츠 템플릿 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id INTEGER,
                    template_name TEXT,
                    template_type TEXT,
                    template_content TEXT,
                    hashtags TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 성과 추적 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id INTEGER,
                    post_id TEXT,
                    content_type TEXT,
                    posted_at TEXT,
                    likes_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    engagement_rate REAL DEFAULT 0.0,
                    reach INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✅ 비즈니스 데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {e}")
        finally:
            conn.close()
    
    def setup_business_automation(self, user_id, business_data):
        """비즈니스 자동화 설정"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 비즈니스 ID 가져오기
            cursor.execute("SELECT id FROM businesses WHERE user_id = ?", (user_id,))
            business_result = cursor.fetchone()
            
            if not business_result:
                logger.error(f"사용자 {user_id}의 비즈니스를 찾을 수 없습니다.")
                return False
            
            business_id = business_result[0]
            
            # 자동화 설정 저장
            cursor.execute("""
                INSERT OR REPLACE INTO business_settings 
                (business_id, auto_post_enabled, post_frequency, preferred_times, content_themes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                business_id,
                business_data.get('auto_post_enabled', True),
                business_data.get('post_frequency', 1),
                json.dumps(business_data.get('preferred_times', ['09:00', '12:00', '18:00'])),
                json.dumps(business_data.get('content_themes', ['product', 'lifestyle']))
            ))
            
            # 기본 콘텐츠 템플릿 생성
            self._create_default_templates(business_id, business_data)
            
            conn.commit()
            logger.info(f"✅ 비즈니스 {business_id} 자동화 설정 완료")
            return True
            
        except Exception as e:
            logger.error(f"자동화 설정 오류: {e}")
            return False
        finally:
            conn.close()
    
    def _create_default_templates(self, business_id, business_data):
        """기본 콘텐츠 템플릿 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        industry = business_data.get('industry', 'general')
        business_name = business_data.get('name', '우리 비즈니스')
        
        # 업종별 기본 템플릿
        templates = self._get_industry_templates(industry, business_name)
        
        for template in templates:
            cursor.execute("""
                INSERT OR IGNORE INTO content_templates 
                (business_id, template_name, template_type, template_content, hashtags)
                VALUES (?, ?, ?, ?, ?)
            """, (
                business_id,
                template['name'],
                template['type'],
                template['content'],
                json.dumps(template['hashtags'])
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 기본 템플릿 {len(templates)}개 생성 완료")
    
    def _get_industry_templates(self, industry, business_name):
        """업종별 콘텐츠 템플릿 반환"""
        templates = {
            'restaurant': [
                {
                    'name': '메뉴 소개',
                    'type': 'product',
                    'content': f'🍽️ {business_name}의 시그니처 메뉴를 소개합니다! 신선한 재료와 정성으로 만든 특별한 맛을 경험해보세요.',
                    'hashtags': ['#맛집', '#맛스타그램', '#음식', '#메뉴추천', '#restaurant']
                },
                {
                    'name': '분위기 소개',
                    'type': 'lifestyle',
                    'content': f'☕ {business_name}의 아늑하고 편안한 분위기에서 소중한 사람들과 함께 시간을 보내세요.',
                    'hashtags': ['#카페', '#분위기', '#힐링', '#데이트', '#모임']
                },
                {
                    'name': '비하인드 스토리',
                    'type': 'behind_scenes',
                    'content': f'👨‍🍳 {business_name} 셰프의 하루! 매일 새벽부터 신선한 재료 선별과 요리 준비에 정성을 다합니다.',
                    'hashtags': ['#비하인드', '#셰프', '#요리과정', '#정성', '#신선함']
                }
            ],
            'fashion': [
                {
                    'name': '신상품 소개',
                    'type': 'product',
                    'content': f'✨ {business_name}의 신상 컬렉션이 출시되었습니다! 이번 시즌 트렌드를 반영한 스타일리시한 아이템들을 만나보세요.',
                    'hashtags': ['#패션', '#신상품', '#ootd', '#스타일', '#트렌드']
                },
                {
                    'name': '스타일링 팁',
                    'type': 'lifestyle',
                    'content': f'💫 {business_name}이 제안하는 이번 주 스타일링 팁! 기본 아이템으로도 충분히 세련된 룩을 연출할 수 있어요.',
                    'hashtags': ['#스타일링', '#패션팁', '#코디', '#스타일', '#fashion']
                }
            ],
            'beauty': [
                {
                    'name': '제품 소개',
                    'type': 'product',
                    'content': f'💄 {business_name}의 신제품을 소개합니다! 자연 성분으로 만든 건강한 뷰티 아이템으로 더욱 아름다워지세요.',
                    'hashtags': ['#뷰티', '#화장품', '#스킨케어', '#자연성분', '#beauty']
                },
                {
                    'name': '뷰티 팁',
                    'type': 'lifestyle',
                    'content': f'✨ {business_name}이 알려주는 뷰티 꿀팁! 간단한 관리법으로 건강하고 아름다운 피부를 유지하세요.',
                    'hashtags': ['#뷰티팁', '#스킨케어', '#피부관리', '#뷰티', '#건강']
                }
            ]
        }
        
        return templates.get(industry, [
            {
                'name': '서비스 소개',
                'type': 'product',
                'content': f'🚀 {business_name}의 전문적인 서비스를 경험해보세요! 고객 만족을 위해 최선을 다하겠습니다.',
                'hashtags': ['#비즈니스', '#서비스', '#전문성', '#고객만족', '#quality']
            }
        ])
    
    def generate_automated_content(self, business_id):
        """자동화된 콘텐츠 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 비즈니스 정보 가져오기
            cursor.execute("""
                SELECT b.business_name, b.industry, b.target_audience, b.brand_voice,
                       bs.content_themes, bs.auto_post_enabled
                FROM businesses b
                LEFT JOIN business_settings bs ON b.id = bs.business_id
                WHERE b.id = ?
            """, (business_id,))
            
            result = cursor.fetchone()
            if not result:
                logger.error(f"비즈니스 {business_id}를 찾을 수 없습니다.")
                return None
            
            business_name, industry, target_audience, brand_voice, content_themes_json, auto_enabled = result
            
            if not auto_enabled:
                logger.info(f"비즈니스 {business_id}의 자동 포스팅이 비활성화되어 있습니다.")
                return None
            
            # 콘텐츠 테마 파싱
            try:
                content_themes = json.loads(content_themes_json) if content_themes_json else ['product']
            except:
                content_themes = ['product']
            
            # 비즈니스 정보 구성
            business_info = {
                'name': business_name,
                'industry': industry,
                'target_audience': target_audience or '',
                'brand_voice': brand_voice or '친근하고 전문적인'
            }
            
            # AI로 콘텐츠 생성
            content = self.poster.generate_content_with_ai(business_info)
            
            if content['success']:
                # 이미지 생성
                image_description = f"{industry} {content_themes[0]} marketing content"
                image_url = self.poster.generate_image_with_dalle(image_description)
                
                # 데이터베이스에 저장
                cursor.execute("""
                    INSERT INTO content (
                        business_id, title, caption, hashtags, image_url,
                        content_type, platform, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    business_id, f"Auto-generated content for {business_name}",
                    content['caption'], json.dumps(content['hashtags']),
                    image_url, 'post', 'instagram', 'draft',
                    datetime.now().isoformat()
                ))
                
                content_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"✅ 자동 콘텐츠 생성 완료: 비즈니스 {business_id}, 콘텐츠 {content_id}")
                return {
                    'content_id': content_id,
                    'caption': content['caption'],
                    'image_url': image_url,
                    'hashtags': content['hashtags']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"자동 콘텐츠 생성 오류: {e}")
            return None
        finally:
            conn.close()
    
    def schedule_content_post(self, business_id, content_id, scheduled_time=None):
        """콘텐츠 포스팅 스케줄링"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 스케줄 시간 설정
            if not scheduled_time:
                # 기본 설정된 시간 중 하나 선택
                cursor.execute("""
                    SELECT preferred_times FROM business_settings WHERE business_id = ?
                """, (business_id,))
                
                times_result = cursor.fetchone()
                if times_result and times_result[0]:
                    try:
                        preferred_times = json.loads(times_result[0])
                        import random
                        selected_time = random.choice(preferred_times)
                        
                        # 내일 해당 시간으로 설정
                        tomorrow = datetime.now() + timedelta(days=1)
                        hour, minute = map(int, selected_time.split(':'))
                        scheduled_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    except:
                        # 기본값: 내일 오전 9시
                        scheduled_time = datetime.now() + timedelta(days=1)
                        scheduled_time = scheduled_time.replace(hour=9, minute=0, second=0, microsecond=0)
                else:
                    # 기본값: 내일 오전 9시
                    scheduled_time = datetime.now() + timedelta(days=1)
                    scheduled_time = scheduled_time.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # 스케줄 저장
            cursor.execute("""
                INSERT INTO content_schedule (
                    business_id, content_id, scheduled_datetime, status, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                business_id, content_id, scheduled_time.isoformat(),
                'pending', datetime.now().isoformat()
            ))
            
            conn.commit()
            logger.info(f"✅ 콘텐츠 스케줄링 완료: {scheduled_time}")
            return True
            
        except Exception as e:
            logger.error(f"콘텐츠 스케줄링 오류: {e}")
            return False
        finally:
            conn.close()
    
    def execute_scheduled_posts(self):
        """예정된 포스트 실행"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 현재 시간 기준으로 실행할 포스트 조회
            now = datetime.now().isoformat()
            cursor.execute("""
                SELECT cs.id, cs.business_id, cs.content_id, c.caption, c.image_url, c.hashtags,
                       b.business_name, b.industry
                FROM content_schedule cs
                JOIN content c ON cs.content_id = c.id
                JOIN businesses b ON cs.business_id = b.id
                WHERE cs.scheduled_datetime <= ? AND cs.status = 'pending'
                ORDER BY cs.scheduled_datetime ASC
            """, (now,))
            
            pending_posts = cursor.fetchall()
            
            for post in pending_posts:
                schedule_id, business_id, content_id, caption, image_url, hashtags, business_name, industry = post
                
                try:
                    business_info = {
                        'name': business_name,
                        'industry': industry
                    }
                    
                    # Instagram에 포스팅
                    post_id = self.poster.post_to_instagram(
                        business_info,
                        custom_caption=caption,
                        custom_image_url=image_url
                    )
                    
                    if post_id:
                        # 성공 처리
                        cursor.execute("""
                            UPDATE content_schedule 
                            SET status = 'completed', post_id = ?, completed_at = ?
                            WHERE id = ?
                        """, (str(post_id), datetime.now().isoformat(), schedule_id))
                        
                        cursor.execute("""
                            UPDATE content 
                            SET status = 'published', published_at = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), content_id))
                        
                        # 성과 추적 레코드 생성
                        cursor.execute("""
                            INSERT INTO performance_tracking (
                                business_id, post_id, content_type, posted_at
                            ) VALUES (?, ?, ?, ?)
                        """, (business_id, str(post_id), 'post', datetime.now().isoformat()))
                        
                        logger.info(f"✅ 포스팅 성공: 비즈니스 {business_id}, 포스트 {post_id}")
                    else:
                        # 실패 처리
                        cursor.execute("""
                            UPDATE content_schedule 
                            SET status = 'failed', retry_count = retry_count + 1,
                                error_message = 'Instagram posting failed'
                            WHERE id = ?
                        """, (schedule_id,))
                        
                        logger.error(f"❌ 포스팅 실패: 비즈니스 {business_id}, 콘텐츠 {content_id}")
                
                except Exception as e:
                    # 개별 포스트 오류 처리
                    cursor.execute("""
                        UPDATE content_schedule 
                        SET status = 'failed', retry_count = retry_count + 1,
                            error_message = ?
                        WHERE id = ?
                    """, (str(e), schedule_id))
                    
                    logger.error(f"포스트 처리 오류: {e}")
            
            conn.commit()
            logger.info(f"스케줄된 포스트 처리 완료: {len(pending_posts)}개")
            
        except Exception as e:
            logger.error(f"스케줄된 포스트 실행 오류: {e}")
        finally:
            conn.close()
    
    def analyze_performance(self, business_id, days=7):
        """성과 분석"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 최근 N일간 성과 데이터 조회
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_posts,
                    AVG(likes_count) as avg_likes,
                    AVG(comments_count) as avg_comments,
                    AVG(engagement_rate) as avg_engagement,
                    SUM(reach) as total_reach,
                    SUM(impressions) as total_impressions
                FROM performance_tracking 
                WHERE business_id = ? AND posted_at >= ?
            """, (business_id, cutoff_date))
            
            result = cursor.fetchone()
            
            if result:
                total_posts, avg_likes, avg_comments, avg_engagement, total_reach, total_impressions = result
                
                analysis = {
                    'period_days': days,
                    'total_posts': total_posts or 0,
                    'avg_likes': round(avg_likes or 0, 1),
                    'avg_comments': round(avg_comments or 0, 1),
                    'avg_engagement_rate': round(avg_engagement or 0, 2),
                    'total_reach': total_reach or 0,
                    'total_impressions': total_impressions or 0,
                    'analysis_date': datetime.now().isoformat()
                }
                
                logger.info(f"✅ 성과 분석 완료: 비즈니스 {business_id}")
                return analysis
            
            return None
            
        except Exception as e:
            logger.error(f"성과 분석 오류: {e}")
            return None
        finally:
            conn.close()
    
    def get_content_suggestions(self, business_id):
        """콘텐츠 제안"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 비즈니스 정보 및 성과 데이터 기반으로 제안 생성
            cursor.execute("""
                SELECT b.industry, b.target_audience, 
                       AVG(pt.engagement_rate) as avg_engagement
                FROM businesses b
                LEFT JOIN performance_tracking pt ON b.id = pt.business_id
                WHERE b.id = ?
                GROUP BY b.id
            """, (business_id,))
            
            result = cursor.fetchone()
            if not result:
                return []
            
            industry, target_audience, avg_engagement = result
            
            # 업종별 콘텐츠 제안
            suggestions = self._generate_content_suggestions(industry, target_audience, avg_engagement)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"콘텐츠 제안 생성 오류: {e}")
            return []
        finally:
            conn.close()
    
    def _generate_content_suggestions(self, industry, target_audience, avg_engagement):
        """업종별 콘텐츠 제안 생성"""
        base_suggestions = [
            "고객 후기 및 리뷰 공유",
            "비하인드 스토리 콘텐츠",
            "시즌별 프로모션 안내",
            "팀원 소개 및 전문성 어필",
            "업계 트렌드 및 팁 공유"
        ]
        
        industry_specific = {
            'restaurant': [
                "오늘의 메뉴 소개",
                "요리 과정 타임랩스",
                "재료 스토리 및 원산지 소개",
                "셰프 추천 메뉴",
                "계절별 특선 요리"
            ],
            'fashion': [
                "신상품 스타일링 제안",
                "패션 트렌드 분석",
                "고객 스타일링 사례",
                "계절별 코디 팁",
                "브랜드 스토리 공유"
            ],
            'beauty': [
                "제품 사용법 튜토리얼",
                "뷰티 팁 및 노하우",
                "고객 변신 스토리",
                "성분 및 효능 소개",
                "시즌별 스킨케어 루틴"
            ]
        }
        
        suggestions = base_suggestions + industry_specific.get(industry, [])
        
        # 참여율 기반 우선순위 조정
        if avg_engagement and avg_engagement > 0.05:  # 5% 이상
            suggestions.insert(0, "높은 참여율 콘텐츠 유형 분석 및 확장")
        
        return suggestions[:8]  # 최대 8개 제안
    
    def run_daily_automation(self):
        """일일 자동화 작업 실행"""
        logger.info("🚀 일일 자동화 작업 시작")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 활성화된 자동 포스팅 비즈니스 조회
            cursor.execute("""
                SELECT b.id, b.business_name
                FROM businesses b
                JOIN business_settings bs ON b.id = bs.business_id
                JOIN users u ON b.user_id = u.id
                WHERE bs.auto_post_enabled = TRUE AND u.is_active = TRUE
            """)
            
            active_businesses = cursor.fetchall()
            
            for business_id, business_name in active_businesses:
                try:
                    # 오늘 생성된 콘텐츠 수 확인
                    today = datetime.now().strftime('%Y-%m-%d')
                    cursor.execute("""
                        SELECT COUNT(*) FROM content 
                        WHERE business_id = ? AND DATE(created_at) = ?
                    """, (business_id, today))
                    
                    today_content_count = cursor.fetchone()[0]
                    
                    # 설정된 빈도만큼 콘텐츠 생성
                    cursor.execute("""
                        SELECT post_frequency FROM business_settings WHERE business_id = ?
                    """, (business_id,))
                    
                    frequency_result = cursor.fetchone()
                    target_frequency = frequency_result[0] if frequency_result else 1
                    
                    if today_content_count < target_frequency:
                        # 자동 콘텐츠 생성
                        content_result = self.generate_automated_content(business_id)
                        
                        if content_result:
                            # 스케줄링
                            self.schedule_content_post(business_id, content_result['content_id'])
                            logger.info(f"✅ {business_name}: 콘텐츠 생성 및 스케줄링 완료")
                        else:
                            logger.warning(f"⚠️ {business_name}: 콘텐츠 생성 실패")
                    else:
                        logger.info(f"ℹ️ {business_name}: 오늘 목표 콘텐츠 수 달성")
                
                except Exception as e:
                    logger.error(f"비즈니스 {business_name} 처리 오류: {e}")
            
            conn.close()
            
            # 스케줄된 포스트 실행
            self.execute_scheduled_posts()
            
            logger.info("✅ 일일 자동화 작업 완료")
            
        except Exception as e:
            logger.error(f"일일 자동화 작업 오류: {e}")

# 스케줄러 설정
def setup_automation_scheduler():
    """자동화 스케줄러 설정"""
    automation = InstagramMarketingBusiness()
    
    # 매일 오전 9시에 일일 자동화 실행
    schedule.every().day.at("09:00").do(automation.run_daily_automation)
    
    # 매시간 스케줄된 포스트 확인
    schedule.every().hour.do(automation.execute_scheduled_posts)
    
    logger.info("✅ 자동화 스케줄러 설정 완료")
    
    return automation

# 메인 실행 함수
def main():
    """메인 자동화 시스템 실행"""
    automation = setup_automation_scheduler()
    
    logger.info("🚀 Instagram 마케팅 자동화 시스템 시작")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    except KeyboardInterrupt:
        logger.info("🛑 자동화 시스템 중단")

if __name__ == "__main__":
    main()