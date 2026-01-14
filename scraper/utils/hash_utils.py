"""
해시 유틸리티

중복 체크를 위한 해시 함수 제공
"""

import hashlib
from typing import Optional
from urllib.parse import urlparse, parse_qs


def generate_content_hash(title: str, content: str = "") -> str:
    """
    뉴스 제목과 내용을 조합하여 SHA256 해시 생성
    중복 뉴스 감지에 사용

    Args:
        title: 뉴스 제목
        content: 뉴스 내용 (선택사항)

    Returns:
        SHA256 해시 문자열 (16진수)
    """
    combined = f"{title.strip()}{content.strip()}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def generate_article_id_from_url(url: str) -> str:
    """
    네이버 뉴스 URL에서 고유 article_id 추출

    네이버 금융 뉴스 URL 형식:
    - https://finance.naver.com/news/read.naver?article_id=0005123456&office_id=001
    - https://n.news.naver.com/mnews/article/001/0012345678

    Args:
        url: 뉴스 URL

    Returns:
        추출된 article_id 또는 URL 해시
    """
    try:
        parsed = urlparse(url)

        # 쿼리 파라미터에서 추출 시도
        if parsed.query:
            params = parse_qs(parsed.query)

            # office_id와 article_id 조합
            if 'office_id' in params and 'article_id' in params:
                office_id = params['office_id'][0]
                article_id = params['article_id'][0]
                return f"naver_{office_id}_{article_id}"

            # article_id만 있는 경우
            if 'article_id' in params:
                return f"naver_{params['article_id'][0]}"

        # 경로에서 추출 시도 (새로운 URL 형식)
        # 예: /mnews/article/001/0012345678
        path_parts = parsed.path.strip('/').split('/')
        if 'article' in path_parts:
            idx = path_parts.index('article')
            if len(path_parts) > idx + 2:
                office_id = path_parts[idx + 1]
                article_id = path_parts[idx + 2]
                return f"naver_{office_id}_{article_id}"

        # 추출 실패 시 URL 전체의 MD5 해시 사용
        return f"hash_{hashlib.md5(url.encode()).hexdigest()}"

    except Exception:
        # 모든 예외 발생 시 URL 해시 사용
        return f"hash_{hashlib.md5(url.encode()).hexdigest()}"


def generate_article_id(
    url: str,
    title: Optional[str] = None,
    published_at: Optional[str] = None
) -> str:
    """
    뉴스 기사 고유 ID 생성

    URL에서 추출하거나, 실패 시 title + published_at 조합으로 생성

    Args:
        url: 뉴스 URL
        title: 뉴스 제목 (fallback용)
        published_at: 발행 시각 (fallback용)

    Returns:
        고유 article_id
    """
    # URL에서 추출 시도
    article_id = generate_article_id_from_url(url)

    # URL에서 추출 실패하고 title이 있는 경우
    if article_id.startswith('hash_') and title:
        # title + published_at으로 해시 생성
        combined = f"{title}{published_at or ''}"
        content_hash = hashlib.md5(combined.encode()).hexdigest()
        return f"title_{content_hash[:16]}"

    return article_id
