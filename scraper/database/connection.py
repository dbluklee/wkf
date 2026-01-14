"""
데이터베이스 연결 및 Repository 관리
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Optional, Generator
import time

from config.settings import Settings
from models.news import NewsArticle
from utils.logger import get_logger
from utils.timezone_utils import get_kst_now, remove_timezone

logger = get_logger(__name__)


class DatabaseManager:
    """PostgreSQL 연결 풀 관리자"""

    def __init__(self, settings: Settings, min_conn: int = 1, max_conn: int = 10):
        """
        Args:
            settings: 설정 객체
            min_conn: 최소 연결 수
            max_conn: 최대 연결 수
        """
        self.settings = settings
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None

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
            logger.info(f"Database connection pool created: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
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


class NewsRepository:
    """뉴스 기사 데이터 저장소"""

    def __init__(self, db_manager: DatabaseManager):
        """
        Args:
            db_manager: DatabaseManager 인스턴스
        """
        self.db_manager = db_manager

    def article_exists(self, article_id: str) -> bool:
        """
        article_id로 중복 체크

        Args:
            article_id: 기사 ID

        Returns:
            존재 여부
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM news_articles WHERE article_id = %s LIMIT 1",
                        (article_id,)
                    )
                    return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check article existence: {e}")
            return False

    def content_hash_exists(self, content_hash: str) -> bool:
        """
        content_hash로 중복 체크

        Args:
            content_hash: 컨텐츠 해시

        Returns:
            존재 여부
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM news_articles WHERE content_hash = %s LIMIT 1",
                        (content_hash,)
                    )
                    return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check content hash: {e}")
            return False

    def insert_article(self, article: NewsArticle) -> bool:
        """
        새 뉴스 기사 저장 (한국 시간대 기준)

        Args:
            article: NewsArticle 객체

        Returns:
            성공 여부
        """
        try:
            # 현재 한국 시간 가져오기
            kst_now = get_kst_now()
            scraped_at_kst = remove_timezone(kst_now)

            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO news_articles
                        (article_id, title, content, url, content_hash,
                         published_at, scraped_at, section_id, section_id2)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (article_id) DO NOTHING
                        RETURNING id
                    """, (
                        article.article_id,
                        article.title,
                        article.content,
                        article.url,
                        article.content_hash,
                        article.published_at,
                        scraped_at_kst,
                        article.section_id,
                        article.section_id2
                    ))

                    result = cursor.fetchone()
                    if result:
                        logger.info(f"Inserted article: {article.article_id}")
                        return True
                    else:
                        logger.debug(f"Article already exists (skipped): {article.article_id}")
                        return False

        except Exception as e:
            logger.error(f"Failed to insert article: {e}")
            return False

    def bulk_insert_articles(self, articles: List[NewsArticle]) -> int:
        """
        여러 뉴스 기사 일괄 저장

        Args:
            articles: NewsArticle 객체 리스트

        Returns:
            성공적으로 저장된 기사 수
        """
        if not articles:
            return 0

        inserted_count = 0
        for article in articles:
            if self.insert_article(article):
                inserted_count += 1

        logger.info(f"Bulk insert completed: {inserted_count}/{len(articles)} articles")
        return inserted_count

    def log_scraping_run(
        self,
        status: str,
        articles_found: int,
        articles_new: int,
        execution_time: float,
        error_message: Optional[str] = None
    ):
        """
        스크래핑 실행 로그 저장 (한국 시간대 기준)

        Args:
            status: 실행 상태 (success, partial, failed)
            articles_found: 발견된 기사 수
            articles_new: 신규 저장된 기사 수
            execution_time: 실행 시간 (초)
            error_message: 에러 메시지 (선택사항)
        """
        try:
            articles_duplicate = articles_found - articles_new

            # 현재 한국 시간 가져오기
            kst_now = get_kst_now()
            created_at_kst = remove_timezone(kst_now)

            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO scraping_logs
                        (status, articles_found, articles_new,
                         articles_duplicate, error_message, execution_time, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        status,
                        articles_found,
                        articles_new,
                        articles_duplicate,
                        error_message,
                        execution_time,
                        created_at_kst
                    ))
                    logger.debug(f"Scraping run logged: {status}")

        except Exception as e:
            logger.error(f"Failed to log scraping run: {e}")

    def get_recent_articles(self, limit: int = 10) -> List[dict]:
        """
        최근 수집된 기사 조회

        Args:
            limit: 조회할 기사 수

        Returns:
            기사 딕셔너리 리스트
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT article_id, title, url, published_at, scraped_at
                        FROM news_articles
                        ORDER BY scraped_at DESC
                        LIMIT %s
                    """, (limit,))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch recent articles: {e}")
            return []
