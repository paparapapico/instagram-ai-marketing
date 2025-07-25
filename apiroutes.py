# api_routes.py - API 엔드포인트들
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import random

# 라우터 생성
api_router = APIRouter(prefix="/api", tags=["API"])

# main.py에서 임포트할 함수들 (실제로는 main.py에 있어야 함)
from main import (
    get_current_user, create_access_token, hash_password, verify_password,
    UserCreate, UserLogin, ContentRequest, ScheduleRequest, BusinessUpdate
)

@api_router.post("/register")
async def register_user(user: UserCreate):
    """사용자 회원가입 (향상된 버전)"""
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
        
        # 세션 저장
        cursor.execute('''
            INSERT INTO user_sessions (user_id, business_id, token, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (
            user_id, business_id, access_token, 
            (datetime.now() + timedelta(hours=24)).isoformat()
        ))
        
        # 기본 분석 데이터 생성
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT INTO analytics (business_id, date, followers_count, posts_count)
            VALUES (?, ?, ?, ?)
        ''', (business_id, today, 0, 0))
        
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

@api_router.post("/login")
async def login_user(user: UserLogin):
    """사용자 로그인 (향상된 버전)"""
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
        
        # 새 세션 생성
        cursor.execute('''
            INSERT INTO user_sessions (user_id, business_id, token, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (
            user_id, business_id, access_token,
            (datetime.now() + timedelta(hours=24)).isoformat()
        ))
        
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

@api_router.get("/dashboard-data")
async def get_dashboard_data(current_user: dict = Depends(get_current_user)):
    """대시보드 데이터 조회 (고급 분석 포함)"""
    try:
        business_id = current_user["business_id"]
        
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 비즈니스 기본 정보
        cursor.execute('''
            SELECT b.*, u.email, u.full_name, u.is_premium
            FROM businesses b
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ?
        ''', (business_id,))
        business_info = cursor.fetchone()
        
        # 이번 달 통계
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('''
            SELECT 
                COUNT(*) as total_posts,
                COUNT(CASE WHEN status = 'published' THEN 1 END) as published_posts,
                COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled_posts,
                AVG(CASE WHEN engagement_rate > 0 THEN engagement_rate END) as avg_engagement
            FROM content c
            WHERE c.business_id = ? AND strftime('%Y-%m', c.created_at) = ?
        ''', (business_id, current_month))
        monthly_stats = cursor.fetchone()
        
        # 최근 7일 성과
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT 
                SUM(likes_count) as total_likes,
                SUM(comments_count) as total_comments,
                SUM(shares_count) as total_shares,
                COUNT(*) as posts_count
            FROM content
            WHERE business_id = ? AND created_at >= ?
        ''', (business_id, week_ago))
        weekly_performance = cursor.fetchone()
        
        # 최근 분석 데이터
        cursor.execute('''
            SELECT followers_count, engagement_rate, reach, impressions
            FROM analytics
            WHERE business_id = ?
            ORDER BY date DESC
            LIMIT 1
        ''', (business_id,))
        analytics_data = cursor.fetchone()
        
        # 예정된 포스트
        cursor.execute('''
            SELECT COUNT(*) FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            WHERE cs.business_id = ? AND cs.status = 'pending'
            AND cs.scheduled_datetime > ?
        ''', (business_id, datetime.now().isoformat()))
        upcoming_posts = cursor.fetchone()[0]
        
        # 월별 성장률 계산 (가상 데이터)
        growth_rate = random.uniform(5.0, 25.0)
        
        conn.close()
        
        return {
            "success": True,
            "business": {
                "name": business_info[2] if business_info else "",
                "industry": business_info[3] if business_info else "",
                "plan": business_info[9] if business_info else "basic",
                "monthly_fee": business_info[10] if business_info else 150000,
                "instagram_connected": business_info[13] if business_info else False,
                "user_email": business_info[-3] if business_info else "",
                "is_premium": business_info[-1] if business_info else False
            },
            "stats": {
                "monthly_posts": monthly_stats[0] if monthly_stats else 0,
                "published_posts": monthly_stats[1] if monthly_stats else 0,
                "scheduled_posts": monthly_stats[2] if monthly_stats else 0,
                "upcoming_posts": upcoming_posts,
                "avg_engagement": round(monthly_stats[3] or 0, 2),
                "growth_rate": round(growth_rate, 1)
            },
            "performance": {
                "total_likes": weekly_performance[0] if weekly_performance else 0,
                "total_comments": weekly_performance[1] if weekly_performance else 0,
                "total_shares": weekly_performance[2] if weekly_performance else 0,
                "weekly_posts": weekly_performance[3] if weekly_performance else 0
            },
            "analytics": {
                "followers": analytics_data[0] if analytics_data else 0,
                "engagement_rate": round(analytics_data[1] or 0, 2),
                "reach": analytics_data[2] if analytics_data else 0,
                "impressions": analytics_data[3] if analytics_data else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}")

@api_router.post("/generate-content")
async def generate_content(
    request: ContentRequest,
    current_user: dict = Depends(get_current_user)
):
    """AI 콘텐츠 생성 (고급 버전)"""
    try:
        business_id = current_user["business_id"]
        
        # 비즈니스 정보 가져오기
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT business_name, industry, target_audience, brand_voice
            FROM businesses WHERE id = ?
        ''', (business_id,))
        business_data = cursor.fetchone()
        
        if not business_data:
            raise HTTPException(status_code=404, detail="비즈니스 정보를 찾을 수 없습니다")
        
        # AI 콘텐츠 생성 시뮬레이션 (실제로는 GPT-4/DALL-E 연동)
        business_name, industry, target_audience, brand_voice = business_data
        
        # 산업별 맞춤 콘텐츠 생성
        industry_templates = {
            "restaurant": {
                "captions": [
                    f"오늘의 특별 메뉴가 준비되었습니다! {business_name}에서만 만날 수 있는 특별한 맛을 경험해보세요 ✨",
                    f"신선한 재료로 정성스럽게 준비한 {business_name}의 시그니처 메뉴입니다 🍽️",
                    f"맛있는 순간을 {business_name}와 함께하세요! 여러분을 위한 특별한 요리가 기다리고 있습니다 👨‍🍳"
                ],
                "hashtags": ["#맛집", "#오늘뭐먹지", "#맛스타그램", "#푸드스타그램", "#맛있어요", "#신메뉴", "#맛집추천"]
            },
            "fashion": {
                "captions": [
                    f"새로운 시즌을 위한 {business_name}의 트렌디한 컬렉션을 만나보세요 👗",
                    f"스타일리시하고 편안한 {business_name}만의 특별한 아이템들을 소개합니다 ✨",
                    f"당신만의 개성을 표현할 수 있는 {business_name}의 신상품이 출시되었습니다 🌟"
                ],
                "hashtags": ["#패션", "#스타일", "#OOTD", "#트렌드", "#신상", "#패션스타그램", "#스타일링"]
            },
            "beauty": {
                "captions": [
                    f"자연스러운 아름다움을 위한 {business_name}의 프리미엄 제품을 소개합니다 💄",
                    f"건강한 피부를 위한 {business_name}의 스킨케어 루틴을 확인해보세요 ✨",
                    f"당신의 매력을 더욱 돋보이게 할 {business_name}의 뷰티 아이템들입니다 🌹"
                ],
                "hashtags": ["#뷰티", "#스킨케어", "#화장품", "#뷰티스타그램", "#셀프케어", "#글로우", "#K뷰티"]
            },
            "software": {
                "captions": [
                    f"비즈니스 성장을 위한 {business_name}의 혁신적인 솔루션을 경험해보세요 💼",
                    f"효율적인 업무 환경을 만들어주는 {business_name}의 최신 기술을 소개합니다 🚀",
                    f"디지털 트랜스포메이션의 시작, {business_name}와 함께하세요 ⭐"
                ],
                "hashtags": ["#IT", "#소프트웨어", "#디지털", "#혁신", "#기술", "#비즈니스", "#자동화"]
            }
        }
        
        # 기본 템플릿 (산업별 템플릿이 없는 경우)
        default_template = {
            "captions": [
                f"{business_name}와 함께하는 특별한 경험을 시작해보세요 ✨",
                f"고객 만족을 위해 끊임없이 노력하는 {business_name}입니다 🌟",
                f"품질과 서비스로 보답하는 {business_name}를 만나보세요 💫"
            ],
            "hashtags": ["#브랜드", "#품질", "#서비스", "#고객만족", "#추천", "#좋아요", "#팔로우"]
        }
        
        # 산업별 템플릿 선택
        template = industry_templates.get(industry, default_template)
        
        # 랜덤 콘텐츠 생성
        caption = random.choice(template["captions"])
        hashtags = random.sample(template["hashtags"], min(5, len(template["hashtags"])))
        
        # 이미지 URL 생성 (Canva나 Unsplash API 연동 예정)
        image_keywords = {
            "restaurant": "delicious food professional photography",
            "fashion": "fashion style trendy clothing",
            "beauty": "beauty cosmetics skincare",
            "software": "technology modern office business",
            "default": "business professional modern"
        }
        
        keyword = image_keywords.get(industry, image_keywords["default"])
        image_url = f"https://images.unsplash.com/photo-1600000000000-000000000000?auto=format&fit=crop&w=800&q=80&{keyword}"
        
        # 콘텐츠 데이터베이스에 저장
        cursor.execute('''
            INSERT INTO content (
                business_id, title, caption, hashtags, image_url, 
                content_type, platform, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            business_id, f"{business_name} - AI Generated Content",
            caption, json.dumps(hashtags), image_url,
            request.content_type, request.platform, "draft"
        ))
        
        content_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "content": {
                "id": content_id,
                "caption": caption,
                "hashtags": hashtags,
                "image_url": image_url,
                "content_type": request.content_type,
                "platform": request.platform,
                "business_name": business_name,
                "industry": industry
            },
            "message": "AI 콘텐츠가 성공적으로 생성되었습니다! 🎨"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"콘텐츠 생성 실패: {str(e)}")

@api_router.post("/schedule-content")
async def schedule_content(
    request: ScheduleRequest,
    current_user: dict = Depends(get_current_user)
):
    """콘텐츠 스케줄링 (고급 알고리즘)"""
    try:
        business_id = current_user["business_id"]
        
        # 최적 포스팅 시간 계산 (산업별)
        optimal_times = {
            "restaurant": ["11:30", "18:00", "20:00"],
            "fashion": ["10:00", "15:00", "19:00"],
            "beauty": ["09:00", "14:00", "21:00"],
            "software": ["09:00", "13:00", "17:00"],
            "default": ["10:00", "14:00", "19:00"]
        }
        
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 비즈니스 정보 가져오기
        cursor.execute("SELECT industry FROM businesses WHERE id = ?", (business_id,))
        industry_result = cursor.fetchone()
        industry = industry_result[0] if industry_result else "default"
        
        # 시작 날짜 설정
        start_date = datetime.strptime(request.start_date, '%Y-%m-%d') if request.start_date else datetime.now()
        
        # 주간 스케줄 생성
        scheduled_posts = []
        times = optimal_times.get(industry, optimal_times["default"])
        
        for week in range(4):  # 4주간 스케줄
            for day in range(7):  # 7일
                post_date = start_date + timedelta(days=week*7 + day)
                
                # 주말에는 포스팅 수 조정
                posts_today = request.posts_per_week // 7
                if day in [5, 6]:  # 토, 일
                    posts_today += 1
                
                for post_num in range(posts_today):
                    if post_num < len(times):
                        post_time = times[post_num]
                        scheduled_datetime = f"{post_date.strftime('%Y-%m-%d')} {post_time}:00"
                        
                        # 임시 콘텐츠 생성
                        cursor.execute('''
                            INSERT INTO content (
                                business_id, title, caption, content_type, status
                            ) VALUES (?, ?, ?, ?, ?)
                        ''', (
                            business_id,
                            f"Scheduled Post {week+1}-{day+1}-{post_num+1}",
                            "AI가 생성할 예정인 콘텐츠입니다.",
                            "post",
                            "scheduled"
                        ))
                        
                        content_id = cursor.lastrowid
                        
                        # 스케줄에 추가
                        cursor.execute('''
                            INSERT INTO content_schedule (
                                business_id, content_id, scheduled_datetime, status
                            ) VALUES (?, ?, ?, ?)
                        ''', (business_id, content_id, scheduled_datetime, "pending"))
                        
                        scheduled_posts.append({
                            "date": post_date.strftime('%Y-%m-%d'),
                            "time": post_time,
                            "content_id": content_id
                        })
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"4주간 총 {len(scheduled_posts)}개의 포스트가 스케줄되었습니다! 📅",
            "schedule_info": {
                "posts_per_week": request.posts_per_week,
                "total_posts": len(scheduled_posts),
                "start_date": start_date.strftime('%Y-%m-%d'),
                "industry": industry,
                "optimal_times": times
            },
            "scheduled_posts": scheduled_posts[:10]  # 처음 10개만 미리보기
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스케줄링 실패: {str(e)}")

@api_router.get("/scheduled-posts")
async def get_scheduled_posts(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """예정된 포스트 목록 (페이지네이션)"""
    try:
        business_id = current_user["business_id"]
        offset = (page - 1) * limit
        
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 전체 개수
        cursor.execute('''
            SELECT COUNT(*) FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            WHERE cs.business_id = ?
        ''', (business_id,))
        total_count = cursor.fetchone()[0]
        
        # 페이지네이션된 결과
        cursor.execute('''
            SELECT 
                cs.id, cs.scheduled_datetime, cs.status, cs.created_at,
                c.title, c.caption, c.image_url, c.content_type,
                cs.post_id, cs.error_message
            FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            WHERE cs.business_id = ?
            ORDER BY cs.scheduled_datetime DESC
            LIMIT ? OFFSET ?
        ''', (business_id, limit, offset))
        
        schedules = cursor.fetchall()
        conn.close()
        
        formatted_schedules = []
        for schedule in schedules:
            formatted_schedules.append({
                "id": schedule[0],
                "scheduled_datetime": schedule[1],
                "status": schedule[2],
                "created_at": schedule[3],
                "content": {
                    "title": schedule[4],
                    "caption": schedule[5][:100] + "..." if len(schedule[5]) > 100 else schedule[5],
                    "image_url": schedule[6],
                    "content_type": schedule[7]
                },
                "post_id": schedule[8],
                "error_message": schedule[9],
                "status_text": {
                    "pending": "⏳ 대기중",
                    "completed": "✅ 완료",
                    "failed": "❌ 실패",
                    "cancelled": "🚫 취소됨"
                }.get(schedule[2], schedule[2])
            })
        
        return {
            "success": True,
            "schedules": formatted_schedules,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스케줄 조회 실패: {str(e)}")

@api_router.post("/update-business")
async def update_business_info(
    business_update: BusinessUpdate,
    current_user: dict = Depends(get_current_user)
):
    """비즈니스 정보 업데이트"""
    try:
        business_id = current_user["business_id"]
        
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 업데이트할 필드들 준비
        update_fields = []
        update_values = []
        
        for field, value in business_update.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if update_fields:
            update_values.append(datetime.now().isoformat())
            update_values.append(business_id)
            
            query = f'''
                UPDATE businesses 
                SET {", ".join(update_fields)}, updated_at = ?
                WHERE id = ?
            '''
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="비즈니스 정보를 찾을 수 없습니다")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "비즈니스 정보가 성공적으로 업데이트되었습니다! ✨"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업데이트 실패: {str(e)}")

@api_router.get("/analytics")
async def get_analytics(
    period: str = "7d",
    current_user: dict = Depends(get_current_user)
):
    """분석 데이터 조회"""
    try:
        business_id = current_user["business_id"]
        
        # 기간별 데이터 계산
        if period == "7d":
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        elif period == "30d":
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif period == "90d":
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        else:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 가상 분석 데이터 생성 (실제로는 Instagram API에서 가져옴)
        analytics_data = []
        for i in range(int(period.replace('d', ''))):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            analytics_data.append({
                "date": date,
                "followers": random.randint(980, 1020),
                "engagement_rate": round(random.uniform(2.5, 8.5), 2),
                "reach": random.randint(800, 1500),
                "impressions": random.randint(1200, 2500),
                "profile_visits": random.randint(50, 150),
                "website_clicks": random.randint(10, 50)
            })
        
        # 성장률 계산
        if len(analytics_data) >= 2:
            growth_rate = ((analytics_data[0]["followers"] - analytics_data[-1]["followers"]) / analytics_data[-1]["followers"]) * 100
        else:
            growth_rate = 0
        
        conn.close()
        
        return {
            "success": True,
            "period": period,
            "analytics": analytics_data,
            "summary": {
                "total_followers": analytics_data[0]["followers"] if analytics_data else 0,
                "avg_engagement": round(sum(d["engagement_rate"] for d in analytics_data) / len(analytics_data), 2) if analytics_data else 0,
                "total_reach": sum(d["reach"] for d in analytics_data),
                "total_impressions": sum(d["impressions"] for d in analytics_data),
                "growth_rate": round(growth_rate, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 데이터 조회 실패: {str(e)}")

@api_router.delete("/logout")
async def logout_user(current_user: dict = Depends(get_current_user)):
    """사용자 로그아웃"""
    try:
        user_id = current_user["user_id"]
        
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 현재 사용자의 모든 세션 비활성화
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = FALSE 
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "안전하게 로그아웃되었습니다 👋"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 실패: {str(e)}")