"""
Analyzer 서비스 메인 애플리케이션
"""

import sys
import threading
from config.settings import AnalyzerSettings
from database.connection import AnalyzerDatabaseManager
from database.repositories import Repositories
from services.openai_service import OpenAIService
from services.kis_service import KISService
from services.trade_executor import TradeExecutor
from services.analyzer_orchestrator import AnalyzerOrchestrator
from wkf_analyzer.services.telegram_service import TelegramService
from listeners.disclosure_listener import DisclosureListener
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """메인 함수"""
    telegram_service = None

    try:
        logger.info("=" * 60)
        logger.info("Starting WKF Analyzer Service")
        logger.info("=" * 60)

        # 1. 설정 로드 및 검증
        logger.info("Loading configuration...")
        settings = AnalyzerSettings.from_env()
        settings.validate()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"- Analysis threshold: {settings.ANALYSIS_THRESHOLD_PERCENT}%")
        logger.info(f"- Max recommendations: {settings.MAX_RECOMMENDATIONS_PER_ARTICLE}")
        logger.info(f"- Stock history days: {settings.STOCK_HISTORY_DAYS}")

        # 2. 텔레그램 서비스 초기화
        logger.info("- Telegram notification service")
        telegram_service = TelegramService(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
            llm_name="openai"
        )

        # 3. 데이터베이스 연결
        logger.info("Connecting to database...")
        db_manager = AnalyzerDatabaseManager(settings)
        db_manager.wait_for_db()
        logger.info("Database connection established")

        # 4. 마이그레이션 실행
        logger.info("Running database migrations...")
        try:
            db_manager.execute_migration('database/migrations/002_create_analyzer_tables.sql')
            db_manager.execute_migration('database/migrations/003_create_notify_trigger.sql')
            logger.info("Migrations completed successfully")
        except Exception as e:
            logger.warning(f"Migration warning (may already exist): {e}")

        # 5. Repository 초기화
        logger.info("Initializing repositories...")
        repos = Repositories(db_manager)

        # 6. 서비스 초기화
        logger.info("Initializing services...")
        logger.info("- OpenAI API service")
        openai_service = OpenAIService(settings)

        logger.info("- KIS API service (Korea Investment & Securities)")
        kis_service = KISService(settings)

        logger.info("- Analyzer orchestrator")
        orchestrator = AnalyzerOrchestrator(
            settings,
            openai_service,
            kis_service,
            repos,
            telegram_service
        )

        logger.info("- Trade Executor (Auto Trading)")
        trade_executor = TradeExecutor(settings, kis_service, repos, telegram_service)
        trade_executor.start_monitoring()

        # 7. 서비스 시작 알림
        telegram_service.notify_service_start()

        # 8. 소스 타입에 따라 리스너 시작
        logger.info("=" * 60)
        logger.info("Starting PostgreSQL LISTEN...")
        logger.info(f"- Source type: {settings.SOURCE_TYPE}")

        if settings.SOURCE_TYPE == 'news':
            from listeners.article_listener import ArticleListener
            logger.info("- Channel 'new_article': News articles")
            logger.info("=" * 60)
            article_listener = ArticleListener(db_manager, orchestrator.analyze_article)
            article_listener.start_listening()
        elif settings.SOURCE_TYPE == 'disclosure':
            logger.info("- Channel 'new_disclosure': Disclosures")
            logger.info("=" * 60)
            disclosure_listener = DisclosureListener(db_manager, orchestrator.analyze_disclosure)
            disclosure_listener.start_listening()
        else:
            raise ValueError(f"Invalid SOURCE_TYPE: {settings.SOURCE_TYPE}")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Shutting down gracefully (Ctrl+C received)...")
        logger.info("=" * 60)
        if telegram_service:
            telegram_service.notify_service_stop()
        sys.exit(0)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"Fatal error: {e}")
        logger.error("=" * 60)
        if telegram_service:
            telegram_service.notify_error("Fatal Error", str(e))
            telegram_service.notify_service_stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
