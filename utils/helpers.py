# 헬퍼 함수들
import os
from datetime import datetime

def get_current_time():
    """현재 시간 반환"""
    return datetime.now()

def create_directory(path):
    """디렉토리 생성"""
    if not os.path.exists(path):
        os.makedirs(path)
        return True
    return False