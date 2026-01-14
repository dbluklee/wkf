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
