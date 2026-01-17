"""
Dashboard 설정
"""
import os
from dotenv import load_dotenv

load_dotenv()


class DashboardSettings:
    """Dashboard 설정 클래스"""

    # Database Configuration
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "finance_news")
    DB_USER: str = os.getenv("DB_USER", "wkf_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # Dashboard Configuration
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8000"))

    @property
    def db_url(self) -> str:
        """PostgreSQL 연결 URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = DashboardSettings()
