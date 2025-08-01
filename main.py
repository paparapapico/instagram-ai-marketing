# main.py - 대기업 스타일로 개선된 버전
from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import hashlib
import secrets
import os
import sqlite3
from datetime import datetime, timedelta
import uvicorn
import json
from typing import Optional, Dict, Any, List
import requests
import asyncio
import logging
import openai
import jwt
import random
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ 환경변수 로드 완료")
except:
    print("⚠️ dotenv 없음")

# 설정
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', 8000))

# JWT 설정
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-this-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# 보안 설정
security = HTTPBearer(auto_error=False)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 요청 모델들
class UserCreate(BaseModel):
    email: str
    password: str
    business_name: str
    industry: str

class UserLogin(BaseModel):
    email: str
    password: str

class ContentRequest(BaseModel):
    business_name: str
    industry: str
    target_audience: str = "일반 고객"
    brand_voice: str = "친근하고 전문적인"

class InstagramPostRequest(BaseModel):
    caption: str
    image_url: Optional[str] = None

# 비밀번호 해싱 함수들
def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{password_hash.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호 검증"""
    try:
        salt, hash_value = password_hash.split(':')
        password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_value == password_hash_check.hex()
    except:
        return False

# JWT 토큰 관리
def create_access_token(user_id: int, email: str) -> str:
    """JWT 액세스 토큰 생성"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

# 현재 사용자 가져오기
async def get_current_user(request: Request) -> Optional[dict]:
    """현재 로그인한 사용자 정보 가져오기"""
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    payload = verify_token(token)
    if not payload:
        return None
    
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, business_name, industry, created_at 
            FROM users 
            WHERE id = ? AND is_active = TRUE
        """, (payload["user_id"],))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                "id": user_data[0],
                "email": user_data[1],
                "business_name": user_data[2],
                "industry": user_data[3],
                "created_at": user_data[4]
            }
    except Exception as e:
        logger.error(f"사용자 조회 오류: {e}")
    
    return None

# 로그인 필수 의존성
async def require_auth(request: Request) -> dict:
    """로그인이 필요한 엔드포인트용 의존성"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return user

# 데이터베이스 초기화
def init_db():
    """데이터베이스 초기화"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 사용자 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                business_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # 생성된 콘텐츠 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_content (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                business_name TEXT,
                industry TEXT,
                caption TEXT,
                hashtags TEXT,
                image_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                posted_to_instagram BOOLEAN DEFAULT FALSE,
                post_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Instagram 포스팅 기록
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instagram_posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                business_name TEXT,
                caption TEXT,
                image_url TEXT,
                post_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                posted_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ 데이터베이스 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"❌ DB 초기화 오류: {e}")
        return False

# Instagram 서비스 클래스
class InstagramService:
    def __init__(self):
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.base_url = "https://graph.facebook.com"
        self.api_version = "v18.0"
        
    def validate_credentials(self) -> bool:
        """인증 정보 유효성 검사"""
        if not self.access_token or not self.business_account_id:
            logger.error("Instagram 인증 정보가 설정되지 않았습니다.")
            return False
        return True
    
    async def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        """미디어 컨테이너 생성"""
        if not self.validate_credentials():
            return None
            
        url = f"{self.base_url}/{self.api_version}/{self.business_account_id}/media"
        
        # 디버깅: 요청 정보 출력
        logger.info(f"📱 Instagram API 호출:")
        logger.info(f"  - URL: {url}")
        logger.info(f"  - Business Account ID: {self.business_account_id}")
        logger.info(f"  - Access Token (처음 20자): {self.access_token[:20] if self.access_token else 'None'}...")
        logger.info(f"  - Access Token 길이: {len(self.access_token) if self.access_token else 0}")
        
        params = {
            'image_url': image_url,
            'caption': caption[:2200],  # Instagram 캡션 길이 제한
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, data=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 미디어 컨테이너 생성 성공: {data.get('id')}")
                return data.get('id')
            else:
                logger.error(f"❌ 미디어 컨테이너 생성 실패: {response.json()}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 미디어 컨테이너 생성 오류: {e}")
            return None
    
    async def publish_media(self, creation_id: str) -> bool:
        """미디어 발행"""
        if not self.validate_credentials():
            return False
            
        url = f"{self.base_url}/{self.api_version}/{self.business_account_id}/media_publish"
        
        params = {
            'creation_id': creation_id,
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(url, data=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"🎉 미디어 발행 성공! Post ID: {data.get('id')}")
                return True
            else:
                logger.error(f"❌ 미디어 발행 실패: {response.json()}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 미디어 발행 오류: {e}")
            return False

# 콘텐츠 생성 시스템
class AIContentGenerator:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY')
        
        # 2025년 최신 트렌드 및 밈
        self.trend_keywords = {
            'restaurant': ['맛도리', '존맛탱', '핫플', '웨이팅', 'JMT', '맛집투어', '찐맛집', '로컬맛집', '숨은맛집'],
            'fashion': ['코디', 'OOTD', '룩북', '하울', '데일리룩', '캐주얼', '스트릿', '미니멀', 'Y2K'],
            'beauty': ['글로우', '속광', '톤업', '꿀피부', '데일리', '겟레디윗미', 'GRWM', '화장품추천', '신상템'],
            'fitness': ['오운완', '헬린이', '벌크업', '다이어트', '홈트', '바디프로필', '운동인증', '헬스타그램']
        }
        
        # 최신 이모지 스타일
        self.emoji_sets = {
            'restaurant': ['🍽️', '🥘', '😋', '🤤', '👨‍🍳', '🔥', '✨', '💯', '🎉', '📍'],
            'fashion': ['👗', '👠', '👜', '💄', '✨', '🛍️', '💫', '🌟', '💖', '🔥'],
            'beauty': ['💄', '✨', '🌸', '💕', '🌟', '💫', '🦋', '🌺', '💖', '🎀'],
            'fitness': ['💪', '🏃‍♀️', '🔥', '💯', '⚡', '🎯', '💦', '🏋️‍♀️', '📈', '✅']
        }
        
    async def generate_content(self, business_info: Dict) -> Dict:
        """AI 콘텐츠 생성 - 트렌디하고 실제적인 버전"""
        try:
            # 더 스마트한 프롬프트 생성
            prompt = self._create_trendy_prompt(business_info)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # 더 나은 모델 사용 (가능하면)
                messages=[
                    {
                        "role": "system", 
                        "content": """당신은 2025년 한국 인스타그램 마케팅 전문가입니다. 
                        MZ세대의 언어와 최신 트렌드를 완벽하게 이해하고 있으며, 
                        실제로 인기를 끌 수 있는 콘텐츠를 작성합니다.
                        자연스럽고 친근한 말투로 작성하되, 과하지 않게 적절히 트렌디한 표현을 사용합니다."""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.9  # 더 창의적인 결과
            )
            
            content_text = response.choices[0].message.content.strip()
            
            # JSON 파싱
            try:
                content_data = json.loads(content_text)
            except:
                # 파싱 실패시 재시도
                content_data = self._parse_content_fallback(content_text, business_info)
            
            # 업종에 맞는 실제 이미지 검색
            image_url = await self._get_trendy_image(business_info)
            
            # 시간대별 해시태그 추가
            time_hashtags = self._get_time_based_hashtags()
            all_hashtags = content_data.get('hashtags', []) + time_hashtags
            
            return {
                'caption': content_data.get('caption', ''),
                'hashtags': all_hashtags[:15],  # 최대 15개
                'image_url': image_url,
                'full_caption': f"{content_data.get('caption', '')}\n\n{' '.join(all_hashtags[:15])}",
                'engagement_tip': content_data.get('engagement_tip', '')
            }
            
        except Exception as e:
            logger.error(f"콘텐츠 생성 오류: {e}")
            return self._get_trendy_fallback_content(business_info)
    
    def _create_trendy_prompt(self, business_info: Dict) -> str:
        """트렌디한 프롬프트 생성"""
        industry = business_info['industry']
        trends = self.trend_keywords.get(industry, [])
        current_month = datetime.now().strftime("%m월")
        
        return f"""
비즈니스: {business_info['business_name']}
업종: {industry}
타겟: {business_info.get('target_audience', '20-30대 MZ세대')}
현재: {current_month}

다음 요구사항에 맞춰 인스타그램 콘텐츠를 생성해주세요:

1. 2025년 최신 인스타그램 트렌드를 반영할 것
2. 실제로 사람들이 좋아요와 댓글을 남길만한 내용
3. 자연스럽고 친근한 한국어 (과하지 않게)
4. 업종 관련 트렌드 키워드 활용: {', '.join(trends)}
5. 적절한 이모지 사용 (2-4개)
6. CTA(Call to Action) 포함

JSON 형식으로 응답:
{{
    "caption": "매력적이고 트렌디한 캡션 (100-150자, 줄바꿈 포함)",
    "hashtags": ["트렌디한_해시태그1", "해시태그2", ...] (10-12개),
    "engagement_tip": "참여 유도 문구"
}}

예시 스타일:
- "오늘 점심 뭐 드셨나요? 🤔"
- "이거 실화냐... 진짜 맛있음 ㅠㅠ"
- "요즘 핫한 OO 다녀왔는데"
- "솔직 후기) OO 써본 썰.txt"
"""
    
    async def _get_trendy_image(self, business_info: Dict) -> str:
        """업종별 트렌디한 이미지 검색"""
        industry = business_info['industry']
        
        # 업종별 구체적인 검색 키워드
        search_queries = {
            'restaurant': [
                f"korean {business_info['business_name']} food aesthetic",
                "instagram worthy cafe food",
                "trendy restaurant interior 2025",
                "korean food photography",
                "seoul cafe aesthetic"
            ],
            'fashion': [
                "korean fashion street style 2025",
                "seoul fashion week street",
                "k-fashion outfit aesthetic",
                "trendy korean fashion store",
                "minimalist fashion photography"
            ],
            'beauty': [
                "korean beauty products aesthetic",
                "k-beauty skincare flatlay",
                "seoul beauty store interior",
                "glass skin makeup result",
                "korean cosmetics photography"
            ],
            'fitness': [
                "modern gym interior design",
                "fitness motivation aesthetic",
                "korean gym equipment",
                "workout results transformation",
                "seoul fitness studio"
            ]
        }
        
        if self.unsplash_key:
            try:
                # 여러 쿼리 중 랜덤 선택
                query = random.choice(search_queries.get(industry, ["lifestyle"]))
                
                response = requests.get(
                    "https://api.unsplash.com/search/photos",
                    params={
                        'query': query,
                        'per_page': 30,
                        'orientation': 'square',
                        'client_id': self.unsplash_key,
                        'order_by': 'relevant'
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['results']:
                        # 상위 5개 중 랜덤 선택 (다양성)
                        top_results = data['results'][:5]
                        selected = random.choice(top_results)
                        return selected['urls']['regular']
            except Exception as e:
                logger.error(f"이미지 검색 오류: {e}")
        
        # Pexels API 폴백 (무료)
        return self._get_pexels_image(industry, business_info)
    
    def _get_pexels_image(self, industry: str, business_info: Dict) -> str:
        """Pexels API를 통한 이미지 검색 (폴백)"""
        # 실제로는 Pexels API 키가 필요하지만, 데모용 고품질 이미지 URL 반환
        quality_images = {
            'restaurant': [
                "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=1024&q=80"
            ],
            'fashion': [
                "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1024&q=80"
            ],
            'beauty': [
                "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1596462502278-27bfdc403348?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?auto=format&fit=crop&w=1024&q=80"
            ],
            'fitness': [
                "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1024&q=80",
                "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=1024&q=80"
            ]
        }
        
        return random.choice(quality_images.get(industry, quality_images['restaurant']))
    
    def _get_time_based_hashtags(self) -> List[str]:
        """시간대별 해시태그"""
        hour = datetime.now().hour
        day_of_week = datetime.now().strftime("%A")
        
        time_tags = []
        
        # 시간대별
        if 6 <= hour < 10:
            time_tags.extend(['#굿모닝', '#아침스타그램', '#모닝루틴'])
        elif 11 <= hour < 14:
            time_tags.extend(['#점심스타그램', '#런치타임', '#점심뭐먹지'])
        elif 17 <= hour < 20:
            time_tags.extend(['#퇴근', '#저녁스타그램', '#오늘하루'])
        elif 21 <= hour < 24:
            time_tags.extend(['#밤스타그램', '#불금', '#힐링타임'])
        
        # 요일별
        if day_of_week in ['Friday', 'Saturday']:
            time_tags.extend(['#불금', '#주말', '#주말스타그램'])
        elif day_of_week == 'Monday':
            time_tags.extend(['#월요병', '#한주시작', '#월요일'])
        
        return time_tags
    
    def _get_trendy_fallback_content(self, business_info: Dict) -> Dict:
        """트렌디한 폴백 콘텐츠"""
        industry = business_info['industry']
        business_name = business_info['business_name']
        emojis = self.emoji_sets.get(industry, ['✨'])
        
        trendy_templates = {
            'restaurant': [
                f"{random.choice(emojis)} 요즘 {business_name} 안 가본 사람 있나요?\n진짜 맛도리 맛집인데... 🤤\n\n특히 시그니처 메뉴는 꼭 드셔보세요!\n(스토리에 더 많은 사진 있어요 📸)",
                f"오늘 점메추 해결! {random.choice(emojis)}\n\n{business_name}에서 JMT 발견...\n이거 실화냐 진짜 너무 맛있음 ㅠㅠ\n\n💬 댓글로 메뉴 추천 받아요!",
                f"📍 {business_name}\n\n요즘 핫한 맛집 다녀왔는데\n분위기도 미쳤고 맛도 미쳤음... {random.choice(emojis)}\n\n웨이팅 있지만 기다릴 가치 충분!"
            ],
            'fashion': [
                f"오늘의 #OOTD {random.choice(emojis)}\n\n{business_name}에서 득템한 아이템으로\n데일리룩 완성! 💫\n\n사이즈 문의는 DM 주세요 🛍️",
                f"신상 입고 소식! {random.choice(emojis)}\n\n{business_name} 이번 컬렉션\n진짜 예쁜 거 너무 많아요... 💖\n\n✔️ 온라인 주문 가능\n✔️ 당일 발송",
                f"룩북 촬영 비하인드 📸\n\n{business_name} 새로운 시즌 준비중!\n미리보기로 보여드려요 {random.choice(emojis)}\n\n어떤 스타일이 제일 예쁜가요?"
            ],
            'beauty': [
                f"#광고 #협찬\n\n{business_name} 신제품 써봤는데 {random.choice(emojis)}\n속광 피부 만들기 대성공... ✨\n\n지금 할인 중이래요! (링크는 프로필에)",
                f"요즘 피부 좋아졌다는 말 많이 듣는데 {random.choice(emojis)}\n\n비결은 {business_name} 제품!\n#GRWM 영상은 릴스에 있어요 💕",
                f"솔직 후기) {business_name} 제품 한달 사용 {random.choice(emojis)}\n\n✅ 장점: 순하고 효과 좋음\n✅ 단점: 너무 빨리 떨어짐 ㅠㅠ\n\n결론: 재구매 의사 100%"
            ],
            'fitness': [
                f"#오운완 {random.choice(emojis)}\n\n{business_name}에서 PT 받는 중!\n확실히 전문가한테 배우니까 다르네요 💪\n\n💬 운동 루틴 궁금하면 댓글 남겨주세요",
                f"3개월 전 vs 오늘 {random.choice(emojis)}\n\n{business_name} 다닌 결과...\n진짜 인생이 바뀜 💯\n\n✔️ 체지방 -5kg\n✔️ 근육량 +3kg",
                f"헬린이 탈출 성공! 🎉\n\n{business_name} 트레이너님들\n진짜 너무 친절하고 전문적이에요 {random.choice(emojis)}\n\n무료 상담 받아보세요! (DM 문의)"
            ]
        }
        
        caption = random.choice(trendy_templates.get(industry, trendy_templates['restaurant']))
        hashtags = self._get_default_trendy_hashtags(industry)
        
        return {
            'caption': caption,
            'hashtags': hashtags,
            'image_url': self._get_pexels_image(industry, business_info),
            'full_caption': f"{caption}\n\n{' '.join(hashtags)}",
            'engagement_tip': "스토리에 투표 스티커 추가하면 참여율 UP! 📊"
        }
    
    def _get_default_trendy_hashtags(self, industry: str) -> List[str]:
        """트렌디한 기본 해시태그"""
        base_tags = ['#일상', '#데일리', '#추천', '#인스타그램', f'#2025']
        
        industry_tags = {
            'restaurant': ['#맛집', '#맛스타그램', '#JMT', '#존맛', '#맛집투어', '#푸드스타그램', '#먹스타그램', '#카페투어', '#핫플레이스'],
            'fashion': ['#패션', '#옷스타그램', '#OOTD', '#데일리룩', '#코디', '#패션스타그램', '#스타일', '#룩북', '#신상'],
            'beauty': ['#뷰티', '#뷰티스타그램', '#화장품', '#스킨케어', '#메이크업', '#뷰티템', '#광고', '#꿀템', '#뷰티인플루언서'],
            'fitness': ['#운동', '#헬스타그램', '#오운완', '#운동스타그램', '#피트니스', '#다이어트', '#바디프로필', '#운동하는여자', '#헬스']
        }
        
        return base_tags + industry_tags.get(industry, industry_tags['restaurant'])
    
    def _parse_content_fallback(self, content_text: str, business_info: Dict) -> Dict:
        """JSON 파싱 실패시 대체 파싱"""
        lines = content_text.strip().split('\n')
        caption = ""
        hashtags = []
        
        for line in lines:
            if line.strip().startswith('#'):
                # 해시태그 라인
                tags = [tag.strip() for tag in line.split() if tag.startswith('#')]
                hashtags.extend(tags)
            elif line.strip():
                # 캡션 라인
                caption += line + "\n"
        
        if not caption:
            caption = lines[0] if lines else f"{business_info['business_name']}과 함께하는 특별한 순간 ✨"
        
        if not hashtags:
            hashtags = self._get_default_trendy_hashtags(business_info['industry'])
        
        return {
            'caption': caption.strip(),
            'hashtags': hashtags[:15],
            'engagement_tip': '스토리 멘션하면 리포스트 해드려요! 🎁'
        }

# FastAPI 앱
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AIGRAM - AI Instagram Marketing Platform 시작")
    init_db()
    yield

app = FastAPI(title="AIGRAM", lifespan=lifespan, debug=DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 인스턴스
instagram_service = InstagramService()
content_generator = AIContentGenerator()

# main.py의 홈페이지 라우트를 이것으로 교체하세요:

@app.get("/", response_class=HTMLResponse)
async def home():
    """대기업 스타일 홈페이지"""
    return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIGRAM - AI 기반 인스타그램 마케팅</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #0066ff;
            --text-gray: #666666;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        
        .navbar {
            padding: 1rem 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .logo {
            font-size: 24px;
            font-weight: 700;
            color: black;
            text-decoration: none;
        }
        
        .logo span {
            color: var(--primary-color);
        }
        
        .hero {
            padding: 100px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .hero h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
        }
        
        .hero h1 span {
            color: #00d4ff;
        }
        
        .hero p {
            font-size: 1.25rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }
        
        .btn-hero {
            background: white;
            color: var(--primary-color);
            padding: 15px 40px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            transition: transform 0.3s;
            border: none;
            cursor: pointer;
        }
        
        .btn-hero:hover {
            transform: translateY(-2px);
            color: var(--primary-color);
        }
        
        .btn-secondary {
            background: transparent;
            color: white;
            border: 2px solid white;
            padding: 15px 40px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .btn-secondary:hover {
            background: white;
            color: var(--primary-color);
        }
        
        .trust-badges {
            display: flex;
            gap: 60px;
            margin-top: 60px;
        }
        
        .trust-badge h3 {
            font-size: 2.5rem;
            margin: 0;
            font-weight: 700;
        }
        
        .trust-badge p {
            margin: 0;
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        .features {
            padding: 80px 0;
            background: white;
        }
        
        .feature-card {
            text-align: center;
            padding: 40px;
            border-radius: 10px;
            background: #f8f9fa;
            height: 100%;
            transition: all 0.3s;
        }
        
        .feature-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .feature-icon {
            width: 80px;
            height: 80px;
            background: var(--primary-color);
            color: white;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            margin: 0 auto 20px;
        }
        
        .demo-section {
            padding: 80px 0;
            background: #f8f9fa;
        }
        
        .demo-form {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .loading {
            display: none;
        }
        
        .loading.show {
            display: inline-block;
        }
        
        #demo-result {
            display: none;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="container">
            <a href="/" class="logo">AI<span>GRAM</span></a>
            <div class="ms-auto d-flex gap-3">
                <a href="#features" class="nav-link">주요 기능</a>
                <a href="/login" class="nav-link">로그인</a>
                <a href="/dashboard" class="btn btn-primary">무료 시작하기</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="row">
                <div class="col-lg-8">
                    <h1>AI가 만드는<br><span>완벽한 인스타그램 마케팅</span></h1>
                    <p>OpenAI GPT-3.5 기술로 브랜드에 최적화된 콘텐츠를 자동 생성하고,<br>
                    Instagram API로 즉시 포스팅하는 완전 자동화 마케팅 솔루션</p>
                    
                    <div class="d-flex gap-3">
                        <a href="/dashboard" class="btn-hero">
                            <i class="fas fa-rocket"></i> 지금 시작하기
                        </a>
                        <button onclick="scrollToDemo()" class="btn-secondary">
                            <i class="fas fa-play"></i> 데모 체험하기
                        </button>
                    </div>
                    
                    <div class="trust-badges">
                        <div class="trust-badge">
                            <h3>3분</h3>
                            <p>설정부터<br>첫 포스팅까지</p>
                        </div>
                        <div class="trust-badge">
                            <h3>24/7</h3>
                            <p>완전 자동<br>콘텐츠 운영</p>
                        </div>
                        <div class="trust-badge">
                            <h3>300%</h3>
                            <p>평균 참여도<br>상승률</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features -->
    <section class="features" id="features">
        <div class="container">
            <h2 class="text-center mb-5">강력한 AI 마케팅 기능</h2>
            <p class="text-center text-muted mb-5">OpenAI와 Instagram API를 완벽하게 연동한 자동화 시스템</p>
            
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="feature-card">
                        <div class="feature-icon">
                            <i class="fas fa-brain"></i>
                        </div>
                        <h4>GPT-3.5 콘텐츠 생성</h4>
                        <p>브랜드 톤앤매너를 학습한 AI가 업종별 최적화된 캡션과 해시태그를 자동으로 생성합니다.</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="feature-card">
                        <div class="feature-icon">
                            <i class="fas fa-images"></i>
                        </div>
                        <h4>스마트 이미지 매칭</h4>
                        <p>Unsplash API로 콘텐츠에 완벽하게 어울리는 고품질 이미지를 자동으로 선택합니다.</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="feature-card">
                        <div class="feature-icon">
                            <i class="fas fa-rocket"></i>
                        </div>
                        <h4>원클릭 자동 포스팅</h4>
                        <p>Instagram Graph API로 생성된 콘텐츠를 즉시 포스팅. 예약 발행도 가능합니다.</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Demo Section -->
    <section class="demo-section" id="demo">
        <div class="container">
            <h2 class="text-center mb-5">실시간 데모 체험</h2>
            <p class="text-center text-muted mb-5">지금 바로 AI 마케팅의 강력함을 경험해보세요</p>
            
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <div class="demo-form">
                        <form id="demo-form" onsubmit="generateDemo(event)">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="form-label">비즈니스 이름</label>
                                    <input type="text" class="form-control" id="demo-business" value="카페 데모" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">업종</label>
                                    <select class="form-select" id="demo-industry" required>
                                        <option value="restaurant">🍽️ 음식점/카페</option>
                                        <option value="fashion">👔 패션/의류</option>
                                        <option value="beauty">💄 뷰티/화장품</option>
                                        <option value="fitness">💪 피트니스/헬스</option>
                                    </select>
                                </div>
                                <div class="col-12">
                                    <button type="submit" class="btn btn-primary w-100">
                                        <span class="spinner-border spinner-border-sm loading" id="loading"></span>
                                        <span id="btn-text">AI 콘텐츠 생성 체험하기</span>
                                    </button>
                                </div>
                            </div>
                        </form>

                        <div id="demo-result" class="mt-4">
                            <div class="alert alert-success">
                                <h5>🎉 AI가 생성한 콘텐츠</h5>
                                <div id="demo-content"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- CTA -->
    <section class="py-5 bg-primary text-white">
        <div class="container text-center">
            <h2 class="mb-4">지금 시작하면 7일 무료</h2>
            <p class="mb-4">신용카드 없이 바로 시작할 수 있습니다</p>
            <a href="/dashboard" class="btn btn-light btn-lg">무료로 시작하기</a>
        </div>
    </section>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 스크롤 함수
        function scrollToDemo() {
            document.getElementById('demo').scrollIntoView({ behavior: 'smooth' });
        }
        
        // 부드러운 스크롤
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
        
        // 데모 폼 제출
        async function generateDemo(event) {
            event.preventDefault();
            
            const loading = document.getElementById('loading');
            const btnText = document.getElementById('btn-text');
            const resultDiv = document.getElementById('demo-result');
            const contentDiv = document.getElementById('demo-content');
            
            // 로딩 표시
            loading.classList.add('show');
            btnText.textContent = 'AI가 콘텐츠를 생성 중입니다...';
            
            const businessName = document.getElementById('demo-business').value;
            const industry = document.getElementById('demo-industry').value;
            
            try {
                // API 호출
                const response = await fetch('/api/demo/generate-content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        business_name: businessName,
                        industry: industry,
                        target_audience: '일반 고객',
                        brand_voice: '친근하고 전문적인'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    contentDiv.innerHTML = `
                        <div class="mb-3">
                            <h6>📝 생성된 캡션</h6>
                            <p>${data.content.caption}</p>
                        </div>
                        <div class="mb-3">
                            <h6>🏷️ 추천 해시태그</h6>
                            <div>${data.content.hashtags.map(tag => `<span class="badge bg-primary me-1">${tag}</span>`).join('')}</div>
                        </div>
                        <div class="mt-3">
                            <a href="/dashboard" class="btn btn-success">실제로 사용해보기 →</a>
                        </div>
                    `;
                    resultDiv.style.display = 'block';
                } else {
                    alert('콘텐츠 생성에 실패했습니다.');
                }
            } catch (error) {
                console.error('Error:', error);
                // 오류 시 샘플 데이터 표시
                const sampleContent = {
                    restaurant: {
                        caption: "☕ 특별한 하루를 시작하는 완벽한 한 잔! 오늘도 카페 데모에서 여러분의 소중한 시간을 함께합니다. 🌟",
                        hashtags: ["#카페데모", "#커피맛집", "#카페스타그램", "#일상", "#커피"]
                    },
                    fashion: {
                        caption: "✨ 새로운 컬렉션이 도착했습니다! 당신만의 스타일을 완성해보세요. 💫",
                        hashtags: ["#패션", "#스타일", "#ootd", "#데일리룩", "#트렌드"]
                    }
                };
                
                const content = sampleContent[industry] || sampleContent.restaurant;
                
                contentDiv.innerHTML = `
                    <div class="mb-3">
                        <h6>📝 생성된 캡션</h6>
                        <p>${content.caption}</p>
                    </div>
                    <div class="mb-3">
                        <h6>🏷️ 추천 해시태그</h6>
                        <div>${content.hashtags.map(tag => `<span class="badge bg-primary me-1">${tag}</span>`).join('')}</div>
                    </div>
                    <div class="mt-3">
                        <a href="/dashboard" class="btn btn-success">실제로 사용해보기 →</a>
                    </div>
                `;
                resultDiv.style.display = 'block';
            } finally {
                // 로딩 숨기기
                loading.classList.remove('show');
                btnText.textContent = 'AI 콘텐츠 생성 체험하기';
            }
        }
    </script>
</body>
</html>
    """

# 대시보드
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """대시보드 (로그인 필요)"""
    logger.info(f"대시보드 접속 시도 - 쿠키: {request.cookies}")
    
    current_user = await get_current_user(request)
    
    if not current_user:
        logger.warning("인증 실패 - 로그인 페이지로 리다이렉트")
        return RedirectResponse(url="/login", status_code=302)
    
    logger.info(f"대시보드 접속 성공 - 사용자: {current_user['email']}")
    
    # dashboard.html 파일 읽기
    try:
        with open("dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        # 파일이 없으면 기본 HTML 반환
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>대시보드</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <h1>대시보드</h1>
                <p>dashboard.html 파일이 필요합니다.</p>
                <a href="/" class="btn btn-secondary">홈으로</a>
            </div>
        </body>
        </html>
        """
    


# 파비콘 설정
@app.get("/favicon.ico")
async def favicon():
    # 이모지를 favicon으로 사용
    return Response(content="", media_type="image/x-icon")

# 로그인 페이지
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """로그인 페이지"""
    with open("login.html", "r", encoding="utf-8") as f:
        return f.read()

# API: 회원가입
@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    """회원가입"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (user_data.email,))
        
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다")
        
        password_hash = hash_password(user_data.password)
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, business_name, industry)
            VALUES (?, ?, ?, ?)
        """, (user_data.email, password_hash, user_data.business_name, user_data.industry))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        access_token = create_access_token(user_id, user_data.email)
        
        response = JSONResponse({
            "success": True,
            "message": "회원가입이 완료되었습니다!",
            "user": {
                "id": user_id,
                "email": user_data.email,
                "business_name": user_data.business_name,
                "industry": user_data.industry
            }
        })
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=JWT_EXPIRATION_HOURS * 3600,
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 처리 오류: {str(e)}")

# API: 로그인
@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    """로그인"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, password_hash, business_name, industry
            FROM users 
            WHERE email = ? AND is_active = TRUE
        """, (user_data.email,))
        
        user_record = cursor.fetchone()
        
        if not user_record or not verify_password(user_data.password, user_record[2]):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다")
        
        cursor.execute("""
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        """, (user_record[0],))
        conn.commit()
        conn.close()
        
        access_token = create_access_token(user_record[0], user_record[1])
        
        response = JSONResponse({
            "success": True,
            "message": "로그인 성공!",
            "user": {
                "id": user_record[0],
                "email": user_record[1],
                "business_name": user_record[3],
                "industry": user_record[4]
            }
        })
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=JWT_EXPIRATION_HOURS * 3600,
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 오류: {str(e)}")

# API: 로그아웃
@app.post("/api/auth/logout")
async def logout():
    """로그아웃"""
    response = JSONResponse({"success": True, "message": "로그아웃되었습니다"})
    response.delete_cookie("access_token")
    return response

# API: 현재 사용자 정보
@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(require_auth)):
    """현재 사용자 정보"""
    return {"success": True, "user": current_user}

# API: 콘텐츠 생성
@app.post("/api/generate-content")
async def generate_content_api(request: ContentRequest, current_user: dict = Depends(require_auth)):
    """AI 콘텐츠 생성"""
    try:
        business_info = {
            'business_name': request.business_name or current_user['business_name'],
            'industry': request.industry or current_user['industry'],
            'target_audience': request.target_audience,
            'brand_voice': request.brand_voice
        }
        
        content = await content_generator.generate_content(business_info)
        
        # DB에 저장
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO generated_content 
            (user_id, business_name, industry, caption, hashtags, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            current_user['id'],
            business_info['business_name'],
            business_info['industry'],
            content['caption'],
            json.dumps(content['hashtags']),
            content['image_url'],
            datetime.now().isoformat()
        ))
        content_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "콘텐츠 생성 완료!",
            "content": content,
            "content_id": content_id
        }
        
    except Exception as e:
        logger.error(f"콘텐츠 생성 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API: Instagram 포스팅
@app.post("/api/post-instagram-final")
async def post_instagram(request: InstagramPostRequest, current_user: dict = Depends(require_auth)):
    """Instagram 포스팅"""
    try:
        if not request.image_url:
            raise HTTPException(status_code=400, detail="이미지 URL이 필요합니다")
        
        # 1. 미디어 컨테이너 생성
        creation_id = await instagram_service.create_media_container(
            request.image_url,
            request.caption
        )
        
        if not creation_id:
            raise HTTPException(status_code=400, detail="미디어 컨테이너 생성 실패")
        
        # 2. 잠시 대기
        await asyncio.sleep(3)
        
        # 3. 미디어 발행
        success = await instagram_service.publish_media(creation_id)
        
        if success:
            # DB에 기록
            try:
                conn = sqlite3.connect("instagram_marketing.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO instagram_posts 
                    (user_id, business_name, caption, image_url, post_id, status, posted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    current_user['id'],
                    current_user['business_name'],
                    request.caption,
                    request.image_url,
                    creation_id,
                    'posted',
                    datetime.now().isoformat()
                ))
                conn.commit()
                conn.close()
            except Exception as db_error:
                logger.warning(f"포스팅 기록 저장 실패: {db_error}")
            
            return {
                "success": True,
                "message": "Instagram 포스팅 성공!",
                "creation_id": creation_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="미디어 발행 실패")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Instagram 포스팅 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API: Instagram 연동 테스트
@app.get("/api/test-instagram-simple")
async def test_instagram():
    """Instagram API 연동 테스트"""
    if not instagram_service.validate_credentials():
        return {
            "success": False,
            "error": "Instagram 인증 정보가 설정되지 않았습니다"
        }
    
    try:
        url = f"{instagram_service.base_url}/{instagram_service.api_version}/{instagram_service.business_account_id}"
        params = {
            'fields': 'id,name,username',
            'access_token': instagram_service.access_token
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "account_info": data,
                "message": f"✅ Instagram 계정 연결 성공: @{data.get('username', 'N/A')}"
            }
        else:
            return {
                "success": False,
                "error": response.json()
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# API: 사용자 통계
@app.get("/api/user/stats")
async def get_user_stats(current_user: dict = Depends(require_auth)):
    """사용자 통계"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM generated_content WHERE user_id = ?", (current_user['id'],))
        total_content = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM instagram_posts WHERE user_id = ? AND status = 'posted'", (current_user['id'],))
        posted_content = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "total_content": total_content,
                "posted_content": posted_content,
                "success_rate": round((posted_content / total_content * 100) if total_content > 0 else 0, 1)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# API: 헬스체크
@app.get("/health")
async def health_check():
    """시스템 상태 확인"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        db_status = "healthy"
    except:
        db_status = "error"
    
    return {
        "status": "healthy",
        "database": db_status,
        "instagram": instagram_service.validate_credentials(),
        "openai": bool(os.getenv('OPENAI_API_KEY')),
        "timestamp": datetime.now().isoformat()
    }

# API: 데모 콘텐츠 생성 (로그인 불필요)
@app.post("/api/demo/generate-content")
async def demo_generate_content(request: ContentRequest):
    """데모용 콘텐츠 생성 (로그인 불필요)"""
    try:
        business_info = {
            'business_name': request.business_name,
            'industry': request.industry,
            'target_audience': request.target_audience,
            'brand_voice': request.brand_voice
        }
        
        # OpenAI API가 없을 경우 템플릿 사용
        if not os.getenv('OPENAI_API_KEY'):
            templates = {
                'restaurant': {
                    'caption': f"☕ 특별한 하루를 시작하는 완벽한 한 잔! 오늘도 {request.business_name}에서 여러분의 소중한 시간을 함께합니다. 정성스럽게 로스팅한 원두의 깊은 향과 바리스타의 전문적인 손길이 만나 특별한 커피가 탄생했습니다. 🌟",
                    'hashtags': ["#카페", "#커피맛집", "#카페스타그램", "#일상", "#커피", "#분위기좋은카페", "#데일리커피", "#핸드드립", "#스페셜티커피", "#카페라떼"]
                },
                'fashion': {
                    'caption': f"✨ {request.business_name}의 새로운 컬렉션이 도착했습니다! 이번 시즌 트렌드를 반영한 스타일리시한 아이템들로 당신만의 개성 있는 룩을 완성해보세요. 특별한 순간을 더욱 빛나게 만들어드립니다. 💫",
                    'hashtags': ["#패션", "#스타일", "#ootd", "#fashion", "#코디", "#데일리룩", "#트렌드", "#스타일링", "#옷스타그램", "#패션스타그램"]
                },
                'beauty': {
                    'caption': f"💄 {request.business_name}과 함께 더 아름다운 당신을 발견하세요! 자연 유래 성분으로 만든 순한 포뮬러가 피부에 편안함을 선사합니다. 건강한 아름다움의 시작, 지금 경험해보세요. ✨",
                    'hashtags': ["#뷰티", "#화장품", "#스킨케어", "#beauty", "#메이크업", "#자연화장품", "#피부관리", "#뷰티팁", "#글로우", "#셀프케어"]
                },
                'fitness': {
                    'caption': f"💪 {request.business_name}에서 건강한 변화를 시작하세요! 전문 트레이너와 함께하는 체계적인 운동 프로그램으로 목표를 달성할 수 있습니다. 오늘이 바로 시작하기 가장 좋은 날입니다! 🔥",
                    'hashtags': ["#피트니스", "#운동", "#헬스", "#fitness", "#다이어트", "#건강", "#트레이닝", "#홈트", "#운동스타그램", "#헬스타그램"]
                }
            }
            
            template = templates.get(request.industry, templates['restaurant'])
            
            return {
                "success": True,
                "content": {
                    "caption": template['caption'],
                    "hashtags": template['hashtags'],
                    "image_url": f"https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1024&q=80"
                }
            }
        
        # OpenAI API 사용
        content = await content_generator.generate_content(business_info)
        
        return {
            "success": True,
            "content": content
        }
        
    except Exception as e:
        logger.error(f"데모 콘텐츠 생성 오류: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 AIGRAM - AI Instagram Marketing Platform")
    print(f"📱 홈페이지: http://{HOST}:{PORT}")
    print(f"📊 대시보드: http://{HOST}:{PORT}/dashboard")
    print(f"📚 API 문서: http://{HOST}:{PORT}/docs")
    print(f"🔧 디버그 모드: {DEBUG}")
    
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)