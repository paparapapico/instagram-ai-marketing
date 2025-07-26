<<<<<<< HEAD
# 🚀 Instagram AI Marketing Automation Platform

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
venv\Scripts\activate

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
=======
# instagram-ai-marketing
>>>>>>> f8c90708105d8ac48ed9fa77b47be5465eb1a6a9
