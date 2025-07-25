@echo off
REM run.bat - Windows 실행 스크립트

echo 🚀 Starting Instagram AI Marketing Platform...

REM 가상환경 활성화 (있는 경우)
if exist "venv\Scripts\activate.bat" (
    echo 📦 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM 데이터베이스 체크
echo 💾 Checking database...
python -c "from main import init_database; init_database()"

REM 스케줄러 백그라운드 시작
echo ⏰ Starting background scheduler...
start /b python scheduler.py

REM 웹 서버 시작
echo 🌐 Starting web server...
echo 📱 Access URL: http://localhost:8000
echo 📊 Admin URL: http://localhost:8000/admin/docs
echo 🛑 Press Ctrl+C to stop

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
