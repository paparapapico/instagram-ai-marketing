# main.py - 수정된 메인 애플리케이션
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

# 라우터 임포트
from api_routes import api_router
from database.init_db import init_database

app = FastAPI(
    title="Instagram AI Marketing Automation",
    description="AI 기반 Instagram 마케팅 자동화 플랫폼",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API 라우터 포함
app.include_router(api_router, prefix="/api", tags=["API"])

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    init_database()
    print("🚀 Instagram AI Marketing Platform Started!")

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """랜딩 페이지"""
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "year": datetime.now().year
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """대시보드 페이지"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request
    })

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )