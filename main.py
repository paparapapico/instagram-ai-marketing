# main.py (수정 제안)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api_routes import api_router  # api_routes.py에서 라우터 가져오기
from database import init_database # DB 초기화 함수도 별도 파일로 분리하면 더 좋습니다.

app = FastAPI(title="Instagram AI Marketing Automation")

# CORS, Static Files 등 미들웨어 설정
app.add_middleware(...)
app.mount("/static", StaticFiles(directory="static"), name="static")

# API 라우터 포함
app.include_router(api_router)

@app.on_event("startup")
def startup_event():
    init_database()
    print("🚀 FastAPI App-i neomu joa~")