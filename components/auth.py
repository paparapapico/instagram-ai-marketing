from fastapi import HTTPException
import jwt
from datetime import datetime, timedelta

class AuthComponent:
    """인증 관련 컴포넌트"""
    
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def create_token(self, user_data):
        """JWT 토큰 생성"""
        payload = {
            **user_data,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token):
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")