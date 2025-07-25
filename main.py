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