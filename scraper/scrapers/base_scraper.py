"""
베이스 스크래퍼 클래스

스크래핑 방지 우회 전략이 통합된 베이스 클래스
"""

from typing import Optional, Dict
import requests

from utils.anti_detection import AntiDetectionMixin
from utils.logger import get_logger
from config.settings import Settings

logger = get_logger(__name__)


class BaseScraper(AntiDetectionMixin):
    """스크래핑 기능을 위한 베이스 클래스"""

    def __init__(self, settings: Settings):
        """
        Args:
            settings: 설정 객체
        """
        super().__init__()

        self.settings = settings

        # Anti-detection 설정 오버라이드
        self.min_delay = settings.MIN_DELAY_SECONDS
        self.max_delay = settings.MAX_DELAY_SECONDS
        self.min_request_interval = settings.MIN_REQUEST_INTERVAL

        # Session 설정
        self.session = self.setup_session_with_retry(
            max_retries=settings.MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504)
        )

        # 프록시 설정
        self.proxies = settings.get_proxies()
        if self.proxies:
            logger.info(f"Proxy enabled: {list(self.proxies.keys())}")

        logger.info("BaseScraper initialized")

    def make_request(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        HTTP 요청 실행 (우회 전략 적용)

        Args:
            url: 요청 URL
            method: HTTP 메서드 (GET, POST 등)
            headers: 추가 헤더 (선택사항)
            **kwargs: requests 라이브러리의 추가 파라미터

        Returns:
            Response 객체 또는 None (실패 시)
        """
        # Throttling 적용
        self.throttle_request()

        # 헤더 생성 (User-Agent 로테이션 포함)
        request_headers = self.get_browser_headers(referer=kwargs.pop('referer', None))

        # 추가 헤더 병합
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                timeout=self.settings.REQUEST_TIMEOUT,
                proxies=self.proxies,
                **kwargs
            )

            response.raise_for_status()
            logger.debug(f"{method} request successful: {url}")

            # 랜덤 딜레이 적용
            self.random_delay()

            return response

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout for {url}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        GET 요청

        Args:
            url: 요청 URL
            **kwargs: 추가 파라미터

        Returns:
            Response 객체 또는 None
        """
        return self.make_request(url, method='GET', **kwargs)

    def post(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        POST 요청

        Args:
            url: 요청 URL
            **kwargs: 추가 파라미터

        Returns:
            Response 객체 또는 None
        """
        return self.make_request(url, method='POST', **kwargs)

    def close(self):
        """Session 종료"""
        if self.session:
            self.session.close()
            logger.debug("Session closed")
