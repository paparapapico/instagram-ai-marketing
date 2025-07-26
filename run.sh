#!/bin/bash
# run.sh - 수정된 프로젝트 실행 스크립트

echo "🚀 Starting Instagram AI Marketing Platform..."

# 현재 디렉토리 확인
if [ ! -f "main.py" ]; then
    echo "❌ main.py 파일을 찾을 수 없습니다. 프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment activated"
    else
        echo "⚠️ Failed to activate virtual environment"
    fi
fi

# 환경변수 로드
if [ -f ".env" ]; then
    echo "⚙️ Loading environment variables..."
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "⚠️ .env file not found. Creating default..."
    cp .env.example .env 2>/dev/null || echo "Please create .env file manually"
fi

# Python 의존성 확인
echo "📋 Checking Python dependencies..."
python -c "import fastapi, uvicorn, sqlite3" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing required dependencies..."
    pip install -r requirements.txt
fi

# 필요한 디렉토리 생성
echo "📁 Creating necessary directories..."
mkdir -p database static/css static/js static/images templates utils components

# 데이터베이스 초기화
echo "💾 Initializing database..."
python -c "
import sys
sys.path.append('.')
try:
    from database.init_db import init_database
    init_database()
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'⚠️ Database initialization: {e}')
    # SQLite 기본 테이블 생성
    import sqlite3
    conn = sqlite3.connect('instagram_marketing.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT, created_at TEXT, is_active BOOLEAN)')
    conn.execute('CREATE TABLE IF NOT EXISTS businesses (id INTEGER PRIMARY KEY, user_id INTEGER, business_name TEXT, industry TEXT, created_at TEXT)')
    conn.close()
    print('✅ Basic database tables created')
"

# 백그라운드에서 스케줄러 시작
echo "⏰ Starting background scheduler..."
if [ -f "scheduler.py" ]; then
    python scheduler.py &
    SCHEDULER_PID=$!
    echo "✅ Scheduler started (PID: $SCHEDULER_PID)"
else
    echo "⚠️ scheduler.py not found, skipping scheduler"
    SCHEDULER_PID=""
fi

# 종료 시 스케줄러도 함께 종료
cleanup() {
    echo "🛑 Stopping services..."
    if [ ! -z "$SCHEDULER_PID" ]; then
        kill $SCHEDULER_PID 2>/dev/null
        echo "✅ Scheduler stopped"
    fi
    exit 0
}

trap cleanup INT TERM

# 웹 서버 시작
echo "🌐 Starting web server..."
echo "📱 Access URL: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "🛑 Press Ctrl+C to stop"
echo ""

# 서버 시작 전 포트 확인
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️ Port 8000 is already in use. Trying alternative ports..."
    for port in 8001 8002 8003; do
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "🔄 Using port $port instead"
            uvicorn main:app --host 0.0.0.0 --port $port --reload
            exit 0
        fi
    done
    echo "❌ No available ports found"
    exit 1
else
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi

# 정리
cleanup