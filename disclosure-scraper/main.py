"""
공시 스크래퍼 메인 애플리케이션
"""
import sys
from config.settings import DisclosureScraperSettings
from database.connection import DisclosureDatabaseManager
from database.repositories import DisclosureRepository, ScrapingLogRepository
from services.opendart_service import OpenDartService
from scrapers.opendart_scraper import OpenDartScraper
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """메인 함수"""
    try:
        logger.info("=" * 60)
        logger.info("Starting WKF Disclosure Scraper Service")
        logger.info("=" * 60)

        # 1. 설정 로드 및 검증
        logger.info("Loading configuration...")
        settings = DisclosureScraperSettings.from_env()
        settings.validate()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"- OpenDART API Key: {'*' * 20}")
        logger.info(f"- Scraping interval: {settings.SCRAPING_INTERVAL_SECONDS}s")
        logger.info(f"- Corp class: {settings.CORP_CLS or 'All'}")
        logger.info(f"- Page count: {settings.PAGE_COUNT}")

        # 2. 데이터베이스 연결
        logger.info("Connecting to database...")
        db_manager = DisclosureDatabaseManager(settings)
        db_manager.wait_for_db()
        logger.info("Database connection established")

        # 3. 마이그레이션 실행
        logger.info("Running database migrations...")
        try:
            db_manager.execute_migration('database/migrations/001_create_disclosure_tables.sql')
            db_manager.execute_migration('database/migrations/002_create_disclosure_notify_trigger.sql')
            logger.info("Migrations completed successfully")
        except Exception as e:
            logger.warning(f"Migration warning (may already exist): {e}")

        # 4. Repository 초기화
        logger.info("Initializing repositories...")
        disclosure_repo = DisclosureRepository(db_manager)
        scraping_log_repo = ScrapingLogRepository(db_manager)

        # 5. 서비스 초기화
        logger.info("Initializing services...")
        opendart_service = OpenDartService(
            api_key=settings.OPENDART_API_KEY,
            base_url=settings.OPENDART_BASE_URL
        )

        # 6. 스크래퍼 초기화 및 실행
        logger.info("Initializing scraper...")
        scraper = OpenDartScraper(
            opendart_service,
            disclosure_repo,
            scraping_log_repo,
            settings
        )

        logger.info("=" * 60)
        logger.info("Starting continuous scraping...")
        logger.info("=" * 60)

        # 지속적인 스크래핑 시작
        scraper.run_continuous()

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Shutting down gracefully (Ctrl+C received)...")
        logger.info("=" * 60)
        sys.exit(0)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Fatal error: {e}")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
