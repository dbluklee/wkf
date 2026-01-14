#!/usr/bin/env python3
"""
네이버 금융 뉴스 스크래퍼 메인 애플리케이션

애플리케이션 진입점
"""

import sys
import signal
from pathlib import Path

from config.settings import Settings
from scheduler.news_scheduler import NewsScraperScheduler
from database.connection import DatabaseManager
from utils.logger import setup_logger, get_logger

# 전역 스케줄러 참조 (signal handler용)
scheduler = None


def signal_handler(sig, frame):
    """
    종료 시그널 핸들러 (Ctrl+C)

    Args:
        sig: 시그널 번호
        frame: 프레임 객체
    """
    logger = get_logger(__name__)
    logger.info("\nReceived interrupt signal. Shutting down gracefully...")

    if scheduler:
        scheduler.stop()

    sys.exit(0)


def initialize_database(settings: Settings):
    """
    데이터베이스 초기화 및 마이그레이션 실행

    Args:
        settings: 설정 객체
    """
    logger = get_logger(__name__)

    try:
        logger.info("Initializing database...")

        db_manager = DatabaseManager(settings)

        # 데이터베이스 준비 대기
        logger.info("Waiting for database to be ready...")
        db_manager.wait_for_db(max_retries=30, retry_interval=2)

        # 마이그레이션 실행
        migration_file = Path(__file__).parent / "database" / "migrations" / "001_create_news_table.sql"

        if migration_file.exists():
            logger.info(f"Running migration: {migration_file.name}")
            db_manager.execute_migration(str(migration_file))
            logger.info("Database migration completed successfully")
        else:
            logger.warning(f"Migration file not found: {migration_file}")

        db_manager.close()

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)


def main():
    """메인 함수"""
    global scheduler

    # 설정 로드
    settings = Settings.from_env()

    # 로거 설정
    setup_logger(
        log_level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
        name=None  # root logger
    )

    logger = get_logger(__name__)

    # 시작 메시지
    logger.info("=" * 70)
    logger.info("  Naver Finance News Scraper  ".center(70))
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Configuration:")
    logger.info(f"  Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    logger.info(f"  Target URL: {settings.TARGET_URL}")
    logger.info(f"  Scraping interval: {settings.SCRAPING_INTERVAL_SECONDS}s")
    logger.info(f"  Delay range: {settings.MIN_DELAY_SECONDS}s - {settings.MAX_DELAY_SECONDS}s")
    logger.info(f"  Proxy enabled: {settings.PROXY_ENABLED}")
    logger.info(f"  Log level: {settings.LOG_LEVEL}")
    logger.info("")

    # 시그널 핸들러 등록 (Ctrl+C 처리)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 데이터베이스 초기화
    initialize_database(settings)

    # 스케줄러 시작
    try:
        scheduler = NewsScraperScheduler(settings)
        scheduler.start()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
