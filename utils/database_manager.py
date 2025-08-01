# utils/database_manager.py - 통합 데이터베이스 관리자
import sqlite3
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Dict, List, Any
from datetime import datetime
import json
import os
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """🗄️ 통합 데이터베이스 관리 클래스"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "instagram_marketing.db"):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "instagram_marketing.db"):
        """데이터베이스 관리자 초기화"""
        if self._initialized:
            return
            
        self.db_path = db_path
        self.connection_pool = {}
        self._local = threading.local()
        self._ensure_database_directory()
        self._initialized = True
        
        # 데이터베이스 초기화
        self.initialize_database()
        logger.info(f"✅ DatabaseManager 초기화 완료: {db_path}")
    
    def _ensure_database_directory(self):
        """데이터베이스 디렉토리 확인/생성"""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 데이터베이스 디렉토리 생성: {db_dir}")
    
    @contextmanager
    def get_connection(self, timeout: int = 30):
        """
        🔗 안전한 데이터베이스 연결 컨텍스트 매니저
        
        Usage:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path, 
                timeout=timeout,
                check_same_thread=False
            )
            # Row factory 설정으로 딕셔너리 형태 결과 반환
            conn.row_factory = sqlite3.Row
            
            # 외래 키 제약조건 활성화
            conn.execute("PRAGMA foreign_keys = ON")
            
            # WAL 모드 설정 (동시성 향상)
            conn.execute("PRAGMA journal_mode = WAL")
            
            yield conn
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 데이터베이스 오류: {e}")
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ 예상치 못한 오류: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_transaction(self):
        """
        🔄 트랜잭션 컨텍스트 매니저
        
        Usage:
            with db_manager.get_transaction() as cursor:
                cursor.execute("INSERT INTO users ...")
                cursor.execute("INSERT INTO businesses ...")
                # 자동으로 commit 또는 rollback
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
                logger.debug("✅ 트랜잭션 커밋 완료")
            except Exception as e:
                conn.rollback()
                logger.error(f"🔄 트랜잭션 롤백: {e}")
                raise
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Optional[Any]:
        """
        📝 쿼리 실행 (SELECT용)
        
        Args:
            query: SQL 쿼리
            params: 파라미터 튜플
            fetch_one: 단일 결과 반환
            fetch_all: 모든 결과 반환
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch_one:
                    result = cursor.fetchone()
                    return dict(result) if result else None
                elif fetch_all:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                else:
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"❌ 쿼리 실행 오류: {e}")
            logger.error(f"   쿼리: {query}")
            logger.error(f"   파라미터: {params}")
            raise
    
    def execute_command(self, query: str, params: tuple = ()) -> int:
        """
        ⚡ 명령 실행 (INSERT, UPDATE, DELETE용)
        
        Returns:
            영향받은 행 수 또는 마지막 삽입 ID
        """
        try:
            with self.get_transaction() as cursor:
                cursor.execute(query, params)
                
                if query.strip().upper().startswith('INSERT'):
                    return cursor.lastrowid
                else:
                    return cursor.rowcount
                    
        except sqlite3.Error as e:
            logger.error(f"❌ 명령 실행 오류: {e}")
            logger.error(f"   쿼리: {query}")
            logger.error(f"   파라미터: {params}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        📦 배치 실행 (여러 행 처리)
        
        Returns:
            처리된 행 수
        """
        try:
            with self.get_transaction() as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount
                
        except sqlite3.Error as e:
            logger.error(f"❌ 배치 실행 오류: {e}")
            logger.error(f"   쿼리: {query}")
            logger.error(f"   배치 크기: {len(params_list)}")
            raise
    
    def initialize_database(self):
        """🏗️ 데이터베이스 테이블 초기화"""
        try:
            with self.get_transaction() as cursor:
                # 사용자 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_login TEXT,
                        CONSTRAINT email_format CHECK (email LIKE '%@%')
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
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """)
                
                # 콘텐츠 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS content (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        business_id INTEGER NOT NULL,
                        title TEXT,
                        caption TEXT NOT NULL,
                        hashtags TEXT, -- JSON 형태로 저장
                        image_url TEXT,
                        content_type TEXT DEFAULT 'post',
                        platform TEXT DEFAULT 'instagram',
                        status TEXT DEFAULT 'draft',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT,
                        published_at TEXT,
                        likes_count INTEGER DEFAULT 0,
                        comments_count INTEGER DEFAULT 0,
                        shares_count INTEGER DEFAULT 0,
                        engagement_rate REAL DEFAULT 0.0,
                        FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE,
                        CONSTRAINT status_check CHECK (status IN ('draft', 'scheduled', 'published', 'failed'))
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
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        completed_at TEXT,
                        FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE,
                        FOREIGN KEY (content_id) REFERENCES content (id) ON DELETE CASCADE,
                        CONSTRAINT schedule_status_check CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'))
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
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE,
                        UNIQUE(business_id, date)
                    )
                """)
                
                # 비즈니스 설정 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS business_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        business_id INTEGER NOT NULL,
                        auto_post_enabled BOOLEAN DEFAULT TRUE,
                        post_frequency INTEGER DEFAULT 1,
                        preferred_times TEXT DEFAULT '["09:00", "12:00", "18:00"]', -- JSON
                        content_themes TEXT DEFAULT '["product", "lifestyle", "behind_scenes"]', -- JSON
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT,
                        FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE,
                        UNIQUE(business_id)
                    )
                """)
                
                # 성과 추적 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        business_id INTEGER NOT NULL,
                        post_id TEXT,
                        content_type TEXT,
                        posted_at TEXT,
                        likes_count INTEGER DEFAULT 0,
                        comments_count INTEGER DEFAULT 0,
                        engagement_rate REAL DEFAULT 0.0,
                        reach INTEGER DEFAULT 0,
                        impressions INTEGER DEFAULT 0,
                        last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE CASCADE
                    )
                """)
                
                # 인덱스 생성
                self._create_indexes(cursor)
                
                logger.info("✅ 데이터베이스 테이블 초기화 완료")
                
        except sqlite3.Error as e:
            logger.error(f"❌ 데이터베이스 초기화 오류: {e}")
            raise
    
    def _create_indexes(self, cursor):
        """📊 인덱스 생성으로 성능 최적화"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_content_business_id ON content(business_id)",
            "CREATE INDEX IF NOT EXISTS idx_content_status ON content(status)",
            "CREATE INDEX IF NOT EXISTS idx_content_created_at ON content(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_schedule_datetime ON content_schedule(scheduled_datetime)",
            "CREATE INDEX IF NOT EXISTS idx_schedule_status ON content_schedule(status)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_business_date ON analytics(business_id, date)",
            "CREATE INDEX IF NOT EXISTS idx_performance_business ON performance_tracking(business_id)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.Error as e:
                logger.warning(f"⚠️ 인덱스 생성 실패: {e}")
    
    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """💾 데이터베이스 백업"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"
        
        try:
            with self.get_connection() as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            logger.info(f"✅ 데이터베이스 백업 완료: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 백업 실패: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """📊 데이터베이스 통계 정보"""
        stats = {}
        
        try:
            tables = [
                'users', 'businesses', 'content', 'content_schedule',
                'analytics', 'business_settings', 'performance_tracking'
            ]
            
            for table in tables:
                count = self.execute_query(
                    f"SELECT COUNT(*) as count FROM {table}",
                    fetch_one=True
                )
                stats[f"{table}_count"] = count['count'] if count else 0
            
            # 데이터베이스 크기
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
            
            # 최근 활동
            recent_content = self.execute_query(
                "SELECT created_at FROM content ORDER BY created_at DESC LIMIT 1",
                fetch_one=True
            )
            stats['last_content_created'] = recent_content['created_at'] if recent_content else None
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 통계 조회 오류: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30):
        """🧹 오래된 데이터 정리"""
        try:
            cutoff_date = datetime.now().strftime("%Y-%m-%d")
            
            with self.get_transaction() as cursor:
                # 완료된 스케줄 데이터 정리
                cursor.execute("""
                    DELETE FROM content_schedule 
                    WHERE status = 'completed' 
                    AND date(completed_at) < date('now', '-{} days')
                """.format(days))
                
                deleted_schedules = cursor.rowcount
                
                # 실패한 스케줄 데이터 정리 (재시도 횟수 많은 것)
                cursor.execute("""
                    DELETE FROM content_schedule 
                    WHERE status = 'failed' 
                    AND retry_count > 3
                    AND date(created_at) < date('now', '-7 days')
                """)
                
                deleted_failed = cursor.rowcount
                
                logger.info(f"🧹 데이터 정리 완료: 스케줄 {deleted_schedules}개, 실패 {deleted_failed}개 삭제")
                
        except Exception as e:
            logger.error(f"❌ 데이터 정리 오류: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """🏥 데이터베이스 상태 확인"""
        try:
            start_time = datetime.now()
            
            # 연결 테스트
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                'status': 'healthy',
                'response_time_seconds': response_time,
                'database_path': self.db_path,
                'connection_test': 'passed',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database_path': self.db_path,
                'connection_test': 'failed',
                'timestamp': datetime.now().isoformat()
            }

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """데이터베이스 매니저 인스턴스 반환"""
    return db_manager