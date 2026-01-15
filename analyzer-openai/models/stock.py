"""
주식 관련 데이터 모델
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class StockRecommendation:
    """Claude Phase 1 종목 추천 결과"""
    stock_code: str
    stock_name: str
    reasoning: str
    article_id: Optional[int] = None
    id: Optional[int] = None
    recommended_at: Optional[datetime] = None


@dataclass
class StockPriceSnapshot:
    """KIS API 주가 스냅샷"""
    stock_code: str
    price_date: str  # YYYYMMDD 형식
    data_type: str  # 'daily' or 'intraday'
    open_price: Optional[int] = None
    high_price: Optional[int] = None
    low_price: Optional[int] = None
    close_price: Optional[int] = None
    volume: Optional[int] = None
    price_time: Optional[str] = None  # HHMMSS 형식 (intraday only)
    id: Optional[int] = None
    fetched_at: Optional[datetime] = None


@dataclass
class StockHolding:
    """보유 종목 정보"""
    stock_code: str
    stock_name: str
    analysis_id: int
    quantity: int = 0
    average_price: Optional[int] = None
    target_price: Optional[int] = None
    stop_loss: Optional[int] = None
    status: str = 'pending'  # pending, bought, sold
    id: Optional[int] = None
    added_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
