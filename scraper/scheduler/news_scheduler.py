"""
뉴스 스크래퍼 스케줄러

1분 간격으로 스크래핑 작업을 실행합니다.
"""

import schedule
import time
from datetime import datetime

from scrapers.naver_finance_scraper import NaverFinanceScraper
from database.connection import DatabaseManager, NewsRepository
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsScraperScheduler:
    """뉴스 스크래퍼 스케줄러"""

    def __init__(self, settings: Settings):
        """
        Args:
            settings: 설정 객체
        """
        self.settings = settings
        self.scraper = NaverFinanceScraper(settings)
        self.db_manager = DatabaseManager(settings)
        self.repository = NewsRepository(self.db_manager)
        self.is_running = False

        logger.info("NewsScraperScheduler initialized")

    def scrape_and_save(self):
        """스크래핑 실행 및 DB 저장"""

        # 중복 실행 방지
        if self.is_running:
            logger.warning("Previous scraping job still running, skipping this run...")
            return

        self.is_running = True
        start_time = time.time()
        status = 'failed'
        articles_found = 0
        articles_new = 0
        error_message = None

        try:
            logger.info("=" * 60)
            logger.info(f"Starting scraping job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            # 뉴스 목록 및 상세 내용 스크래핑
            articles = self.scraper.scrape_with_content(max_articles=20)
            articles_found = len(articles)

            logger.info(f"Scraped {articles_found} articles total")

            # 새 뉴스만 필터링
            new_articles = []
            for article in articles:
                # article_id로 중복 체크
                if not self.repository.article_exists(article.article_id):
                    new_articles.append(article)
                else:
                    logger.debug(f"Article already exists (skipped): {article.article_id}")

            logger.info(f"Found {len(new_articles)} new articles (out of {articles_found})")

            # DB에 저장
            if new_articles:
                articles_new = self.repository.bulk_insert_articles(new_articles)
                logger.info(f"Successfully saved {articles_new} new articles to database")
            else:
                logger.info("No new articles to save")

            status = 'success'

        except Exception as e:
            error_message = str(e)
            logger.error(f"Scraping job failed: {e}", exc_info=True)
            status = 'failed'

        finally:
            # 실행 시간 계산
            execution_time = time.time() - start_time

            # 로그 저장
            self.repository.log_scraping_run(
                status=status,
                articles_found=articles_found,
                articles_new=articles_new,
                execution_time=execution_time,
                error_message=error_message
            )

            # 결과 요약
            logger.info("-" * 60)
            logger.info(f"Scraping job completed:")
            logger.info(f"  Status: {status}")
            logger.info(f"  Articles found: {articles_found}")
            logger.info(f"  New articles saved: {articles_new}")
            logger.info(f"  Duplicates skipped: {articles_found - articles_new}")
            logger.info(f"  Execution time: {execution_time:.2f}s")
            logger.info("=" * 60)

            self.is_running = False

    def start(self):
        """스케줄러 시작"""
        interval_seconds = self.settings.SCRAPING_INTERVAL_SECONDS

        logger.info(f"Starting scheduler with {interval_seconds}s interval")
        logger.info("Press Ctrl+C to stop")

        # 즉시 한 번 실행
        logger.info("Running initial scrape...")
        self.scrape_and_save()

        # 스케줄 등록
        schedule.every(interval_seconds).seconds.do(self.scrape_and_save)

        logger.info(f"Scheduler started. Next run in {interval_seconds}s")

        # 무한 루프
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Scheduler interrupted by user")
            self.stop()

    def stop(self):
        """스케줄러 종료"""
        logger.info("Stopping scheduler...")

        # 스크래퍼 세션 종료
        if hasattr(self.scraper, 'close'):
            self.scraper.close()

        # DB 연결 종료
        if self.db_manager:
            self.db_manager.close()

        logger.info("Scheduler stopped")
