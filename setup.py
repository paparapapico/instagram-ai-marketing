# setup.py - 프로젝트 설정 및 실행 스크립트

import os
import subprocess
import sys
from pathlib import Path

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
        print(f"✅ Created directory: {directory}")

def install_dependencies():
    """필요한 Python 패키지 설치"""
    dependencies = [
        "fastapi",
        "uvicorn[standard]",
        "jinja2",
        "python-multipart",
        "python-jose[cryptography]",
        "bcrypt",
        "sqlite3",  # 기본 내장
        "requests",
        "openai",  # OpenAI API 연동용
        "Pillow",  # 이미지 처리용
        "schedule",  # 스케줄링용
        "python-dotenv"  # 환경변수 관리용
    ]
    
    print("📦 Installing Python dependencies...")
    for dep in dependencies:
        try:
            if dep != "sqlite3":  # sqlite3는 기본 내장
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                print(f"✅ Installed: {dep}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install: {dep}")

def create_env_file():
    """환경변수 파일 생성"""
    env_content = """# Instagram AI Marketing Platform Environment Variables

# FastAPI Settings
SECRET_KEY=your-ultra-secure-secret-key-change-in-production-2024
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite:///./instagram_marketing.db

# OpenAI API (콘텐츠 생성용)
OPENAI_API_KEY=your-openai-api-key-here

# Instagram API (실제 포스팅용)
INSTAGRAM_ACCESS_TOKEN=your-instagram-access-token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your-business-account-id

# Email Settings (알림용)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Canva API (이미지 생성 대안)
CANVA_API_KEY=your-canva-api-key

# Redis (선택사항 - 캐싱용)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ Created .env file")

def create_requirements_txt():
    """requirements.txt 파일 생성"""
    requirements = """fastapi==0.104.1
uvicorn[standard]==0.24.0
jinja2==3.1.2
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
bcrypt==4.1.2
requests==2.31.0
openai==1.3.7
Pillow==10.1.0
schedule==1.2.0
python-dotenv==1.0.0
aiofiles==23.2.1
httpx==0.25.2
pydantic==2.5.1
"""
    
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)
    
    print("✅ Created requirements.txt")

def create_dockerfile():
    """Docker 파일 생성"""
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    
    with open("Dockerfile", "w", encoding="utf-8") as f:
        f.write(dockerfile_content)
    
    print("✅ Created Dockerfile")

def create_docker_compose():
    """Docker Compose 파일 생성"""
    compose_content = """version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - ./data:/app/data
    environment:
      - DEBUG=True
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  scheduler:
    build: .
    command: python scheduler.py
    volumes:
      - .:/app
      - ./data:/app/data
    depends_on:
      - web
      - redis
    restart: unless-stopped

volumes:
  redis_data:
"""
    
    with open("docker-compose.yml", "w", encoding="utf-8") as f:
        f.write(compose_content)
    
    print("✅ Created docker-compose.yml")

def create_gitignore():
    """.gitignore 파일 생성"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment Variables
.env
.env.local
.env.production

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Uploads
uploads/
temp/

# API Keys
secrets/
keys/
"""
    
    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    
    print("✅ Created .gitignore")

def create_scheduler():
    """백그라운드 스케줄러 생성"""
    scheduler_content = """# scheduler.py - 백그라운드 작업 스케줄러

import schedule
import time
import sqlite3
import asyncio
from datetime import datetime, timedelta
import logging
from complete_automation_system import InstagramMarketingBusiness
from instagram_auto_poster import InstagramAutoPoster

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 시스템 초기화
business_system = InstagramMarketingBusiness()
poster_system = InstagramAutoPoster()

def process_scheduled_posts():
    \"\"\"예정된 포스트 처리\"\"\"
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 현재 시간 기준으로 처리할 포스트 조회
        now = datetime.now().isoformat()
        cursor.execute('''
            SELECT cs.id, cs.business_id, cs.content_id, c.caption, c.image_url, c.hashtags
            FROM content_schedule cs
            JOIN content c ON cs.content_id = c.id
            WHERE cs.scheduled_datetime <= ? AND cs.status = 'pending'
        ''', (now,))
        
        pending_posts = cursor.fetchall()
        
        for post in pending_posts:
            schedule_id, business_id, content_id, caption, image_url, hashtags = post
            
            try:
                # 비즈니스 정보 가져오기
                cursor.execute("SELECT business_name, industry FROM businesses WHERE id = ?", (business_id,))
                business_info = cursor.fetchone()
                
                if business_info:
                    business_data = {
                        'name': business_info[0],
                        'industry': business_info[1],
                        'caption': caption,
                        'image_url': image_url,
                        'hashtags': hashtags
                    }
                    
                    # Instagram에 포스팅
                    post_id = poster_system.post_to_instagram(business_data)
                    
                    if post_id:
                        # 성공적으로 포스팅됨
                        cursor.execute('''
                            UPDATE content_schedule 
                            SET status = 'completed', post_id = ?, completed_at = ?
                            WHERE id = ?
                        ''', (post_id, datetime.now().isoformat(), schedule_id))
                        
                        cursor.execute('''
                            UPDATE content 
                            SET status = 'published', published_at = ?
                            WHERE id = ?
                        ''', (datetime.now().isoformat(), content_id))
                        
                        logger.info(f"Successfully posted content {content_id} for business {business_id}")
                    else:
                        # 포스팅 실패
                        cursor.execute('''
                            UPDATE content_schedule 
                            SET status = 'failed', retry_count = retry_count + 1,
                                error_message = 'Instagram posting failed'
                            WHERE id = ?
                        ''', (schedule_id,))
                        
                        logger.error(f"Failed to post content {content_id} for business {business_id}")
                
            except Exception as e:
                # 개별 포스트 처리 실패
                cursor.execute('''
                    UPDATE content_schedule 
                    SET status = 'failed', retry_count = retry_count + 1,
                        error_message = ?
                    WHERE id = ?
                ''', (str(e), schedule_id))
                
                logger.error(f"Error processing post {content_id}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        if pending_posts:
            logger.info(f"Processed {len(pending_posts)} scheduled posts")
            
    except Exception as e:
        logger.error(f"Error in process_scheduled_posts: {str(e)}")

def generate_daily_content():
    \"\"\"일일 콘텐츠 자동 생성\"\"\"
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 활성 비즈니스 목록 조회
        cursor.execute('''
            SELECT b.id, b.business_name, b.industry, b.target_audience, b.brand_voice
            FROM businesses b
            JOIN users u ON b.user_id = u.id
            WHERE u.is_active = TRUE
        ''')
        
        businesses = cursor.fetchall()
        
        for business in businesses:
            business_id, name, industry, target_audience, brand_voice = business
            
            # 오늘 생성된 콘텐츠가 있는지 확인
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM content 
                WHERE business_id = ? AND DATE(created_at) = ?
            ''', (business_id, today))
            
            today_content_count = cursor.fetchone()[0]
            
            # 하루에 최대 3개까지만 자동 생성
            if today_content_count < 3:
                business_info = {
                    'name': name,
                    'industry': industry,
                    'target_audience': target_audience,
                    'brand_voice': brand_voice
                }
                
                # AI 콘텐츠 생성
                content = poster_system.generate_content_with_ai(business_info)
                image_url = poster_system.generate_image_with_dalle(f"{industry} marketing content")
                
                # 데이터베이스에 저장
                cursor.execute('''
                    INSERT INTO content (
                        business_id, title, caption, hashtags, image_url, 
                        content_type, platform, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    business_id, f"Auto-generated content for {name}",
                    content['caption'], json.dumps(content['hashtags']), 
                    image_url, 'post', 'instagram', 'draft'
                ))
                
                logger.info(f"Generated daily content for business {business_id}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error in generate_daily_content: {str(e)}")

def cleanup_old_data():
    \"\"\"오래된 데이터 정리\"\"\"
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 30일 이상 된 완료된 스케줄 삭제
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('''
            DELETE FROM content_schedule 
            WHERE status = 'completed' AND completed_at < ?
        ''', (cutoff_date,))
        
        # 90일 이상 된 비활성 세션 삭제
        session_cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        cursor.execute('''
            DELETE FROM user_sessions 
            WHERE is_active = FALSE AND created_at < ?
        ''', (session_cutoff,))
        
        conn.commit()
        conn.close()
        
        logger.info("Completed data cleanup")
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {str(e)}")

def update_analytics():
    \"\"\"분석 데이터 업데이트\"\"\"
    try:
        conn = sqlite3.connect("instagram_marketing.db")
        cursor = conn.cursor()
        
        # 각 비즈니스의 오늘 분석 데이터 생성/업데이트
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("SELECT id FROM businesses")
        businesses = cursor.fetchall()
        
        for (business_id,) in businesses:
            # 오늘 분석 데이터가 있는지 확인
            cursor.execute('''
                SELECT id FROM analytics 
                WHERE business_id = ? AND date = ?
            ''', (business_id, today))
            
            existing = cursor.fetchone()
            
            # 가상 분석 데이터 생성 (실제로는 Instagram API에서 가져옴)
            import random
            followers = random.randint(1000, 10000)
            engagement_rate = round(random.uniform(2.0, 8.0), 2)
            reach = random.randint(500, 5000)
            impressions = random.randint(1000, 15000)
            
            if existing:
                # 업데이트
                cursor.execute('''
                    UPDATE analytics 
                    SET followers_count = ?, engagement_rate = ?, 
                        reach = ?, impressions = ?
                    WHERE business_id = ? AND date = ?
                ''', (followers, engagement_rate, reach, impressions, business_id, today))
            else:
                # 새로 생성
                cursor.execute('''
                    INSERT INTO analytics (
                        business_id, date, followers_count, engagement_rate,
                        reach, impressions
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (business_id, today, followers, engagement_rate, reach, impressions))
        
        conn.commit()
        conn.close()
        
        logger.info("Updated analytics data")
        
    except Exception as e:
        logger.error(f"Error in update_analytics: {str(e)}")

# 스케줄 설정
def setup_scheduler():
    \"\"\"스케줄러 설정\"\"\"
    # 매 5분마다 예정된 포스트 확인
    schedule.every(5).minutes.do(process_scheduled_posts)
    
    # 매일 오전 9시에 콘텐츠 자동 생성
    schedule.every().day.at("09:00").do(generate_daily_content)
    
    # 매일 자정에 분석 데이터 업데이트
    schedule.every().day.at("00:00").do(update_analytics)
    
    # 매주 일요일 자정에 데이터 정리
    schedule.every().sunday.at("00:00").do(cleanup_old_data)
    
    logger.info("Scheduler setup completed")

def main():
    \"\"\"메인 스케줄러 실행\"\"\"
    setup_scheduler()
    
    logger.info("🚀 Instagram Marketing Scheduler Started")
    logger.info("⏰ Running scheduled tasks...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    main()
"""
    
    with open("scheduler.py", "w", encoding="utf-8") as f:
        f.write(scheduler_content)
    
    print("✅ Created scheduler.py")

def create_run_script():
    """실행 스크립트 생성"""
    run_script = """#!/bin/bash
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
"""
    
    with open("run.sh", "w", encoding="utf-8") as f:
        f.write(run_script)
    
    # 실행 권한 부여 (Unix 시스템)
    try:
        os.chmod("run.sh", 0o755)
    except:
        pass
    
    print("✅ Created run.sh")

def create_windows_batch():
    """Windows 배치 파일 생성"""
    batch_content = """@echo off
REM run.bat - Windows 실행 스크립트

echo 🚀 Starting Instagram AI Marketing Platform...

REM 가상환경 활성화 (있는 경우)
if exist "venv\\Scripts\\activate.bat" (
    echo 📦 Activating virtual environment...
    call venv\\Scripts\\activate.bat
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
"""
    
    with open("run.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print("✅ Created run.bat")

def create_readme():
    """README 파일 생성"""
    readme_content = """# 🚀 Instagram AI Marketing Automation Platform

AI 기반 Instagram 마케팅 자동화 플랫폼입니다. GPT-4와 DALL-E를 활용한 콘텐츠 자동 생성, 스마트 스케줄링, 실시간 분석을 제공합니다.

## ✨ 주요 기능

- 🤖 **AI 콘텐츠 생성**: GPT-4와 DALL-E를 활용한 자동 콘텐츠 생성
- ⏰ **스마트 스케줄링**: 최적 시간 자동 분석 및 포스팅
- 📊 **실시간 분석**: 성과 분석 및 인사이트 제공
- 🎨 **프리미엄 UI/UX**: 토스, 삼성 수준의 세련된 인터페이스
- 🔐 **보안**: JWT 인증, 암호화된 데이터 저장
- 📱 **반응형**: 모바일, 태블릿, 데스크톱 최적화

## 🛠️ 기술 스택

### Backend
- **FastAPI**: 고성능 Python 웹 프레임워크
- **SQLite**: 경량 데이터베이스
- **JWT**: 보안 인증
- **OpenAI API**: GPT-4, DALL-E 연동

### Frontend
- **Bootstrap 5**: 반응형 UI 프레임워크
- **Chart.js**: 데이터 시각화
- **AOS**: 스크롤 애니메이션
- **Font Awesome**: 아이콘

### DevOps
- **Docker**: 컨테이너화
- **Redis**: 캐싱 (선택사항)
- **Nginx**: 리버스 프록시 (프로덕션)

## 🚀 빠른 시작

### 1. 저장소 복제
```bash
git clone <repository-url>
cd instagram-ai-marketing
```

### 2. 가상환경 생성 (권장)
```bash
python -m venv venv

# Windows
venv\\Scripts\\activate

# macOS/Linux  
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정
`.env` 파일을 수정하여 API 키를 설정하세요:
```env
OPENAI_API_KEY=your-openai-api-key-here
SECRET_KEY=your-secret-key-here
```

### 5. 실행

#### 자동 실행 (권장)
```bash
# Unix/Linux/macOS
./run.sh

# Windows
run.bat
```

#### 수동 실행
```bash
# 웹 서버만 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 별도 터미널에서 스케줄러 실행
python scheduler.py
```

### 6. 접속
- **메인 사이트**: http://localhost:8000
- **API 문서**: http://localhost:8000/admin/docs
- **ReDoc**: http://localhost:8000/admin/redoc

## 🐳 Docker 실행

### Docker Compose 사용 (권장)
```bash
docker-compose up -d
```

### Docker 단독 실행
```bash
# 이미지 빌드
docker build -t instagram-ai-marketing .

# 컨테이너 실행
docker run -p 8000:8000 instagram-ai-marketing
```

## 📁 프로젝트 구조

```
instagram-ai-marketing/
├── main.py                 # FastAPI 메인 애플리케이션
├── api_routes.py          # API 엔드포인트
├── scheduler.py           # 백그라운드 스케줄러
├── complete_automation_system.py  # 비즈니스 로직
├── instagram_auto_poster.py       # Instagram 연동
├── templates/             # HTML 템플릿
│   ├── landing.html      # 랜딩 페이지
│   └── dashboard.html    # 대시보드
├── static/               # 정적 파일
│   ├── css/             # 스타일시트
│   ├── js/              # JavaScript
│   └── images/          # 이미지
├── database/            # 데이터베이스 관련
├── utils/              # 유틸리티 함수
├── .env               # 환경변수
├── requirements.txt   # Python 의존성
├── Dockerfile        # Docker 설정
├── docker-compose.yml # Docker Compose 설정
└── README.md         # 프로젝트 문서
```

## 🔧 설정

### OpenAI API 설정
1. [OpenAI Platform](https://platform.openai.com)에서 API 키 발급
2. `.env` 파일에 `OPENAI_API_KEY` 설정

### Instagram API 설정
1. [Instagram Basic Display API](https://developers.facebook.com/docs/instagram-basic-display-api) 설정
2. 비즈니스 계정 연동
3. 액세스 토큰 발급

### SMTP 설정 (알림용)
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

## 📊 API 엔드포인트

### 인증
- `POST /api/register` - 회원가입
- `POST /api/login` - 로그인
- `DELETE /api/logout` - 로그아웃

### 대시보드
- `GET /api/dashboard-data` - 대시보드 데이터
- `GET /api/analytics` - 분석 데이터

### 콘텐츠
- `POST /api/generate-content` - AI 콘텐츠 생성
- `GET /api/scheduled-posts` - 예정된 포스트 조회
- `POST /api/schedule-content` - 콘텐츠 스케줄링

### 설정
- `POST /api/update-business` - 비즈니스 정보 업데이트

## 🎨 UI/UX 특징

### 디자인 시스템
- **색상**: 그라데이션 기반 모던 컬러 팔레트
- **타이포그래피**: Pretendard 폰트 사용
- **아이콘**: Font Awesome 6
- **애니메이션**: AOS, CSS Transform

### 반응형 디자인
- **Mobile First**: 모바일 우선 설계
- **Breakpoints**: Bootstrap 5 그리드 시스템
- **Touch Friendly**: 터치 인터페이스 최적화

### 사용자 경험
- **로딩 상태**: 스켈레톤 UI, 스피너
- **피드백**: 토스트 알림, 모달
- **접근성**: ARIA 레이블, 키보드 네비게이션

## 🔒 보안

### 인증 및 인가
- **JWT 토큰**: 상태 없는 인증
- **비밀번호 해싱**: bcrypt 사용
- **세션 관리**: 토큰 만료, 갱신

### 데이터 보호
- **SQL 인젝션 방지**: 파라미터화된 쿼리
- **XSS 방지**: 입력 데이터 검증
- **CSRF 방지**: SameSite 쿠키

## 📈 성능 최적화

### 프론트엔드
- **Code Splitting**: 페이지별 JavaScript 분할
- **Lazy Loading**: 이미지, 콘텐츠 지연 로딩
- **Caching**: 브라우저 캐싱 활용

### 백엔드
- **DB 최적화**: 인덱스, 쿼리 최적화
- **Redis 캐싱**: 세션, API 응답 캐시
- **비동기 처리**: FastAPI 비동기 엔드포인트

## 🚀 배포

### 프로덕션 설정
```bash
# 환경변수 설정
export DEBUG=False
export SECRET_KEY=production-secret-key

# 정적 파일 최적화
python -m http.server 8080 --directory static
```

### Nginx 설정
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/static/;
        expires 1y;
    }
}
```

## 🧪 테스트

```bash
# 단위 테스트
python -m pytest tests/

# 커버리지 확인
python -m pytest --cov=. tests/
```

## 📝 라이센스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 지원

- **이슈**: [GitHub Issues](https://github.com/username/repo/issues)
- **문서**: [Wiki](https://github.com/username/repo/wiki)
- **이메일**: support@example.com

## 🎯 로드맵

### v1.1 (예정)
- [ ] Instagram 스토리 자동 생성
- [ ] 릴스 콘텐츠 지원
- [ ] 다국어 지원

### v1.2 (예정)  
- [ ] Facebook, Twitter 연동
- [ ] 고급 분석 대시보드
- [ ] A/B 테스트 기능

### v2.0 (예정)
- [ ] 모바일 앱
- [ ] AI 챗봇 통합
- [ ] 엔터프라이즈 기능

---

Made with ❤️ by AI & Human Collaboration
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ Created README.md")

def main():
    """메인 설정 함수"""
    print("🚀 Instagram AI Marketing Platform Setup")
    print("=" * 50)
    
    # 프로젝트 구조 생성
    create_project_structure()
    
    # 설정 파일들 생성
    create_env_file()
    create_requirements_txt()
    create_dockerfile()
    create_docker_compose()
    create_gitignore()
    create_scheduler()
    create_run_script()
    create_windows_batch()
    create_readme()
    
    print("\n" + "=" * 50)
    print("✅ 프로젝트 설정 완료!")
    print("\n📋 다음 단계:")
    print("1. .env 파일에서 API 키 설정")
    print("2. pip install -r requirements.txt")
    print("3. ./run.sh 또는 run.bat 실행")
    print("4. http://localhost:8000 접속")
    print("\n🎯 Happy Coding!")

if __name__ == "__main__":
    main()