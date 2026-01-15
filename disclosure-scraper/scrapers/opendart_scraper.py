"""
OpenDART 공시 스크래퍼
"""
import time
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenDartScraper:
    """OpenDART 공시 스크래퍼"""

    def __init__(self, opendart_service, disclosure_repo, scraping_log_repo, settings):
        """
        Args:
            opendart_service: OpenDartService 인스턴스
            disclosure_repo: DisclosureRepository 인스턴스
            scraping_log_repo: ScrapingLogRepository 인스턴스
            settings: DisclosureScraperSettings 인스턴스
        """
        self.opendart = opendart_service
        self.disclosure_repo = disclosure_repo
        self.log_repo = scraping_log_repo
        self.settings = settings

    def scrape_once(self):
        """공시 1회 스크래핑"""
        logger.info("=" * 60)
        logger.info("Starting disclosure scraping")
        logger.info("=" * 60)

        start_time = time.time()

        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")

        # 최근 공시 접수일자 조회
        latest_rcept_dt = self.disclosure_repo.get_latest_rcept_dt()

        if latest_rcept_dt:
            # 최근 공시부터 오늘까지 조회
            bgn_de = latest_rcept_dt
            logger.info(f"Fetching disclosures from {bgn_de} to {today}")
        else:
            # 데이터가 없으면 오늘만 조회
            bgn_de = today
            logger.info(f"No previous disclosures found, fetching today's disclosures only")

        # 공시 조회
        disclosures = self.opendart.fetch_disclosures_range(
            bgn_de,
            today,
            self.settings.CORP_CLS,
            self.settings.PAGE_COUNT
        )

        # 데이터베이스에 저장
        if disclosures:
            result = self.disclosure_repo.save_disclosures_batch(disclosures)

            new_count = result["new_count"]
            duplicate_count = result["duplicate_count"]
            error_count = result["error_count"]
            total_fetched = len(disclosures)

            logger.info(f"Scraping completed:")
            logger.info(f"  - Total fetched: {total_fetched}")
            logger.info(f"  - New: {new_count}")
            logger.info(f"  - Duplicates: {duplicate_count}")
            logger.info(f"  - Errors: {error_count}")

            # 스크래핑 로그 저장
            execution_time = time.time() - start_time
            self.log_repo.log_scraping(
                bgn_de,
                today,
                total_fetched,
                new_count,
                duplicate_count,
                error_count,
                execution_time
            )
        else:
            logger.info("No disclosures found")

        logger.info("=" * 60)

    def run_continuous(self):
        """지속적인 스크래핑 실행 (9:00~15:00 사이에만)"""
        logger.info(f"Starting continuous scraping (interval: {self.settings.SCRAPING_INTERVAL_SECONDS}s)")
        logger.info("Scraping active hours: 09:00 ~ 15:00 (weekdays only)")

        while True:
            try:
                # 현재 시간 체크
                now = datetime.now()
                current_time = now.time()

                # 평일(월~금) 체크
                if now.weekday() >= 5:  # 5=토요일, 6=일요일
                    logger.debug("Weekend - skipping scraping")
                    time.sleep(self.settings.SCRAPING_INTERVAL_SECONDS)
                    continue

                # 시간 체크 (9:00~15:00)
                from datetime import time as time_type
                scraping_start = time_type(9, 0)
                scraping_end = time_type(15, 0)

                if not (scraping_start <= current_time <= scraping_end):
                    logger.debug(f"Outside scraping hours ({current_time.strftime('%H:%M')}), skipping")
                    time.sleep(self.settings.SCRAPING_INTERVAL_SECONDS)
                    continue

                # 스크래핑 실행
                self.scrape_once()
            except Exception as e:
                logger.error(f"Scraping error: {e}")

            # 다음 실행까지 대기
            logger.info(f"Waiting {self.settings.SCRAPING_INTERVAL_SECONDS} seconds until next scraping...")
            time.sleep(self.settings.SCRAPING_INTERVAL_SECONDS)
