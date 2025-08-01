# api_routes.py - 개선된 API 라우트 (에러 처리 통합)
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
import bcrypt
import jwt
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# 개선된 모듈들 임포트
from utils.database_manager import get_db_manager
from utils.error_handler import (
    handle_error, create_error_response, async_error_handler_decorator,
    ValidationError, DatabaseError, AuthenticationError, APIError,
    ErrorType, ErrorSeverity
)
from utils.config import get_config

# 기존 모듈들
try:
    from instagram_auto_poster import InstagramAutoPoster
    from complete_automation_system import InstagramMarketingBusiness
except ImportError as e:
    print(f"⚠️ Instagram 모듈 임포트 실패: {e}")
    InstagramAutoPoster = None
    InstagramMarketingBusiness = None

load_dotenv()

# 설정 및 매니저들
config = get_config()
db_manager = get_db_manager()
api_router = APIRouter()
security = HTTPBearer(auto_error=False)

# 환경변수
SECRET_KEY = config.get_secret_key()
ALGORITHM = config.get_jwt_algorithm()
ACCESS_TOKEN_EXPIRE_HOURS = config.get_access_token_expire_hours()

# Instagram 시스템 초기화 (안전하게)
poster = None
automation_system = None

try:
    if InstagramAutoPoster:
        poster = InstagramAutoPoster()
    if InstagramMarketingBusiness:
        automation_system = InstagramMarketingBusiness()
except Exception as e:
    print(f"⚠️ Instagram 시스템 초기화 실패: {e}")

# 개선된 Pydantic 모델들
class UserCreate(BaseModel):
    business_name: str
    email: EmailStr
    password: str
    industry: str
    target_audience: str
    brand_voice: Optional[str] = "친근하고 전문적인"
    phone: Optional[str] = ""
    website: Optional[str] = ""
    
    @validator('business_name')
    def validate_business_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('비즈니스명은 2글자 이상이어야 합니다.')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 8글자 이상이어야 합니다.')
        return v
    
    @validator('industry')
    def validate_industry(cls, v):
        allowed_industries = [
            'restaurant', 'fashion', 'beauty', 'fitness', 
            'retail', 'software', 'consulting', 'other'
        ]
        if v not in allowed_industries:
            raise ValueError(f'허용된 업종: {", ".join(allowed_industries)}')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ContentGenerate(BaseModel):
    content_type: Optional[str] = "post"
    theme: Optional[str] = "product"
    custom_prompt: Optional[str] = ""
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['post', 'story', 'reel']
        if v not in allowed_types:
            raise ValueError(f'허용된 콘텐츠 타입: {", ".join(allowed_types)}')
        return v

class ContentSchedule(BaseModel):
    content_id: int
    scheduled_datetime: Optional[str] = None
    auto_schedule: Optional[bool] = True
    
    @validator('content_id')
    def validate_content_id(cls, v):
        if v <= 0:
            raise ValueError('유효하지 않은 콘텐츠 ID입니다.')
        return v

class InstagramPostRequest(BaseModel):
    caption: Optional[str] = None
    image_url: Optional[str] = None

# 유틸리티 함수들 (개선됨)
def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    try:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except Exception as e:
        raise ValidationError("비밀번호 처리 중 오류가 발생했습니다.", details={'error': str(e)})

def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        raise ValidationError("비밀번호 검증 중 오류가 발생했습니다.", details={'error': str(e)})

def create_access_token(data: dict):
    """JWT 토큰 생성"""
    try:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    except Exception as e:
        raise AuthenticationError("토큰 생성 중 오류가 발생했습니다.", details={'error': str(e)})

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """토큰 검증"""
    if credentials is None:
        raise AuthenticationError("인증이 필요합니다.")
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise AuthenticationError("유효하지 않은 토큰입니다.")
        return user_id
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("토큰이 만료되었습니다.")
    except jwt.JWTError as e:
        raise AuthenticationError("유효하지 않은 토큰입니다.", details={'jwt_error': str(e)})

# API 엔드포인트들 (개선됨)
@api_router.post("/register")
@async_error_handler_decorator
async def register_user(user: UserCreate, request: Request):
    """회원가입 및 자동화 설정"""
    try:
        # 이메일 중복 확인
        existing_user = db_manager.execute_query(
            "SELECT id FROM users WHERE email = ?", 
            (user.email,), 
            fetch_one=True
        )
        
        if existing_user:
            raise ValidationError(
                "이미 등록된 이메일입니다.", 
                field="email",
                details={'email': user.email}
            )
        
        # 사용자 생성 (트랜잭션 사용)
        with db_manager.get_transaction() as cursor:
            # 사용자 테이블에 삽입
            hashed_password = hash_password(user.password)
            cursor.execute("""
                INSERT INTO users (email, password_hash, created_at, is_active)
                VALUES (?, ?, ?, ?)
            """, (user.email, hashed_password, datetime.now().isoformat(), True))
            
            user_id = cursor.lastrowid
            
            # 비즈니스 정보 생성
            cursor.execute("""
                INSERT INTO businesses (
                    user_id, business_name, industry, target_audience, 
                    brand_voice, phone, website, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, user.business_name, user.industry, user.target_audience,
                user.brand_voice, user.phone, user.website, datetime.now().isoformat()
            ))
            
            business_id = cursor.lastrowid
            
            # 기본 비즈니스 설정 생성
            cursor.execute("""
                INSERT INTO business_settings (
                    business_id, auto_post_enabled, post_frequency, 
                    preferred_times, content_themes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                business_id, True, 1,
                json.dumps(['09:00', '12:00', '18:00']),
                json.dumps(['product', 'lifestyle']),
                datetime.now().isoformat()
            ))
        
        # 자동화 시스템 설정 (선택사항)
        if automation_system:
            try:
                automation_data = {
                    'name': user.business_name,
                    'industry': user.industry,
                    'target_audience': user.target_audience,
                    'brand_voice': user.brand_voice,
                    'auto_post_enabled': True,
                    'post_frequency': 1,
                    'preferred_times': ['09:00', '12:00', '18:00'],
                    'content_themes': ['product', 'lifestyle']
                }
                automation_system.setup_business_automation(user_id, automation_data)
            except Exception as e:
                # 자동화 설정 실패는 치명적이지 않음
                handle_error(e, {'context': 'automation_setup', 'user_id': user_id})
        
        # JWT 토큰 생성
        access_token = create_access_token({"user_id": user_id})
        
        return {
            "success": True,
            "message": "회원가입이 완료되었습니다.",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user.email,
                "business_name": user.business_name
            }
        }
        
    except ValidationError:
        raise
    except DatabaseError:
        raise
    except Exception as e:
        # 예상치 못한 오류
        raise DatabaseError(
            "회원가입 처리 중 오류가 발생했습니다.",
            details={'original_error': str(e)}
        )

@api_router.post("/login")
@async_error_handler_decorator
async def login_user(user: UserLogin, request: Request):
    """로그인"""
    try:
        # 사용자 조회
        user_data = db_manager.execute_query("""
            SELECT u.id, u.password_hash, b.business_name
            FROM users u
            LEFT JOIN businesses b ON u.id = b.user_id
            WHERE u.email = ? AND u.is_active = 1
        """, (user.email,), fetch_one=True)
        
        if not user_data:
            raise AuthenticationError(
                "이메일 또는 비밀번호가 잘못되었습니다.",
                details={'email': user.email}
            )
        
        # 비밀번호 검증
        if not verify_password(user.password, user_data['password_hash']):
            raise AuthenticationError(
                "이메일 또는 비밀번호가 잘못되었습니다.",
                details={'email': user.email}
            )
        
        # 마지막 로그인 시간 업데이트
        db_manager.execute_command(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user_data['id'])
        )
        
        # JWT 토큰 생성
        access_token = create_access_token({"user_id": user_data['id']})
        
        return {
            "success": True,
            "message": "로그인이 완료되었습니다.",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_data['id'],
                "email": user.email,
                "business_name": user_data['business_name']
            }
        }
        
    except AuthenticationError:
        raise
    except Exception as e:
        raise DatabaseError(
            "로그인 처리 중 오류가 발생했습니다.",
            details={'original_error': str(e)}
        )

@api_router.post("/generate-content")
@async_error_handler_decorator
async def generate_content(
    content_data: ContentGenerate,
    user_id: int = Depends(verify_token),
    request: Request = None
):
    """AI 콘텐츠 생성"""
    try:
        # 비즈니스 정보 가져오기
        business = db_manager.execute_query("""
            SELECT id, business_name, industry, target_audience, brand_voice
            FROM businesses WHERE user_id = ?
        """, (user_id,), fetch_one=True)
        
        if not business:
            raise ValidationError(
                "비즈니스 정보를 찾을 수 없습니다.",
                details={'user_id': user_id}
            )
        
        # Instagram 포스터 확인
        if not poster:
            raise APIError(
                "AI 콘텐츠 생성 서비스를 사용할 수 없습니다.",
                service="OpenAI",
                details={'reason': 'InstagramAutoPoster not initialized'}
            )
        
        business_info = {
            'name': business['business_name'],
            'industry': business['industry'],
            'target_audience': business['target_audience'] or '',
            'brand_voice': business['brand_voice'] or '친근하고 전문적인'
        }
        
        # 사용자 지정 프롬프트 추가
        if content_data.custom_prompt:
            business_info['custom_prompt'] = content_data.custom_prompt
        
        # AI 콘텐츠 생성
        content = poster.generate_content_with_ai(business_info)
        
        if not content.get('success'):
            raise APIError(
                "AI 콘텐츠 생성에 실패했습니다.",
                service="OpenAI",
                details={'business_info': business_info}
            )
        
        # 이미지 생성
        image_description = f"{business['industry']} {content_data.theme} marketing content"
        image_url = poster.generate_image_with_dalle(image_description)
        
        # 데이터베이스에 저장
        content_id = db_manager.execute_command("""
            INSERT INTO content (
                business_id, title, caption, hashtags, image_url,
                content_type, platform, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            business['id'], f"AI Generated - {content_data.theme}",
            content['caption'], json.dumps(content['hashtags']),
            image_url, content_data.content_type, 'instagram', 'draft',
            datetime.now().isoformat()
        ))
        
        return {
            "success": True,
            "message": "AI 콘텐츠가 성공적으로 생성되었습니다!",
            "content_id": content_id,
            "content": {
                "caption": content['raw_caption'],
                "hashtags": content['hashtags'],
                "full_caption": content['caption'],
                "image_url": image_url
            }
        }
        
    except (ValidationError, APIError):
        raise
    except Exception as e:
        raise APIError(
            "콘텐츠 생성 중 예상치 못한 오류가 발생했습니다.",
            service="ContentGeneration",
            details={'original_error': str(e)}
        )

@api_router.post("/post-instagram")
@async_error_handler_decorator
async def post_instagram_content(
    post_data: InstagramPostRequest,
    user_id: int = Depends(verify_token),
    request: Request = None
):
    """인스타그램에 즉시 포스팅"""
    try:
        # 비즈니스 정보 가져오기
        business = db_manager.execute_query("""
            SELECT business_name, industry, target_audience, brand_voice
            FROM businesses WHERE user_id = ?
        """, (user_id,), fetch_one=True)
        if not business:
            raise ValidationError(
                "비즈니스 정보를 찾을 수 없습니다.",
                details={'user_id': user_id}
            )
        if not poster:
            raise APIError(
                "Instagram 포스팅 서비스를 사용할 수 없습니다.",
                service="InstagramAutoPoster",
                details={'reason': 'InstagramAutoPoster not initialized'}
            )
        business_info = {
            'name': business['business_name'],
            'industry': business['industry'],
            'target_audience': business['target_audience'] or '',
            'brand_voice': business['brand_voice'] or '친근하고 전문적인'
        }
        # 포스팅 실행
        post_id = poster.post_to_instagram(
            business_info,
            custom_caption=post_data.caption,
            custom_image_url=post_data.image_url
        )
        if post_id:
            return {"success": True, "message": "포스팅 성공!", "post_id": post_id}
        else:
            return {"success": False, "message": "포스팅 실패"}
    except (ValidationError, APIError):
        raise
    except Exception as e:
        raise APIError(
            "인스타그램 포스팅 중 오류가 발생했습니다.",
            service="InstagramPost",
            details={'original_error': str(e)}
        )

@api_router.get("/dashboard-data")
@async_error_handler_decorator
async def get_dashboard_data(user_id: int = Depends(verify_token)):
    """대시보드 데이터"""
    try:
        # 비즈니스 정보
        business = db_manager.execute_query("""
            SELECT business_name, industry, target_audience
            FROM businesses WHERE user_id = ?
        """, (user_id,), fetch_one=True)
        
        if not business:
            raise ValidationError("비즈니스 정보를 찾을 수 없습니다.")
        
        # 통계 데이터 조회
        stats_queries = {
            'monthly_posts': """
                SELECT COUNT(*) as count FROM content 
                WHERE business_id = (SELECT id FROM businesses WHERE user_id = ?)
                AND date(created_at) >= date('now', 'start of month')
            """,
            'pending_posts': """
                SELECT COUNT(*) as count FROM content_schedule cs
                JOIN content c ON cs.content_id = c.id
                JOIN businesses b ON c.business_id = b.id
                WHERE b.user_id = ? AND cs.status = 'pending'
            """,
            'published_posts': """
                SELECT COUNT(*) as count FROM content 
                WHERE business_id = (SELECT id FROM businesses WHERE user_id = ?)
                AND status = 'published'
            """
        }
        
        stats = {}
        for stat_name, query in stats_queries.items():
            result = db_manager.execute_query(query, (user_id,), fetch_one=True)
            stats[stat_name] = result['count'] if result else 0
        
        return {
            "success": True,
            "business": {
                "name": business['business_name'],
                "industry": business['industry'],
                "target": business['target_audience'] or "일반 고객"
            },
            "stats": {
                **stats,
                "avg_engagement": 5.2  # 실제 데이터로 교체 예정
            }
        }
        
    except ValidationError:
        raise
    except Exception as e:
        raise DatabaseError(
            "대시보드 데이터 조회 중 오류가 발생했습니다.",
            details={'original_error': str(e)}
        )

# 추가 엔드포인트들은 동일한 패턴으로 개선...
# (post-now, schedule-content, content-list 등)