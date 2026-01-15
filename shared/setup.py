"""
WKF Analyzer 공유 라이브러리
Multi-LLM 주식 분석 시스템의 공통 컴포넌트
"""
from setuptools import setup, find_packages

setup(
    name="wkf-analyzer",
    version="0.1.0",
    description="WKF Finance News Analyzer - Shared Library",
    packages=find_packages(),
    install_requires=[
        # Database
        "psycopg2-binary==2.9.9",

        # HTTP Client
        "requests==2.31.0",
        "urllib3==2.2.0",

        # Utilities
        "python-dotenv==1.0.1",
        "python-dateutil==2.8.2",
        "pytz==2024.1",

        # Retry Logic
        "tenacity==8.2.3",

        # Logging
        "colorlog==6.8.2",
    ],
    python_requires=">=3.11",
)
