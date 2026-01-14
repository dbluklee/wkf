"""
스크래핑 방지 우회 전략 유틸리티

User-Agent 로테이션, 랜덤 딜레이, HTTP 헤더 다양화 등을 제공합니다.
"""

import random
import time
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests


# 다양한 실제 브라우저 User-Agent 풀
USER_AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',

    # Chrome on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

    # Chrome on Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',

    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',

    # Firefox on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',

    # Firefox on Linux
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',

    # Safari on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',

    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',

    # Edge on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]


class AntiDetectionMixin:
    """스크래핑 방지 우회 기능을 제공하는 Mixin 클래스"""

    def __init__(self):
        self.last_request_time: Optional[float] = None
        self.min_request_interval: float = 1.0  # 최소 요청 간격 (초)
        self.min_delay: float = 0.5
        self.max_delay: float = 2.0

    def get_random_user_agent(self) -> str:
        """랜덤하게 User-Agent 선택"""
        return random.choice(USER_AGENTS)

    def get_browser_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """
        실제 브라우저처럼 보이는 HTTP 헤더 생성

        Args:
            referer: Referer 헤더 값 (선택사항)

        Returns:
            HTTP 헤더 딕셔너리
        """
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none' if not referer else 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        if referer:
            headers['Referer'] = referer

        return headers

    def random_delay(self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None):
        """
        랜덤 딜레이 적용

        Args:
            min_seconds: 최소 딜레이 시간 (초)
            max_seconds: 최대 딜레이 시간 (초)
        """
        min_val = min_seconds if min_seconds is not None else self.min_delay
        max_val = max_seconds if max_seconds is not None else self.max_delay

        delay = random.uniform(min_val, max_val)
        time.sleep(delay)

    def throttle_request(self, min_interval: Optional[float] = None):
        """
        최소 요청 간격 보장 (throttling)

        Args:
            min_interval: 최소 간격 (초)
        """
        interval = min_interval if min_interval is not None else self.min_request_interval

        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < interval:
                sleep_time = interval - elapsed
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def setup_session_with_retry(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        status_forcelist: tuple = (429, 500, 502, 503, 504)
    ) -> requests.Session:
        """
        Retry 전략이 적용된 requests.Session 생성

        Args:
            max_retries: 최대 재시도 횟수
            backoff_factor: 재시도 간 대기 시간 배수
            status_forcelist: 재시도할 HTTP 상태 코드

        Returns:
            설정된 requests.Session 객체
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session


def get_random_user_agent() -> str:
    """랜덤 User-Agent 반환 (독립 함수)"""
    return random.choice(USER_AGENTS)


def random_sleep(min_seconds: float = 0.5, max_seconds: float = 2.0):
    """랜덤 sleep (독립 함수)"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
