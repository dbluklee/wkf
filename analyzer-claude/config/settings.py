"""
Analyzer 서비스 설정 관리
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AnalyzerSettings:
    """Analyzer 설정 클래스"""

    # Database Configuration
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # Anthropic Claude Configuration
    ANTHROPIC_API_KEY: str
    ANALYSIS_THRESHOLD_PERCENT: int
    MAX_RECOMMENDATIONS_PER_ARTICLE: int

    # KIS API Configuration
    KIS_APP_KEY: str
    KIS_APP_SECRET: str
    KIS_ACCOUNT_NUMBER: str
    KIS_BASE_URL: str
    KIS_IS_REAL_ACCOUNT: bool

    # Market Configuration
    MARKET_OPEN_HOUR: int
    MARKET_OPEN_MINUTE: int
    MARKET_CLOSE_HOUR: int
    MARKET_CLOSE_MINUTE: int
    STOCK_HISTORY_DAYS: int

    # Retry Configuration
    MAX_API_RETRIES: int
    RETRY_BACKOFF_FACTOR: int

    # Trading Configuration
    PROFIT_TARGET_PERCENT: float
    STOP_LOSS_PERCENT: float
    TRADE_MONITORING_INTERVAL_SECONDS: int
    TRADE_AMOUNT_PER_STOCK: int

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Logging
    LOG_LEVEL: str
    LOG_FILE: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AnalyzerSettings":
        """환경 변수에서 설정 로드"""
        return cls(
            # Database
            DB_HOST=os.getenv("DB_HOST", "localhost"),
            DB_PORT=int(os.getenv("DB_PORT", "5432")),
            DB_NAME=os.getenv("DB_NAME", "finance_news"),
            DB_USER=os.getenv("DB_USER", "wkf_user"),
            DB_PASSWORD=os.getenv("DB_PASSWORD", ""),

            # Anthropic Claude
            ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY", ""),
            ANALYSIS_THRESHOLD_PERCENT=int(os.getenv("ANALYSIS_THRESHOLD_PERCENT", "70")),
            MAX_RECOMMENDATIONS_PER_ARTICLE=int(os.getenv("MAX_RECOMMENDATIONS_PER_ARTICLE", "3")),

            # KIS API
            KIS_APP_KEY=os.getenv("KIS_APP_KEY", ""),
            KIS_APP_SECRET=os.getenv("KIS_APP_SECRET", ""),
            KIS_ACCOUNT_NUMBER=os.getenv("KIS_ACCOUNT_NUMBER", ""),
            KIS_BASE_URL=os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"),
            KIS_IS_REAL_ACCOUNT=os.getenv("KIS_IS_REAL_ACCOUNT", "false").lower() == "true",

            # Market
            MARKET_OPEN_HOUR=int(os.getenv("MARKET_OPEN_HOUR", "9")),
            MARKET_OPEN_MINUTE=int(os.getenv("MARKET_OPEN_MINUTE", "0")),
            MARKET_CLOSE_HOUR=int(os.getenv("MARKET_CLOSE_HOUR", "15")),
            MARKET_CLOSE_MINUTE=int(os.getenv("MARKET_CLOSE_MINUTE", "30")),
            STOCK_HISTORY_DAYS=int(os.getenv("STOCK_HISTORY_DAYS", "5")),

            # Retry
            MAX_API_RETRIES=int(os.getenv("MAX_API_RETRIES", "3")),
            RETRY_BACKOFF_FACTOR=int(os.getenv("RETRY_BACKOFF_FACTOR", "2")),

            # Trading
            PROFIT_TARGET_PERCENT=float(os.getenv("PROFIT_TARGET_PERCENT", "2.0")),
            STOP_LOSS_PERCENT=float(os.getenv("STOP_LOSS_PERCENT", "1.0")),
            TRADE_MONITORING_INTERVAL_SECONDS=int(os.getenv("TRADE_MONITORING_INTERVAL_SECONDS", "60")),
            TRADE_AMOUNT_PER_STOCK=int(os.getenv("TRADE_AMOUNT_PER_STOCK", "1000000")),

            # Telegram
            TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID", ""),

            # Logging
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            LOG_FILE=os.getenv("LOG_FILE", "logs/analyzer.log"),
        )

    def validate(self):
        """설정 유효성 검사"""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")

        if not self.KIS_APP_KEY or not self.KIS_APP_SECRET:
            raise ValueError("KIS_APP_KEY and KIS_APP_SECRET are required")

        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD is required")

        if not (0 <= self.ANALYSIS_THRESHOLD_PERCENT <= 100):
            raise ValueError("ANALYSIS_THRESHOLD_PERCENT must be between 0 and 100")
