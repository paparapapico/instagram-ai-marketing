# 데이터베이스 모델
from datetime import datetime

class User:
    def __init__(self, id, email, password, created_at=None):
        self.id = id
        self.email = email
        self.password = password
        self.created_at = created_at or datetime.now()

class Post:
    def __init__(self, id, user_id, content, image_url, scheduled_time, created_at=None):
        self.id = id
        self.user_id = user_id
        self.content = content
        self.image_url = image_url
        self.scheduled_time = scheduled_time
        self.created_at = created_at or datetime.now() 