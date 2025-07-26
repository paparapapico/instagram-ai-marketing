from datetime import datetime
import hashlib
import random
import string

def generate_random_string(length=10):
    """랜덤 문자열 생성"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def hash_string(text):
    """문자열 해싱"""
    return hashlib.sha256(text.encode()).hexdigest()

def format_datetime(dt):
    """날짜 시간 포맷팅"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def validate_email(email):
    """이메일 형식 검증"""
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def get_industry_colors(industry):
    """업종별 색상 반환"""
    colors = {
        "restaurant": "#ff6b6b",
        "fashion": "#4ecdc4", 
        "beauty": "#45b7d1",
        "software": "#96ceb4",
        "default": "#6366f1"
    }
    return colors.get(industry, colors["default"])