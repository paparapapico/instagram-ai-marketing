import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_path="instagram_marketing.db"):
    """데이터베이스 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=None, db_path="instagram_marketing.db"):
    """쿼리 실행 유틸리티"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.fetchall()