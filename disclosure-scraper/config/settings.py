"""
공시 스크래퍼 설정
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DisclosureScraperSettings:
    """공시 스크래퍼 설정 클래스"""

    # Database Configuration
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # OpenDART API Configuration
    OPENDART_API_KEY: str
    OPENDART_BASE_URL: str

    # Scraping Configuration
    SCRAPING_INTERVAL_SECONDS: int  # 스크래핑 주기 (초)
    CORP_CLS: str  # 법인구분 (Y: 유가증권, K: 코스닥, N: 코넥스, E: 기타, 빈 값: 전체)
    PAGE_COUNT: int  # 페이지당 조회 건수 (최대 100)

    # Logging
    LOG_LEVEL: str
    LOG_FILE: str

    @classmethod
    def from_env(cls) -> "DisclosureScraperSettings":
        """환경 변수에서 설정 로드"""
        return cls(
            # Database
            DB_HOST=os.getenv("DB_HOST", "localhost"),
            DB_PORT=int(os.getenv("DB_PORT", "5432")),
            DB_NAME=os.getenv("DB_NAME", "finance_news"),
            DB_USER=os.getenv("DB_USER", "wkf_user"),
            DB_PASSWORD=os.getenv("DB_PASSWORD", ""),

            # OpenDART API
            OPENDART_API_KEY=os.getenv("OPENDART_API_KEY", ""),
            OPENDART_BASE_URL=os.getenv("OPENDART_BASE_URL", "https://opendart.fss.or.kr"),

            # Scraping
            SCRAPING_INTERVAL_SECONDS=int(os.getenv("DISCLOSURE_SCRAPING_INTERVAL_SECONDS", "300")),  # 기본 5분
            CORP_CLS=(os.getenv("DISCLOSURE_CORP_CLS", "") or "").strip(),  # 빈 값: 전체
            PAGE_COUNT=int(os.getenv("DISCLOSURE_PAGE_COUNT", "100")),

            # Logging
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            LOG_FILE=os.getenv("LOG_FILE", "logs/disclosure-scraper.log"),
        )

    def validate(self):
        """설정 유효성 검사"""
        if not self.OPENDART_API_KEY:
            raise ValueError("OPENDART_API_KEY is required")

        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is required")

        if self.SCRAPING_INTERVAL_SECONDS < 10:
            raise ValueError("SCRAPING_INTERVAL_SECONDS must be at least 10 seconds")

        if not (1 <= self.PAGE_COUNT <= 100):
            raise ValueError("PAGE_COUNT must be between 1 and 100")

        # CORP_CLS 검증: 빈 문자열 또는 Y, K, N, E 중 하나
        if self.CORP_CLS and self.CORP_CLS not in ['Y', 'K', 'N', 'E']:
            raise ValueError(f"CORP_CLS must be one of: Y, K, N, E, or empty string (got: '{self.CORP_CLS}', repr: {repr(self.CORP_CLS)})")
