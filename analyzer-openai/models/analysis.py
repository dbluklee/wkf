"""
분석 관련 데이터 모델
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class AnalysisResult:
    """Claude Phase 2 분석 결과"""
    article_id: int
    recommendation_id: int
    stock_code: str
    probability: int  # 0-100
    reasoning: str
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None
    id: Optional[int] = None
    analyzed_at: Optional[datetime] = None


@dataclass
class AnalysisLog:
    """분석 실행 로그"""
    status: str  # success, partial, failed
    step: Optional[str] = None  # recommendation, price_fetch, analysis, storage, complete
    article_id: Optional[int] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class NewsArticle:
    """뉴스 기사 (scraper DB에서 조회용)"""
    id: int
    article_id: str
    title: str
    content: str
    url: str
    published_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None

@dataclass
class Disclosure:
    """공시 데이터 (disclosure-scraper DB에서 조회용)"""
    id: int
    rcept_no: str  # 접수번호
    corp_name: str  # 회사명
    stock_code: Optional[str]  # 종목코드
    report_nm: str  # 보고서명
    rcept_dt: str  # 접수일자 (YYYYMMDD)
    corp_cls: Optional[str] = None  # 법인구분
    corp_code: Optional[str] = None  # 고유번호
    flr_nm: Optional[str] = None  # 공시제출인명
    rm: Optional[str] = None  # 비고
    scraped_at: Optional[datetime] = None
