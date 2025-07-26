# main.py - FastAPI 메인 애플리케이션
from fastapi import FastAPI, HTTPException, Depends, Request, Form, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import sqlite3
import json
import jwt
import hashlib
from datetime import datetime, timedelta
import os
import asyncio
from pathlib import Path

# main.py 상단에 추가 (기존 import 아래)
from instagram_auto_poster import InstagramAutoPoster
import os
from openai import OpenAI

# 시스템 초기화 (app 생성 후에 추가)
poster_system = InstagramAutoPoster()

# OpenAI 클라이언트 직접 초기화
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 프로젝트 구조 생성
def create_project_structure():
    """프로젝트 디렉토리 구조 생성"""
    directories = [
        "templates",
        "static/css",
        "static/js", 
        "static/images",
        "static/fonts",
        "components",
        "utils",
        "database"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ 프로젝트 구조 생성 완료")

# FastAPI 앱 초기화
app = FastAPI(
    title="Instagram AI Marketing Automation",
    description="Enterprise-grade Instagram marketing automation platform",
    version="2.0.0",
    docs_url="/admin/docs",  # API 문서를 관리자 경로로 이동
    redoc_url="/admin/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
create_project_structure()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 보안 설정
security = HTTPBearer()
SECRET_KEY = "your-ultra-secure-secret-key-change-in-production-2024"
ALGORITHM = "HS256"

# Pydantic 모델들
class UserCreate(BaseModel):
    business_name: str
    email: str
    password: str
    industry: str
    target_audience: str
    brand_voice: str
    phone: Optional[str] = None
    website: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ContentRequest(BaseModel):
    business_info: Dict
    content_type: str = "post"
    platform: str = "instagram"

class ScheduleRequest(BaseModel):
    client_id: int
    posts_per_week: int = 3
    start_date: Optional[str] = None

class BusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    brand_voice: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None

# 데이터베이스 관련 함수들 (database/db_manager.py로 분리 예정)
def init_database():
    """데이터베이스 초기화"""
    conn = sqlite3.connect("instagram_marketing.db")
    cursor = conn.cursor()
    
    # 사용자 테이블 (확장됨)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            is_premium BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            profile_image TEXT
        )
    ''')
    
    # 비즈니스 정보 테이블 (확장됨)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            business_name TEXT NOT NULL,
            industry TEXT,
            target_audience TEXT,
            brand_voice TEXT,
            website TEXT,
            phone TEXT,
            logo_url TEXT,
            subscription_plan TEXT DEFAULT 'basic',
            monthly_fee INTEGER DEFAULT 150000,
            instagram_username TEXT,
            instagram_connected BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 콘텐츠 테이블 (확장됨)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            title TEXT,
            caption TEXT,
            hashtags TEXT,
            image_url TEXT,
            content_type TEXT DEFAULT 'post',
            platform TEXT DEFAULT 'instagram',
            status TEXT DEFAULT 'draft',
            engagement_rate REAL DEFAULT 0.0,
            likes_count INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            published_at TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses (id)
        )
    ''')
    
    # 스케줄 테이블 (확장됨)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            content_id INTEGER,
            scheduled_datetime TEXT,
            status TEXT DEFAULT 'pending',
            post_id TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses (id),
            FOREIGN KEY (content_id) REFERENCES content (id)
        )
    ''')
    
    # 분석 데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            date TEXT,
            platform TEXT DEFAULT 'instagram',
            followers_count INTEGER DEFAULT 0,
            posts_count INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0.0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            profile_visits INTEGER DEFAULT 0,
            website_clicks INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses (id)
        )
    ''')
    
    # 사용자 세션 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            business_id INTEGER,
            token TEXT,
            expires_at TEXT,
            ip_address TEXT,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (business_id) REFERENCES businesses (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 데이터베이스 초기화 완료")

# 유틸리티 함수들 (utils/ 폴더로 분리 예정)
def hash_password(password: str) -> str:
    """비밀번호 해싱 (보안 강화)"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증 (보안 강화)"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 토큰 생성 (보안 강화)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """현재 사용자 정보 가져오기 (보안 강화)"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        business_id: int = payload.get("business_id")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # 토큰 유효성 추가 검증
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.is_active, b.id as business_id
            FROM users u
            LEFT JOIN businesses b ON u.id = b.user_id
            WHERE u.id = ? AND u.is_active = TRUE
        """, (user_id,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found or inactive")
            
        return {
            "user_id": user_data[0],
            "email": user_data[1],
            "business_id": user_data[3] or business_id
        }
        
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# 메인 라우트들
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    init_database()
    print("🚀 Instagram AI Marketing Platform 시작!")

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """프리미엄 랜딩 페이지"""
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "year": datetime.now().year
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """프리미엄 대시보드"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request
    })

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    """가격 정책 페이지"""
    return templates.TemplateResponse("pricing.html", {
        "request": request
    })

@app.get("/features", response_class=HTMLResponse)
async def features_page(request: Request):
    """기능 소개 페이지"""
    return templates.TemplateResponse("features.html", {
        "request": request
    })

# API 엔드포인트들은 다음 아티팩트에서 계속...

if __name__ == "__main__":
    import uvicorn
    
    print("🎯 Instagram AI Marketing Automation Platform")
    print("=" * 60)
    print("🌐 URL: http://localhost:8000")
    print("📊 Admin: http://localhost:8000/admin/docs")
    print("🎨 Features: Premium UI/UX, AI Content, Auto Posting")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
# Vercel 배포를 위한 설정
if __name__ != "__main__":
    # Vercel에서 실행될 때
    app = app

# main.py 맨 아래에 추가/수정
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# 기존 코드는 그대로 두고, 맨 아래에 이것만 추가:

# Vercel용 핸들러
def handler(request):
    """Vercel serverless function handler"""
    return app

# Vercel 배포를 위한 앱 내보내기
app_for_vercel = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





 # main.py에 새로운 API 엔드포인트 추가

@app.post("/api/generate-real-content")
async def generate_real_content(
    business_name: str = "테스트 비즈니스",
    industry: str = "restaurant",
    current_user: dict = Depends(get_current_user) if 'get_current_user' in globals() else None
):
    """실제 AI로 콘텐츠 생성"""
    try:
        business_info = {
            'name': business_name,
            'industry': industry,
            'target': '20-30대 고객'
        }
        
        # 실제 AI 콘텐츠 생성
        content = poster_system.generate_content_with_ai(business_info)
        
        # 실제 DALL-E 이미지 생성
        image_description = f"{industry} business marketing content"
        image_url = poster_system.generate_image_with_dalle(image_description)
        
        return {
            "success": True,
            "content": {
                "caption": content['raw_caption'],
                "hashtags": content['hashtags'],
                "full_caption": content['caption'],
                "image_url": image_url
            },
            "message": "실제 AI가 콘텐츠를 생성했습니다! 🎨"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "AI 콘텐츠 생성 중 오류가 발생했습니다."
        }

@app.post("/api/post-to-instagram-real")
async def post_to_instagram_real(
    business_name: str = "Instagram AI Bot",
    industry: str = "marketing"
):
    """실제 Instagram에 포스팅"""
    try:
        business_info = {
            'name': business_name,
            'industry': industry,
            'target': '소상공인 및 마케터'
        }
        
        # 실제 Instagram 포스팅
        post_id = poster_system.post_to_instagram(business_info)
        
        if post_id:
            return {
                "success": True,
                "post_id": post_id,
                "message": f"Instagram에 성공적으로 포스팅되었습니다! 🎉",
                "instagram_url": f"https://www.instagram.com/p/{post_id}/"
            }
        else:
            return {
                "success": False,
                "message": "Instagram 포스팅에 실패했습니다."
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "포스팅 중 오류가 발생했습니다."
        }

@app.get("/api/test-connections")
async def test_connections():
    """API 연결 상태 테스트"""
    results = {
        "openai": False,
        "instagram": False,
        "errors": []
    }
    
    # OpenAI 테스트
    try:
        if openai_client:
            test_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            results["openai"] = True
        else:
            results["errors"].append("OpenAI API 키가 설정되지 않았습니다")
    except Exception as e:
        results["errors"].append(f"OpenAI 오류: {str(e)}")
    
    # Instagram 테스트
    try:
        account_info = poster_system.get_account_info()
        if account_info:
            results["instagram"] = True
            results["instagram_info"] = account_info
        else:
            results["errors"].append("Instagram 계정 정보를 가져올 수 없습니다")
    except Exception as e:
        results["errors"].append(f"Instagram 오류: {str(e)}")
    
    return results   