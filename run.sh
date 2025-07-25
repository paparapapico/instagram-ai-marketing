#!/bin/bash
# run.sh - 프로젝트 실행 스크립트

echo "🚀 Starting Instagram AI Marketing Platform..."

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# 환경변수 로드
if [ -f ".env" ]; then
    echo "⚙️ Loading environment variables..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# 데이터베이스 마이그레이션 (필요한 경우)
echo "💾 Checking database..."
python -c "from main import init_database; init_database()"

# 백그라운드에서 스케줄러 시작
echo "⏰ Starting background scheduler..."
python scheduler.py &
SCHEDULER_PID=$!

# 웹 서버 시작
echo "🌐 Starting web server..."
echo "📱 Access URL: http://localhost:8000"
echo "📊 Admin URL: http://localhost:8000/admin/docs"
echo "🛑 Press Ctrl+C to stop"

# 종료 시 스케줄러도 함께 종료
trap "echo '🛑 Stopping services...'; kill $SCHEDULER_PID 2>/dev/null; exit" INT TERM

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 스케줄러 종료
kill $SCHEDULER_PID 2>/dev/null
