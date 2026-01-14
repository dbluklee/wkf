"""
시간대 처리 유틸리티

한국 시간대(KST, Asia/Seoul) 관련 함수
"""

from datetime import datetime
import pytz

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')


def get_kst_now() -> datetime:
    """
    현재 한국 시간 반환

    Returns:
        현재 한국 시간 (timezone-aware datetime)
    """
    return datetime.now(KST)


def to_kst(dt: datetime) -> datetime:
    """
    datetime 객체를 한국 시간대로 변환

    Args:
        dt: datetime 객체 (timezone-aware 또는 naive)

    Returns:
        한국 시간대로 변환된 datetime (timezone-aware)
    """
    if dt is None:
        return None

    # timezone-naive인 경우 UTC로 가정하고 변환
    if dt.tzinfo is None:
        utc_dt = pytz.utc.localize(dt)
        return utc_dt.astimezone(KST)

    # 이미 timezone-aware인 경우 KST로 변환
    return dt.astimezone(KST)


def naive_to_kst(dt: datetime) -> datetime:
    """
    timezone-naive datetime을 한국 시간으로 가정하고 timezone-aware로 변환

    Args:
        dt: timezone-naive datetime 객체

    Returns:
        한국 시간대로 localize된 datetime
    """
    if dt is None:
        return None

    if dt.tzinfo is not None:
        # 이미 timezone-aware인 경우 그대로 반환
        return dt

    # naive datetime을 한국 시간으로 localize
    return KST.localize(dt)


def remove_timezone(dt: datetime) -> datetime:
    """
    timezone 정보를 제거하여 naive datetime으로 변환
    (PostgreSQL에 저장할 때 사용 - DB에서 TIMESTAMP 타입 사용 시)

    Args:
        dt: timezone-aware datetime 객체

    Returns:
        timezone 정보가 제거된 naive datetime
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt

    return dt.replace(tzinfo=None)
