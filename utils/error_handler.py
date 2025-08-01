# utils/error_handler.py - 통합 에러 처리 시스템
import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum
from pathlib import Path
import json

# 로그 설정
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ErrorType(Enum):
    """에러 타입 분류"""
    VALIDATION_ERROR = "validation_error"
    DATABASE_ERROR = "database_error"
    API_ERROR = "api_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    SYSTEM_ERROR = "system_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    CONFIGURATION_ERROR = "configuration_error"

class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"           # 로그만 기록
    MEDIUM = "medium"     # 알림 필요
    HIGH = "high"         # 즉시 대응 필요
    CRITICAL = "critical" # 시스템 중단 위험

class InstagramMarketingError(Exception):
    """🚨 커스텀 베이스 예외 클래스"""
    
    def __init__(
        self, 
        message: str,
        error_type: ErrorType = ErrorType.SYSTEM_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.details = details or {}
        self.user_message = user_message or "시스템 오류가 발생했습니다."
        self.timestamp = datetime.now().isoformat()
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """에러 정보를 딕셔너리로 변환"""
        return {
            'message': self.message,
            'error_type': self.error_type.value,
            'severity': self.severity.value,
            'details': self.details,
            'user_message': self.user_message,
            'timestamp': self.timestamp
        }

# 구체적인 예외 클래스들
class ValidationError(InstagramMarketingError):
    """입력 검증 오류"""
    def __init__(self, message: str, field: str = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        
        super().__init__(
            message=message,
            error_type=ErrorType.VALIDATION_ERROR,
            severity=ErrorSeverity.LOW,
            details=details,
            user_message="입력 정보를 확인해주세요.",
            **kwargs
        )

class DatabaseError(InstagramMarketingError):
    """데이터베이스 오류"""
    def __init__(self, message: str, query: str = None, **kwargs):
        details = kwargs.get('details', {})
        if query:
            details['query'] = query
        
        super().__init__(
            message=message,
            error_type=ErrorType.DATABASE_ERROR,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message="데이터 처리 중 오류가 발생했습니다.",
            **kwargs
        )

class APIError(InstagramMarketingError):
    """API 관련 오류"""
    def __init__(self, message: str, status_code: int = None, service: str = None, **kwargs):
        details = kwargs.get('details', {})
        if status_code:
            details['status_code'] = status_code
        if service:
            details['service'] = service
        
        super().__init__(
            message=message,
            error_type=ErrorType.API_ERROR,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            user_message="외부 서비스 연결에 문제가 있습니다.",
            **kwargs
        )

class AuthenticationError(InstagramMarketingError):
    """인증 오류"""
    def __init__(self, message: str = "인증에 실패했습니다.", **kwargs):
        super().__init__(
            message=message,
            error_type=ErrorType.AUTHENTICATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            user_message="로그인이 필요합니다.",
            **kwargs
        )

class AuthorizationError(InstagramMarketingError):
    """권한 오류"""
    def __init__(self, message: str = "권한이 부족합니다.", **kwargs):
        super().__init__(
            message=message,
            error_type=ErrorType.AUTHORIZATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            user_message="접근 권한이 없습니다.",
            **kwargs
        )

class ExternalServiceError(InstagramMarketingError):
    """외부 서비스 오류"""
    def __init__(self, message: str, service_name: str, **kwargs):
        details = kwargs.get('details', {})
        details['service_name'] = service_name
        
        super().__init__(
            message=message,
            error_type=ErrorType.EXTERNAL_SERVICE_ERROR,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message=f"{service_name} 서비스에 일시적인 문제가 있습니다.",
            **kwargs
        )

class RateLimitError(InstagramMarketingError):
    """레이트 리미트 오류"""
    def __init__(self, message: str = "요청 한도를 초과했습니다.", **kwargs):
        super().__init__(
            message=message,
            error_type=ErrorType.RATE_LIMIT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            user_message="잠시 후 다시 시도해주세요.",
            **kwargs
        )

class ErrorHandler:
    """🛡️ 통합 에러 처리기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_log_file = log_dir / 'errors.log'
        
        # 에러별 로거 설정
        self.error_logger = logging.getLogger('errors')
        error_handler = logging.FileHandler(self.error_log_file, encoding='utf-8')
        error_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.error_logger.addHandler(error_handler)
        self.error_logger.setLevel(logging.ERROR)
    
    def handle_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        🚨 에러 처리 메인 함수
        
        Args:
            error: 발생한 예외
            context: 에러 발생 컨텍스트 정보
            user_id: 에러 발생 사용자 ID
            
        Returns:
            처리된 에러 정보
        """
        context = context or {}
        
        # 커스텀 예외인지 확인
        if isinstance(error, InstagramMarketingError):
            error_info = self._handle_custom_error(error, context, user_id)
        else:
            error_info = self._handle_generic_error(error, context, user_id)
        
        # 로깅
        self._log_error(error_info)
        
        # 심각한 오류는 알림
        if error_info.get('severity') in [ErrorSeverity.HIGH.value, ErrorSeverity.CRITICAL.value]:
            self._send_alert(error_info)
        
        return error_info
    
    def _handle_custom_error(
        self, 
        error: InstagramMarketingError, 
        context: Dict[str, Any],
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """커스텀 예외 처리"""
        error_info = error.to_dict()
        error_info.update({
            'context': context,
            'user_id': user_id,
            'traceback': traceback.format_exc(),
            'handled_by': 'custom_handler'
        })
        
        return error_info
    
    def _handle_generic_error(
        self, 
        error: Exception, 
        context: Dict[str, Any],
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """일반 예외 처리"""
        # 에러 타입에 따라 분류
        error_type = self._classify_error(error)
        severity = self._determine_severity(error, error_type)
        
        error_info = {
            'message': str(error),
            'error_type': error_type.value,
            'severity': severity.value,
            'details': {
                'exception_type': type(error).__name__,
                'exception_module': getattr(error, '__module__', 'unknown')
            },
            'user_message': self._get_user_friendly_message(error_type),
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'user_id': user_id,
            'traceback': traceback.format_exc(),
            'handled_by': 'generic_handler'
        }
        
        return error_info
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """에러 타입 자동 분류"""
        error_type_name = type(error).__name__
        error_message = str(error).lower()
        
        # 데이터베이스 관련
        if 'sqlite' in error_type_name.lower() or 'database' in error_message:
            return ErrorType.DATABASE_ERROR
        
        # API 관련
        if any(keyword in error_message for keyword in ['api', 'request', 'response', 'http']):
            return ErrorType.API_ERROR
        
        # 검증 관련
        if any(keyword in error_message for keyword in ['validation', 'invalid', 'required']):
            return ErrorType.VALIDATION_ERROR
        
        # 권한 관련
        if any(keyword in error_message for keyword in ['permission', 'forbidden', 'unauthorized']):
            return ErrorType.AUTHORIZATION_ERROR
        
        # 설정 관련
        if any(keyword in error_message for keyword in ['config', 'environment', 'setting']):
            return ErrorType.CONFIGURATION_ERROR
        
        # 기본값
        return ErrorType.SYSTEM_ERROR
    
    def _determine_severity(self, error: Exception, error_type: ErrorType) -> ErrorSeverity:
        """에러 심각도 결정"""
        error_message = str(error).lower()
        
        # 시스템 중단 위험
        if any(keyword in error_message for keyword in ['critical', 'fatal', 'crash']):
            return ErrorSeverity.CRITICAL
        
        # 데이터베이스 오류는 높은 심각도
        if error_type == ErrorType.DATABASE_ERROR:
            return ErrorSeverity.HIGH
        
        # API 오류는 중간 심각도
        if error_type in [ErrorType.API_ERROR, ErrorType.EXTERNAL_SERVICE_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # 검증 오류는 낮은 심각도
        if error_type == ErrorType.VALIDATION_ERROR:
            return ErrorSeverity.LOW
        
        # 기본값
        return ErrorSeverity.MEDIUM
    
    def _get_user_friendly_message(self, error_type: ErrorType) -> str:
        """사용자 친화적 메시지 반환"""
        messages = {
            ErrorType.VALIDATION_ERROR: "입력 정보를 확인해주세요.",
            ErrorType.DATABASE_ERROR: "데이터 처리 중 오류가 발생했습니다.",
            ErrorType.API_ERROR: "외부 서비스 연결에 문제가 있습니다.",
            ErrorType.AUTHENTICATION_ERROR: "로그인이 필요합니다.",
            ErrorType.AUTHORIZATION_ERROR: "접근 권한이 없습니다.",
            ErrorType.EXTERNAL_SERVICE_ERROR: "외부 서비스에 일시적인 문제가 있습니다.",
            ErrorType.RATE_LIMIT_ERROR: "잠시 후 다시 시도해주세요.",
            ErrorType.CONFIGURATION_ERROR: "시스템 설정에 문제가 있습니다.",
            ErrorType.BUSINESS_LOGIC_ERROR: "요청을 처리할 수 없습니다.",
            ErrorType.SYSTEM_ERROR: "시스템 오류가 발생했습니다."
        }
        
        return messages.get(error_type, "알 수 없는 오류가 발생했습니다.")
    
    def _log_error(self, error_info: Dict[str, Any]):
        """에러 로깅"""
        severity = error_info.get('severity', 'medium')
        error_type = error_info.get('error_type', 'unknown')
        message = error_info.get('message', 'Unknown error')
        
        log_message = f"[{error_type.upper()}] {message}"
        
        # 심각도에 따른 로그 레벨 결정
        if severity == ErrorSeverity.CRITICAL.value:
            self.logger.critical(log_message)
            self.error_logger.critical(json.dumps(error_info, ensure_ascii=False, indent=2))
        elif severity == ErrorSeverity.HIGH.value:
            self.logger.error(log_message)
            self.error_logger.error(json.dumps(error_info, ensure_ascii=False, indent=2))
        elif severity == ErrorSeverity.MEDIUM.value:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _send_alert(self, error_info: Dict[str, Any]):
        """심각한 오류 알림 (이메일, 슬랙 등)"""
        try:
            # 여기에 실제 알림 로직 구현
            # 예: 이메일, 슬랙, 디스코드 등
            
            alert_message = f"""
🚨 심각한 오류 발생!

타입: {error_info.get('error_type', 'unknown')}
심각도: {error_info.get('severity', 'unknown')}
메시지: {error_info.get('message', 'Unknown')}
시간: {error_info.get('timestamp', 'Unknown')}
사용자: {error_info.get('user_id', 'Unknown')}

상세 정보는 로그 파일을 확인하세요.
            """
            
            # 현재는 로그로만 기록
            self.logger.critical(f"ALERT SENT: {alert_message}")
            
        except Exception as e:
            self.logger.error(f"알림 전송 실패: {e}")
    
    def create_error_response(
        self, 
        error: Exception, 
        status_code: int = 500,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """API 응답용 에러 생성"""
        error_info = self.handle_error(error, context)
        
        return {
            'success': False,
            'error': {
                'message': error_info.get('user_message', '오류가 발생했습니다.'),
                'type': error_info.get('error_type', 'system_error'),
                'timestamp': error_info.get('timestamp'),
                'request_id': context.get('request_id') if context else None
            },
            'status_code': status_code
        }
    
    def get_error_stats(self, days: int = 7) -> Dict[str, Any]:
        """에러 통계 조회"""
        try:
            # 로그 파일에서 에러 통계 추출
            if not self.error_log_file.exists():
                return {'message': '에러 로그 파일이 없습니다.'}
            
            error_counts = {}
            severity_counts = {}
            recent_errors = []
            
            with open(self.error_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        if line.strip().startswith('{'):
                            error_data = json.loads(line.strip())
                            
                            # 최근 N일 필터링
                            error_time = datetime.fromisoformat(error_data.get('timestamp', ''))
                            if (datetime.now() - error_time).days <= days:
                                error_type = error_data.get('error_type', 'unknown')
                                severity = error_data.get('severity', 'unknown')
                                
                                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                                
                                recent_errors.append({
                                    'timestamp': error_data.get('timestamp'),
                                    'type': error_type,
                                    'severity': severity,
                                    'message': error_data.get('message', '')[:100]
                                })
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            return {
                'period_days': days,
                'total_errors': sum(error_counts.values()),
                'error_types': error_counts,
                'severity_distribution': severity_counts,
                'recent_errors': recent_errors[-10:],  # 최근 10개
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"에러 통계 조회 실패: {e}")
            return {'error': '통계 조회에 실패했습니다.'}

# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler()

def handle_error(error: Exception, context: Dict[str, Any] = None, user_id: int = None) -> Dict[str, Any]:
    """에러 처리 함수"""
    return error_handler.handle_error(error, context, user_id)

def create_error_response(error: Exception, status_code: int = 500, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """API 에러 응답 생성"""
    return error_handler.create_error_response(error, status_code, context)

# 데코레이터
def error_handler_decorator(func):
    """에러 처리 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                'function': func.__name__,
                'args': str(args)[:200],  # 너무 길면 자르기
                'kwargs': str(kwargs)[:200]
            }
            error_info = handle_error(e, context)
            
            # 에러 재발생 (상위에서 처리하도록)
            raise e
    
    return wrapper

# 비동기 데코레이터
def async_error_handler_decorator(func):
    """비동기 에러 처리 데코레이터"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            context = {
                'function': func.__name__,
                'args': str(args)[:200],
                'kwargs': str(kwargs)[:200]
            }
            error_info = handle_error(e, context)
            
            # 에러 재발생
            raise e
    
    return wrapper