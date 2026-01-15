"""
한국 주식 시장 관련 유틸리티
- 시장 개장 시간 체크
- 영업일 판단
"""
from datetime import datetime, time
import pytz


def is_market_open(settings) -> bool:
    """
    한국 주식 시장 개장 여부 확인

    Args:
        settings: 설정 객체 (MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE, MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE 포함)

    Returns:
        bool: 시장 개장 시간이면 True, 아니면 False
    """
    # 한국 시간대로 현재 시각 가져오기
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)

    # 주말 체크 (토요일: 5, 일요일: 6)
    if now.weekday() >= 5:
        return False

    # 시장 시간 체크
    market_open = time(settings.MARKET_OPEN_HOUR, settings.MARKET_OPEN_MINUTE)
    market_close = time(settings.MARKET_CLOSE_HOUR, settings.MARKET_CLOSE_MINUTE)
    current_time = now.time()

    # 09:00 <= 현재시간 <= 15:30
    return market_open <= current_time <= market_close


def get_current_kst_time() -> datetime:
    """
    현재 한국 시간 반환

    Returns:
        datetime: 한국 시간대의 현재 시각
    """
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst)


def is_trading_day(date: datetime = None) -> bool:
    """
    주어진 날짜가 거래일인지 확인 (주말 제외)

    Args:
        date: 확인할 날짜 (기본값: 오늘)

    Returns:
        bool: 평일이면 True, 주말이면 False

    Note:
        공휴일은 별도로 체크하지 않음 (향후 추가 가능)
    """
    if date is None:
        date = get_current_kst_time()

    # 월요일(0) ~ 금요일(4)만 거래일
    return date.weekday() < 5
