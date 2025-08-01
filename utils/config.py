# utils/config.py - 보안 강화된 설정 관리
import os
import secrets
from dotenv import load_dotenv
from typing import Optional
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityConfig:
    """🔒 보안 설정 관리 클래스"""
    
    def __init__(self):
        """환경변수 로드 및 검증"""
        self.load_environment()
        self.validate_critical_settings()
    
    def load_environment(self):
        """환경변수 로드"""
        # .env 파일 로드
        env_loaded = load_dotenv()
        
        if env_loaded:
            logger.info("✅ .env 파일이 로드되었습니다.")
        else:
            logger.warning("⚠️ .env 파일을 찾을 수 없습니다. 환경변수를 직접 확인합니다.")
        
        # 환경 확인
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        if self.environment == 'production' and self.debug:
            logger.error("❌ 프로덕션 환경에서 DEBUG=True는 보안 위험입니다!")
            raise ValueError("Production environment cannot have DEBUG=True")
    
    def validate_critical_settings(self):
        """🔒 중요한 설정값 검증"""
        errors = []
        
        # SECRET_KEY 검증
        secret_key = self.get_secret_key()
        if not secret_key:
            errors.append("SECRET_KEY가 설정되지 않았습니다.")
        elif len(secret_key) < 32:
            errors.append("SECRET_KEY는 최소 32자 이상이어야 합니다.")
        elif secret_key in ['your-secret-key-here', 'change-this']:
            errors.append("SECRET_KEY를 기본값에서 변경해야 합니다.")
        
        # 프로덕션 환경 추가 검증
        if self.environment == 'production':
            if self.debug:
                errors.append("프로덕션에서는 DEBUG=False여야 합니다.")
            
            # HTTPS 강제 확인
            if not self.get_ssl_required():
                logger.warning("⚠️ 프로덕션 환경에서 HTTPS 사용을 권장합니다.")
        
        if errors:
            logger.error("❌ 보안 설정 오류:")
            for error in errors:
                logger.error(f"   - {error}")
            raise ValueError("보안 설정을 확인해주세요.")
        
        logger.info("✅ 보안 설정 검증 완료")
    
    # 🔒 보안 관련 설정
    def get_secret_key(self) -> str:
        """JWT 암호화용 비밀키"""
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            if self.environment == 'development':
                # 개발 환경에서만 자동 생성
                secret_key = secrets.token_urlsafe(32)
                logger.warning(f"⚠️ SECRET_KEY가 자동 생성되었습니다: {secret_key}")
                logger.warning("프로덕션 배포 전에 고정된 키로 설정하세요!")
            else:
                raise ValueError("SECRET_KEY가 설정되지 않았습니다.")
        return secret_key
    
    def get_jwt_algorithm(self) -> str:
        """JWT 알고리즘"""
        return os.getenv('JWT_ALGORITHM', 'HS256')
    
    def get_access_token_expire_hours(self) -> int:
        """액세스 토큰 만료 시간 (시간)"""
        return int(os.getenv('ACCESS_TOKEN_EXPIRE_HOURS', '24'))
    
    def get_ssl_required(self) -> bool:
        """HTTPS 강제 여부"""
        return os.getenv('SSL_REQUIRED', 'False').lower() == 'true'
    
    # 🤖 AI 관련 설정
    def get_openai_api_key(self) -> Optional[str]:
        """OpenAI API 키"""
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and api_key.startswith('sk-'):
            return api_key
        elif api_key:
            logger.warning("⚠️ OpenAI API 키 형식이 올바르지 않습니다.")
        return None
    
    def get_openai_model(self) -> str:
        """OpenAI 모델명"""
        return os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    def get_openai_max_tokens(self) -> int:
        """OpenAI 최대 토큰 수"""
        return int(os.getenv('OPENAI_MAX_TOKENS', '500'))
    
    # 📱 Instagram 관련 설정
    def get_instagram_access_token(self) -> Optional[str]:
        """Instagram 액세스 토큰"""
        token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        if token and len(token) > 50:  # 기본적인 길이 검증
            return token
        elif token:
            logger.warning("⚠️ Instagram 액세스 토큰이 너무 짧습니다.")
        return None
    
    def get_instagram_business_account_id(self) -> Optional[str]:
        """Instagram 비즈니스 계정 ID"""
        account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        if account_id and account_id.isdigit():
            return account_id
        elif account_id:
            logger.warning("⚠️ Instagram 비즈니스 계정 ID는 숫자여야 합니다.")
        return None
    
    def get_instagram_app_id(self) -> Optional[str]:
        """Instagram 앱 ID"""
        return os.getenv('INSTAGRAM_APP_ID')
    
    def get_instagram_app_secret(self) -> Optional[str]:
        """Instagram 앱 시크릿"""
        return os.getenv('INSTAGRAM_APP_SECRET')
    
    # 🗄️ 데이터베이스 설정
    def get_database_url(self) -> str:
        """데이터베이스 URL"""
        return os.getenv('DATABASE_URL', 'sqlite:///./instagram_marketing.db')
    
    def get_database_pool_size(self) -> int:
        """데이터베이스 연결 풀 크기"""
        return int(os.getenv('DATABASE_POOL_SIZE', '10'))
    
    def get_database_timeout(self) -> int:
        """데이터베이스 타임아웃 (초)"""
        return int(os.getenv('DATABASE_TIMEOUT', '30'))
    
    # 🌐 서버 설정
    def get_host(self) -> str:
        """서버 호스트"""
        return os.getenv('HOST', '0.0.0.0')
    
    def get_port(self) -> int:
        """서버 포트"""
        return int(os.getenv('PORT', '8000'))
    
    def get_workers(self) -> int:
        """워커 프로세스 수"""
        return int(os.getenv('WORKERS', '1'))
    
    def get_reload(self) -> bool:
        """자동 리로드 여부"""
        return os.getenv('RELOAD', 'False').lower() == 'true'
    
    # 📧 이메일 설정
    def get_smtp_config(self) -> dict:
        """SMTP 설정"""
        return {
            'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'use_tls': os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
        }
    
    # 📊 로깅 설정
    def get_log_level(self) -> str:
        """로그 레벨"""
        return os.getenv('LOG_LEVEL', 'INFO')
    
    def get_log_file(self) -> str:
        """로그 파일 경로"""
        return os.getenv('LOG_FILE', 'logs/app.log')
    
    # 🚦 레이트 리미팅
    def get_rate_limit_per_minute(self) -> int:
        """분당 요청 제한"""
        return int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    
    def get_rate_limit_per_hour(self) -> int:
        """시간당 요청 제한"""
        return int(os.getenv('RATE_LIMIT_PER_HOUR', '1000'))
    
    # 🎨 UI 설정
    def get_app_name(self) -> str:
        """앱 이름"""
        return os.getenv('APP_NAME', 'Instagram AI Marketing')
    
    def get_app_version(self) -> str:
        """앱 버전"""
        return os.getenv('APP_VERSION', '1.0.0')
    
    def get_brand_color(self) -> str:
        """브랜드 컬러"""
        return os.getenv('BRAND_COLOR', '#007bff')
    
    # 🔍 설정 상태 확인
    def check_ai_features_available(self) -> bool:
        """AI 기능 사용 가능 여부"""
        return self.get_openai_api_key() is not None
    
    def check_instagram_features_available(self) -> bool:
        """Instagram 기능 사용 가능 여부"""
        return (self.get_instagram_access_token() is not None and 
                self.get_instagram_business_account_id() is not None)
    
    def get_feature_status(self) -> dict:
        """기능별 사용 가능 상태"""
        return {
            'ai_content_generation': self.check_ai_features_available(),
            'instagram_posting': self.check_instagram_features_available(),
            'email_notifications': bool(self.get_smtp_config()['username']),
            'debug_mode': self.debug,
            'environment': self.environment
        }
    
    def print_status_summary(self):
        """설정 상태 요약 출력"""
        print("🔧 시스템 설정 상태")
        print("=" * 50)
        
        status = self.get_feature_status()
        
        for feature, available in status.items():
            icon = "✅" if available else "❌"
            print(f"{icon} {feature}: {'사용 가능' if available else '사용 불가'}")
        
        print("=" * 50)
        
        # 권장사항
        if not status['ai_content_generation']:
            print("💡 OpenAI API 키를 설정하면 AI 콘텐츠 생성을 사용할 수 있습니다.")
        
        if not status['instagram_posting']:
            print("💡 Instagram API를 설정하면 실제 포스팅이 가능합니다.")
        
        if status['debug_mode'] and self.environment == 'production':
            print("⚠️ 프로덕션 환경에서 DEBUG 모드가 활성화되어 있습니다!")

# 전역 설정 인스턴스
config = SecurityConfig()

def get_config() -> SecurityConfig:
    """설정 인스턴스 반환"""
    return config

def validate_environment():
    """환경 설정 검증"""
    try:
        config.validate_critical_settings()
        return True
    except ValueError as e:
        logger.error(f"환경 설정 오류: {e}")
        return False