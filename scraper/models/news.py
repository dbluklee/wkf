"""
뉴스 데이터 모델
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class NewsArticle:
    """뉴스 기사 데이터 클래스"""

    article_id: str
    title: str
    url: str
    content: Optional[str] = None
    content_hash: str = ""
    published_at: Optional[datetime] = None
    section_id: str = "101"  # 증권
    section_id2: str = "258"  # 시황

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        # datetime을 문자열로 변환
        if data['published_at']:
            data['published_at'] = data['published_at'].isoformat()
        return data

    def __str__(self) -> str:
        """문자열 표현"""
        return f"NewsArticle(id={self.article_id}, title={self.title[:30]}...)"

    def __repr__(self) -> str:
        return self.__str__()
