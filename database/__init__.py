# database/init_db.py - 데이터베이스 초기화
import sqlite3
import os
from datetime import datetime

def init_database(db_path="instagram_marketing.db"):
    """데이터베이스 테이블 생성"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 사용자 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                last_login TEXT
            )
        """)
        
        # 비즈니스 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                business_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                target_audience TEXT,
                brand_voice TEXT,
                phone TEXT,
                website TEXT,
                instagram_username TEXT,
                instagram_access_token TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 콘텐츠 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                title TEXT,
                caption TEXT NOT NULL,
                hashtags TEXT,
                image_url TEXT,
                content_type TEXT DEFAULT 'post',
                platform TEXT DEFAULT 'instagram',
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                published_at TEXT,
                likes_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                shares_count INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                FOREIGN KEY (business_id) REFERENCES businesses (id)
            )
        """)
        
        # 콘텐츠 스케줄 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                content_id INTEGER NOT NULL,
                scheduled_datetime TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                post_id TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (business_id) REFERENCES businesses (id),
                FOREIGN KEY (content_id) REFERENCES content (id)
            )
        """)
        
        # 분석 데이터 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                followers_count INTEGER DEFAULT 0,
                following_count INTEGER DEFAULT 0,
                posts_count INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                reach INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (business_id) REFERENCES businesses (id)
            )
        """)
        
        # 사용자 세션 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # 설정 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (business_id) REFERENCES businesses (id),
                UNIQUE(business_id, setting_key)
            )
        """)
        
        # 인덱스 생성
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_business_id ON content(business_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_schedule_datetime ON content_schedule(scheduled_datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_business_date ON analytics(business_id, date)")
        
        conn.commit()
        print("✅ 데이터베이스 테이블이 성공적으로 생성되었습니다.")
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 오류: {e}")
        conn.rollback()
    finally:
        conn.close()

def seed_sample_data(db_path="instagram_marketing.db"):
    """샘플 데이터 생성"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 샘플 사용자 확인
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            print("샘플 데이터가 이미 존재합니다.")
            return
        
        # 샘플 사용자 생성
        import bcrypt
        password_hash = bcrypt.hashpw("demo123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, created_at, is_active)
            VALUES (?, ?, ?, ?)
        """, ("demo@example.com", password_hash, datetime.now().isoformat(), True))
        
        user_id = cursor.lastrowid
        
        # 샘플 비즈니스 생성
        cursor.execute("""
            INSERT INTO businesses (
                user_id, business_name, industry, target_audience,
                brand_voice, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id, "데모 카페", "restaurant", "20-30대 직장인",
            "친근하고 따뜻한", datetime.now().isoformat()
        ))
        
        business_id = cursor.lastrowid
        
        # 샘플 콘텐츠 생성
        sample_contents = [
            ("오늘의 특별 메뉴", "신선한 재료로 만든 오늘의 특별 메뉴를 소개합니다! #카페 #맛집 #특별메뉴"),
            ("새로운 디저트", "달콤한 새 디저트가 출시되었어요 🍰 #디저트 #카페 #신메뉴"),
            ("편안한 분위기", "편안한 분위기에서 즐기는 커피 한 잔 ☕ #카페 #분위기 #휴식")
        ]
        
        for title, caption in sample_contents:
            cursor.execute("""
                INSERT INTO content (
                    business_id, title, caption, content_type,
                    platform, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                business_id, title, caption, "post",
                "instagram", "draft", datetime.now().isoformat()
            ))
        
        conn.commit()
        print("✅ 샘플 데이터가 생성되었습니다.")
        print("   데모 계정: demo@example.com / demo123")
        
    except Exception as e:
        print(f"❌ 샘플 데이터 생성 오류: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
    seed_sample_data()