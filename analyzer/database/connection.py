"""
데이터베이스 연결 관리
"""

import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from typing import Generator
import time

from config.settings import AnalyzerSettings
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalyzerDatabaseManager:
    """PostgreSQL 연결 풀 관리자"""

    def __init__(self, settings: AnalyzerSettings, min_conn: int = 1, max_conn: int = 10):
        """
        Args:
            settings: 설정 객체
            min_conn: 최소 연결 수
            max_conn: 최대 연결 수
        """
        self.settings = settings
        self.connection_pool = None

        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_conn,
                max_conn,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD
            )
            logger.info(f"Analyzer database connection pool created: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise

    def _ensure_pool(self):
        """연결 풀이 닫혔으면 재생성"""
        if self.connection_pool is None or self.connection_pool.closed:
            logger.warning("Connection pool is closed, recreating...")
            try:
                self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1,
                    10,
                    host=self.settings.DB_HOST,
                    port=self.settings.DB_PORT,
                    database=self.settings.DB_NAME,
                    user=self.settings.DB_USER,
                    password=self.settings.DB_PASSWORD
                )
                logger.info("Connection pool recreated successfully")
            except Exception as e:
                logger.error(f"Failed to recreate connection pool: {e}")
                raise

    @contextmanager
    def get_connection(self) -> Generator:
        """
        연결 풀에서 연결을 가져오는 컨텍스트 매니저

        Yields:
            psycopg2 connection 객체
        """
        connection = None
        try:
            self._ensure_pool()
            connection = self.connection_pool.getconn()
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if connection and self.connection_pool and not self.connection_pool.closed:
                self.connection_pool.putconn(connection)

    def execute_migration(self, sql_file_path: str):
        """
        SQL 마이그레이션 파일 실행

        Args:
            sql_file_path: SQL 파일 경로
        """
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql_script)
                    logger.info(f"Migration executed successfully: {sql_file_path}")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    def wait_for_db(self, max_retries: int = 30, retry_interval: int = 2):
        """
        데이터베이스가 준비될 때까지 대기

        Args:
            max_retries: 최대 재시도 횟수
            retry_interval: 재시도 간격 (초)
        """
        for i in range(max_retries):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        logger.info("Database is ready")
                        return
            except Exception as e:
                logger.warning(f"Waiting for database... ({i+1}/{max_retries}): {e}")
                time.sleep(retry_interval)

        raise Exception("Database is not available after max retries")

    def close(self):
        """연결 풀 종료"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")
