"""
데이터베이스 연결 관리
"""
import time
import psycopg2
from psycopg2.extensions import connection
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class DisclosureDatabaseManager:
    """공시 데이터베이스 연결 관리자"""

    def __init__(self, settings):
        """
        Args:
            settings: DisclosureScraperSettings 인스턴스
        """
        self.settings = settings
        self._connection: Optional[connection] = None

    def get_connection(self) -> connection:
        """
        데이터베이스 연결 반환 (필요 시 재연결)

        Returns:
            psycopg2 connection 객체
        """
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.settings.DB_HOST,
                port=self.settings.DB_PORT,
                dbname=self.settings.DB_NAME,
                user=self.settings.DB_USER,
                password=self.settings.DB_PASSWORD
            )
            logger.info("Database connection established")

        return self._connection

    def wait_for_db(self, max_retries: int = 30, retry_interval: int = 2):
        """
        데이터베이스 연결 대기

        Args:
            max_retries: 최대 재시도 횟수
            retry_interval: 재시도 간격 (초)
        """
        for attempt in range(1, max_retries + 1):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                logger.info("Database is ready")
                return
            except psycopg2.OperationalError as e:
                if attempt < max_retries:
                    logger.warning(f"Database not ready (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts")
                    raise

    def execute_migration(self, migration_file: str):
        """
        마이그레이션 파일 실행

        Args:
            migration_file: 마이그레이션 파일 경로
        """
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(sql)
            conn.commit()
            logger.info(f"Migration executed: {migration_file}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {migration_file} - {e}")
            raise
        finally:
            cursor.close()

    def close(self):
        """데이터베이스 연결 종료"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")
