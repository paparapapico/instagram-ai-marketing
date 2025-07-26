# api_routes.py - 수정된 API 라우터
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import sqlite3
import bcrypt
import jwt
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

load_dotenv()

# 라우터 생성
api_router = APIRouter()
security = HTTPBearer(auto_error=False)

# 환경변수
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Pydantic 모델들
class UserCreate(BaseModel):
    business_name: str
    email: EmailStr
    password: str
    industry: str
    target_audience: str
    brand_voice: Optional[str] = ""
    phone: Optional[str] = ""
    website: Optional[str] = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    brand_voice: Optional[str] = None

# 유틸리티 함수들
def get_db_connection():
    """데이터베이스 연결"""
    return sqlite3.connect("instagram_marketing.db")

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    """JWT 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """토큰 검증"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다"
        )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다"
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다"
        )

# API 엔드포인트들
@api_router.post("/register")
async def register_user(user: UserCreate):
    """회원가입"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 이메일 중복 확인
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일입니다"
            )
        
        # 비밀번호 해싱
        hashed_password = hash_password(user.password)
        
        # 사용자 생성
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
        
        conn.commit()
        
        # JWT 토큰 생성
        access_token = create_access_token({"user_id": user_id})
        
        return {
            "message": "회원가입이 완료되었습니다",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user.email,
                "business_name": user.business_name
            }
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 중 오류가 발생했습니다: {str(e)}"
        )
    finally:
        conn.close()

@api_router.post("/login")
async def login_user(user: UserLogin):
    """로그인"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 사용자 조회
        cursor.execute("""
            SELECT u.id, u.password_hash, b.business_name
            FROM users u
            LEFT JOIN businesses b ON u.id = b.user_id
            WHERE u.email = ? AND u.is_active = True
        """, (user.email,))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 잘못되었습니다"
            )
        
        user_id, password_hash, business_name = result
        
        # 비밀번호 검증
        if not verify_password(user.password, password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 잘못되었습니다"
            )
        
        # JWT 토큰 생성
        access_token = create_access_token({"user_id": user_id})
        
        return {
            "message": "로그인이 완료되었습니다",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": user.email,
                "business_name": business_name
            }
        }
        
    finally:
        conn.close()

@api_router.get("/dashboard-data")
async def get_dashboard_data(user_id: int = Depends(verify_token)):
    """대시보드 데이터 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 비즈니스 정보
        cursor.execute("""
            SELECT business_name, industry, target_audience
            FROM businesses WHERE user_id = ?
        """, (user_id,))
        business = cursor.fetchone()
        
        # 이번 달 포스트 수
        cursor.execute("""
            SELECT COUNT(*) FROM content 
            WHERE business_id = (SELECT id FROM businesses WHERE user_id = ?)
            AND DATE(created_at) >= DATE('now', 'start of month')
        """, (user_id,))
        monthly_posts = cursor.fetchone()[0]
        
        # 예정된 포스트 수
        cursor.execute("""
            SELECT COUNT(*) FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            JOIN businesses b ON c.business_id = b.id
            WHERE b.user_id = ? AND cs.status = 'pending'
        """, (user_id,))
        pending_posts = cursor.fetchone()[0]
        
        return {
            "business": {
                "name": business[0] if business else "비즈니스",
                "industry": business[1] if business else "",
                "target": business[2] if business else ""
            },
            "stats": {
                "monthly_posts": monthly_posts,
                "pending_posts": pending_posts,
                "avg_engagement": 5.2,  # 임시값
                "followers": 1200  # 임시값
            }
        }
        
    finally:
        conn.close()

@api_router.post("/generate-content")
async def generate_content(user_id: int = Depends(verify_token)):
    """AI 콘텐츠 생성"""
    # instagram_auto_poster 모듈 사용
    try:
        from instagram_auto_poster import InstagramAutoPoster
        poster = InstagramAutoPoster()
        
        # 비즈니스 정보 가져오기
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT business_name, industry, target_audience, brand_voice
            FROM businesses WHERE user_id = ?
        """, (user_id,))
        business = cursor.fetchone()
        conn.close()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비즈니스 정보를 찾을 수 없습니다"
            )
        
        business_info = {
            'name': business[0],
            'industry': business[1],
            'target': business[2],
            'brand_voice': business[3]
        }
        
        # AI 콘텐츠 생성
        content = poster.generate_content_with_ai(business_info)
        image_url = poster.generate_image_with_dalle(f"{business[1]} marketing content")
        
        return {
            "content": content,
            "image_url": image_url,
            "message": "콘텐츠가 성공적으로 생성되었습니다"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}"
        )

@api_router.post("/update-business")
async def update_business_info(
    business_data: BusinessUpdate,
    user_id: int = Depends(verify_token)
):
    """비즈니스 정보 업데이트"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 업데이트할 필드들 구성
        update_fields = []
        update_values = []
        
        if business_data.business_name:
            update_fields.append("business_name = ?")
            update_values.append(business_data.business_name)
        
        if business_data.industry:
            update_fields.append("industry = ?")
            update_values.append(business_data.industry)
        
        if business_data.target_audience:
            update_fields.append("target_audience = ?")
            update_values.append(business_data.target_audience)
        
        if business_data.brand_voice:
            update_fields.append("brand_voice = ?")
            update_values.append(business_data.brand_voice)
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업데이트할 정보가 없습니다"
            )
        
        update_values.append(user_id)
        
        query = f"""
            UPDATE businesses 
            SET {', '.join(update_fields)}, updated_at = ?
            WHERE user_id = ?
        """
        update_values.insert(-1, datetime.now().isoformat())
        
        cursor.execute(query, update_values)
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="비즈니스 정보를 찾을 수 없습니다"
            )
        
        return {"message": "비즈니스 정보가 업데이트되었습니다"}
        
    finally:
        conn.close()

@api_router.delete("/logout")
async def logout(user_id: int = Depends(verify_token)):
    """로그아웃 (클라이언트에서 토큰 삭제)"""
    return {"message": "로그아웃되었습니다"}

@api_router.get("/scheduled-posts")
async def get_scheduled_posts(user_id: int = Depends(verify_token)):
    """예정된 포스트 목록"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT c.title, c.caption, cs.scheduled_datetime, cs.status
            FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            JOIN businesses b ON c.business_id = b.id
            WHERE b.user_id = ?
            ORDER BY cs.scheduled_datetime ASC
            LIMIT 10
        """, (user_id,))
        
        posts = cursor.fetchall()
        
        return {
            "posts": [
                {
                    "title": post[0],
                    "caption": post[1][:100] + "..." if len(post[1]) > 100 else post[1],
                    "scheduled_time": post[2],
                    "status": post[3]
                }
                for post in posts
            ]
        }
        
    finally:
        conn.close()

@api_router.get("/analytics")
async def get_analytics(user_id: int = Depends(verify_token)):
    """분석 데이터"""
    # 임시 분석 데이터 반환
    return {
        "engagement_rate": 5.2,
        "follower_growth": 8.1,
        "reach": 2500,
        "impressions": 15000,
        "likes": 450,
        "comments": 89,
        "shares": 23
    }