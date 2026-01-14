"""
환경 설정 관리

.env 파일에서 환경 변수를 로드하고 설정을 관리합니다.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class Settings:
    """애플리케이션 설정"""

    # Database
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # Scraping
    TARGET_URL: str
    SCRAPING_INTERVAL_SECONDS: int

    # Anti-Detection
    MIN_DELAY_SECONDS: float
    MAX_DELAY_SECONDS: float
    MIN_REQUEST_INTERVAL: float

    # HTTP
    REQUEST_TIMEOUT: int
    MAX_RETRIES: int

    # Proxy (optional)
    PROXY_ENABLED: bool
    PROXY_HTTP: Optional[str]
    PROXY_HTTPS: Optional[str]

    # Logging
    LOG_LEVEL: str
    LOG_FILE: str

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'Settings':
        """
        환경 변수에서 설정 로드

        Args:
            env_file: .env 파일 경로 (선택사항)

        Returns:
            Settings 인스턴스
        """
        # .env 파일 로드
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        return cls(
            # Database
            DB_HOST=os.getenv('DB_HOST', 'localhost'),
            DB_PORT=int(os.getenv('DB_PORT', '5432')),
            DB_NAME=os.getenv('DB_NAME', 'finance_news'),
            DB_USER=os.getenv('DB_USER', 'postgres'),
            DB_PASSWORD=os.getenv('DB_PASSWORD', ''),

            # Scraping
            TARGET_URL=os.getenv(
                'TARGET_URL',
                'https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258'
            ),
            SCRAPING_INTERVAL_SECONDS=int(os.getenv('SCRAPING_INTERVAL_SECONDS', '60')),

            # Anti-Detection
            MIN_DELAY_SECONDS=float(os.getenv('MIN_DELAY_SECONDS', '0.5')),
            MAX_DELAY_SECONDS=float(os.getenv('MAX_DELAY_SECONDS', '2.0')),
            MIN_REQUEST_INTERVAL=float(os.getenv('MIN_REQUEST_INTERVAL', '1.0')),

            # HTTP
            REQUEST_TIMEOUT=int(os.getenv('REQUEST_TIMEOUT', '30')),
            MAX_RETRIES=int(os.getenv('MAX_RETRIES', '3')),

            # Proxy
            PROXY_ENABLED=os.getenv('PROXY_ENABLED', 'false').lower() == 'true',
            PROXY_HTTP=os.getenv('PROXY_HTTP') or None,
            PROXY_HTTPS=os.getenv('PROXY_HTTPS') or None,

            # Logging
            LOG_LEVEL=os.getenv('LOG_LEVEL', 'INFO'),
            LOG_FILE=os.getenv('LOG_FILE', 'logs/scraper.log'),
        )

    def get_db_url(self) -> str:
        """PostgreSQL 연결 URL 생성"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def get_proxies(self) -> Optional[dict]:
        """
        프록시 설정 딕셔너리 반환

        Returns:
            프록시 딕셔너리 또는 None
        """
        if not self.PROXY_ENABLED:
            return None

        proxies = {}
        if self.PROXY_HTTP:
            proxies['http'] = self.PROXY_HTTP
        if self.PROXY_HTTPS:
            proxies['https'] = self.PROXY_HTTPS

        return proxies if proxies else None

    def __repr__(self) -> str:
        """설정 정보 문자열 (비밀번호 마스킹)"""
        return (
            f"Settings(\n"
            f"  DB: {self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}\n"
            f"  Target URL: {self.TARGET_URL}\n"
            f"  Interval: {self.SCRAPING_INTERVAL_SECONDS}s\n"
            f"  Delays: {self.MIN_DELAY_SECONDS}-{self.MAX_DELAY_SECONDS}s\n"
            f"  Proxy: {'Enabled' if self.PROXY_ENABLED else 'Disabled'}\n"
            f"  Log Level: {self.LOG_LEVEL}\n"
            f")"
        )
