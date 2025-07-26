# schemas.py
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    business_name: str
    email: str
    # ... 이하 생략

class UserLogin(BaseModel):
    email: str
    password: str
# ... 다른 Pydantic 모델들도 모두 여기에 정의