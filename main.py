# main.py - FastAPI 메인 애플리케이션 (수정된 버전)
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import sqlite3
import json
import jwt
from datetime import datetime, timedelta
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 프로젝트 구조 생성
def create_project_structure():
    """프로젝트 디렉토리 구조 생성"""
    directories = [
        "templates",
        "static/css",
        "static/js", 
        "static/images",
        "static/fonts"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# FastAPI 앱 초기화
app = FastAPI(
    title="Instagram AI Marketing Automation",
    description="Enterprise-grade Instagram marketing automation platform",
    version="2.0.0",
    docs_url="/admin/docs",
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

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception as e:
    print(f"정적 파일 설정 오류: {e}")
    templates = None

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

# 데이터베이스 초기화
def init_database():
    """데이터베이스 초기화"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 사용자 테이블
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
        
        # 비즈니스 정보 테이블
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
        
        conn.commit()
        conn.close()
        print("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        print(f"데이터베이스 초기화 오류: {e}")

# 유틸리티 함수들
def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
# 기존 유틸리티 함수들 아래에 추가
def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except ImportError:
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hashed

# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    init_database()
    print("🚀 Instagram AI Marketing Platform 시작!")

# 메인 라우트들
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """프리미엄 랜딩 페이지"""
    if templates:
        try:
            return templates.TemplateResponse("landing.html", {
                "request": request,
                "year": datetime.now().year
            })
        except Exception as e:
            print(f"템플릿 로드 오류: {e}")
    
    # 기본 HTML 응답
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram AI Marketing Platform</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            .container {
                text-align: center;
                max-width: 800px;
                padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            }
            h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
                font-weight: 800;
            }
            p {
                font-size: 1.2rem;
                margin-bottom: 2rem;
                opacity: 0.9;
            }
            .btn {
                background: white;
                color: #667eea;
                padding: 15px 30px;
                border: none;
                border-radius: 12px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                margin: 10px;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            }
            .features {
                margin-top: 3rem;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 2rem;
            }
            .feature {
                padding: 1.5rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
            .status {
                margin: 2rem 0;
                padding: 1rem;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Instagram AI Marketing</h1>
            <p>AI 기반 Instagram 마케팅 자동화 플랫폼</p>
            
            <div class="status">
                <h3>✅ 플랫폼이 성공적으로 배포되었습니다!</h3>
                <p>현재 시간: <span id="time"></span></p>
            </div>
            
            <div>
                <a href="/dashboard" class="btn">대시보드 이동</a>
                <a href="/admin/docs" class="btn">API 문서</a>
                <button class="btn" onclick="testAPI()">연결 테스트</button>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h4>🤖 AI 콘텐츠 생성</h4>
                    <p>GPT-4로 자동 콘텐츠 생성</p>
                </div>
                <div class="feature">
                    <h4>⏰ 스마트 스케줄링</h4>
                    <p>최적 시간 자동 포스팅</p>
                </div>
                <div class="feature">
                    <h4>📊 실시간 분석</h4>
                    <p>성과 분석 및 인사이트</p>
                </div>
            </div>
            
            <div id="result" style="margin-top: 2rem;"></div>
        </div>
        
        <script>
            // 현재 시간 표시
            function updateTime() {
                document.getElementById('time').textContent = new Date().toLocaleString('ko-KR');
            }
            updateTime();
            setInterval(updateTime, 1000);
            
            // API 테스트
            async function testAPI() {
                const result = document.getElementById('result');
                result.innerHTML = '<div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px;">테스트 중...</div>';
                
                try {
                    const response = await fetch('/test');
                    const data = await response.json();
                    result.innerHTML = `
                        <div style="background: rgba(34, 197, 94, 0.3); padding: 15px; border-radius: 8px; margin-top: 15px;">
                            <strong>✅ 연결 성공!</strong><br>
                            상태: ${data.status}<br>
                            서버 시간: ${data.time}<br>
                            OpenAI: ${data.api_keys.openai ? '✅' : '❌'}<br>
                            Instagram: ${data.api_keys.instagram ? '✅' : '❌'}
                        </div>
                    `;
                } catch (error) {
                    result.innerHTML = `
                        <div style="background: rgba(239, 68, 68, 0.3); padding: 15px; border-radius: 8px; margin-top: 15px;">
                            ❌ 오류: ${error.message}
                        </div>
                    `;
                }
            }
        </script>
    </body>
    </html>
    """)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """대시보드 페이지"""
    if templates:
        try:
            return templates.TemplateResponse("dashboard.html", {
                "request": request
            })
        except Exception as e:
            print(f"대시보드 템플릿 오류: {e}")
    
    return HTMLResponse("""
    <div style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>대시보드</h1>
        <p>대시보드 기능을 준비 중입니다...</p>
        <a href="/" style="color: #667eea; text-decoration: none;">← 홈으로 돌아가기</a>
    </div>
    """)

@app.get("/test")
async def test():
    """기본 테스트 엔드포인트"""
    return {
        "status": "success",
        "message": "서버 정상 작동",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "platform": "Railway",
        "api_keys": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "instagram": bool(os.getenv("INSTAGRAM_ACCESS_TOKEN"))
        }
    }

# 기존 @app.get("/api/generate-content") 위에 추가

@app.post("/api/login")
async def login_user(user: UserLogin):
    """사용자 로그인"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 사용자 확인 및 비즈니스 정보 가져오기
        cursor.execute('''
            SELECT u.id, u.password_hash, u.full_name, u.email,
                   b.id as business_id, b.business_name, b.subscription_plan
            FROM users u
            LEFT JOIN businesses b ON u.id = b.user_id
            WHERE u.email = ? AND u.is_active = TRUE
        ''', (user.email,))
        
        result = cursor.fetchone()
        if not result or not verify_password(user.password, result[1]):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")
        
        user_id, _, full_name, email, business_id, business_name, plan = result
        
        # 마지막 로그인 시간 업데이트
        cursor.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.now().isoformat(), user_id))
        
        # JWT 토큰 생성
        access_token = create_access_token({
            "user_id": user_id,
            "business_id": business_id,
            "email": email
        })
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "business_name": business_name,
                "subscription_plan": plan
            },
            "business_id": business_id,
            "message": f"안녕하세요, {business_name}님! 👋"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 중 오류가 발생했습니다: {str(e)}")

@app.post("/api/register")
async def register_user(user: UserCreate):
    """사용자 회원가입"""
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 이메일 중복 확인
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")
        
        # 사용자 등록
        password_hash = hash_password(user.password)
        cursor.execute('''
            INSERT INTO users (email, password_hash, full_name)
            VALUES (?, ?, ?)
        ''', (user.email, password_hash, user.business_name))
        
        user_id = cursor.lastrowid
        
        # 비즈니스 정보 등록
        cursor.execute('''
            INSERT INTO businesses (
                user_id, business_name, industry, target_audience, 
                brand_voice, phone, website, subscription_plan, monthly_fee
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, user.business_name, user.industry, user.target_audience,
            user.brand_voice, user.phone, user.website, 'basic', 150000
        ))
        
        business_id = cursor.lastrowid
        
        # JWT 토큰 생성
        access_token = create_access_token({
            "user_id": user_id, 
            "business_id": business_id,
            "email": user.email
        })
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user.email,
                "business_name": user.business_name
            },
            "business_id": business_id,
            "message": "회원가입이 완료되었습니다! 🎉"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")

# AI 기능 API (안전한 버전)
@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """대시보드 기본 데이터"""
    return {
        "success": True,
        "business": {
            "name": "테스트 비즈니스",
            "industry": "software",
            "plan": "basic",
            "monthly_fee": 150000
        },
        "stats": {
            "monthly_posts": 12,
            "published_posts": 8,
            "scheduled_posts": 4,
            "avg_engagement": 5.2
        }
    }


    """간단한 콘텐츠 생성 (AI 없이)"""
    try:
        # 산업별 기본 콘텐츠 템플릿
        templates_dict = {
            "restaurant": {
                "caption": f"🍽️ {business_name}에서 특별한 맛을 경험해보세요! 신선한 재료로 정성스럽게 준비한 오늘의 메뉴를 소개합니다.",
                "hashtags": ["#맛집", "#푸드스타그램", "#맛있어요", "#신메뉴", "#오늘뭐먹지"]
            },
            "fashion": {
                "caption": f"✨ {business_name}의 새로운 컬렉션을 만나보세요! 트렌디하고 스타일리시한 아이템들로 당신만의 스타일을 완성하세요.",
                "hashtags": ["#패션", "#스타일", "#OOTD", "#신상", "#패션스타그램"]
            },
            "beauty": {
                "caption": f"💄 {business_name}와 함께 더욱 아름다운 당신을 발견하세요! 프리미엄 뷰티 제품으로 자연스러운 아름다움을 연출해보세요.",
                "hashtags": ["#뷰티", "#화장품", "#스킨케어", "#뷰티스타그램", "#셀프케어"]
            }
        }
        
        template = templates_dict.get(industry, {
            "caption": f"🌟 {business_name}와 함께하는 특별한 경험! 고객 만족을 위해 최선을 다하는 저희를 만나보세요.",
            "hashtags": ["#비즈니스", "#서비스", "#품질", "#고객만족", "#추천"]
        })
        
        return {
            "success": True,
            "content": {
                "caption": template["caption"],
                "hashtags": template["hashtags"],
                "full_caption": template["caption"] + "\n\n" + " ".join(template["hashtags"]),
                "image_url": "https://images.unsplash.com/photo-1611224923853-80b023f02d71?auto=format&fit=crop&w=1024&q=80"
            },
            "message": "콘텐츠가 생성되었습니다! 🎨"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "콘텐츠 생성 중 오류가 발생했습니다."
        }

# 실제 AI 기능 (선택적 로드)
@app.get("/api/generate-ai-content")
async def generate_ai_content(
    business_name: str = "테스트 비즈니스",
    industry: str = "restaurant"
):
    """실제 AI 콘텐츠 생성 (OpenAI API 사용)"""
    try:
        # AI 시스템을 안전하게 임포트
        poster_system = None
        try:
            from instagram_auto_poster import InstagramAutoPoster
            poster_system = InstagramAutoPoster()
        except ImportError as e:
            return {
                "success": False,
                "error": "AI 모듈을 불러올 수 없습니다",
                "message": "기본 콘텐츠 생성을 사용해주세요."
            }
        
        business_info = {
            'name': business_name,
            'industry': industry,
            'target': '20-30대 고객'
        }
        
        # 실제 AI 콘텐츠 생성
        content = poster_system.generate_content_with_ai(business_info)
        
        return {
            "success": True,
            "content": {
                "caption": content.get('raw_caption', ''),
                "hashtags": content.get('hashtags', []),
                "full_caption": content.get('caption', ''),
                "image_url": "https://images.unsplash.com/photo-1611224923853-80b023f02d71?auto=format&fit=crop&w=1024&q=80"
            },
            "message": "AI가 콘텐츠를 생성했습니다! 🤖"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "AI 콘텐츠 생성 중 오류가 발생했습니다."
        }

@app.get("/")
async def read_root():
    return FileResponse("templates/landing.html")

if __name__ == "__main__":
    import uvicorn
    
    print("🎯 Instagram AI Marketing Automation Platform")
    print("=" * 60)
    print("🌐 URL: http://localhost:8000")
    print("📊 Admin: http://localhost:8000/admin/docs")
    print("🎨 Features: Premium UI/UX, AI Content, Auto Posting")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )