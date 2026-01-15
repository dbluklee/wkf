"""
Analyzer 서비스 메인 애플리케이션
"""

import sys
import threading
from config.settings import AnalyzerSettings
from database.connection import AnalyzerDatabaseManager
from database.repositories import Repositories
from services.claude_service import ClaudeService
from services.kis_service import KISService
from services.analyzer_orchestrator import AnalyzerOrchestrator
from listeners.disclosure_listener import DisclosureListener
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """메인 함수"""
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

        # 2. 데이터베이스 연결
        logger.info("Connecting to database...")
        db_manager = AnalyzerDatabaseManager(settings)
        db_manager.wait_for_db()
        logger.info("Database connection established")

        # 3. 마이그레이션 실행
        logger.info("Running database migrations...")
        try:
            db_manager.execute_migration('database/migrations/002_create_analyzer_tables.sql')
            db_manager.execute_migration('database/migrations/003_create_notify_trigger.sql')
            logger.info("Migrations completed successfully")
        except Exception as e:
            logger.warning(f"Migration warning (may already exist): {e}")

        # 4. Repository 초기화
        logger.info("Initializing repositories...")
        repos = Repositories(db_manager)

        # 5. 서비스 초기화
        logger.info("Initializing services...")
        logger.info("- Claude API service (Anthropic)")
        claude_service = ClaudeService(settings)

        logger.info("- KIS API service (Korea Investment & Securities)")
        kis_service = KISService(settings)

        logger.info("- Analyzer orchestrator")
        orchestrator = AnalyzerOrchestrator(
            settings,
            claude_service,
            kis_service,
            repos
        )

        # 6. 공시 리스너 시작
        logger.info("=" * 60)
        logger.info("Starting PostgreSQL LISTEN...")
        logger.info("- Channel 'new_disclosure': Disclosures only")
        logger.info("=" * 60)

        # 공시 리스너
        disclosure_listener = DisclosureListener(db_manager, orchestrator.analyze_disclosure)
        disclosure_listener.start_listening()

    except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Shutting down gracefully (Ctrl+C received)...")
            logger.info("=" * 60)
            sys.exit(0)

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
