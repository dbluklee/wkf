"""
한국투자증권 (KIS) API 서비스
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import AnalyzerSettings
from utils.logger import get_logger

logger = get_logger(__name__)


class KISService:
    """한국투자증권 OpenAPI 서비스"""

    def __init__(self, settings: AnalyzerSettings):
        self.settings = settings
        self.base_url = settings.KIS_BASE_URL
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self._token = None
        self._token_expires_at = None

    def _get_valid_token(self) -> str:
        """
        유효한 OAuth2 토큰 반환 (만료 시 자동 재발급)

        Returns:
            Access token
        """
        now = datetime.now()

        # 토큰이 유효하면 재사용
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return self._token

        # 토큰 발급
        try:
            url = f"{self.base_url}/oauth2/tokenP"
            headers = {"content-type": "application/json"}
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }

            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()

            self._token = result['access_token']
            expires_in = result['expires_in']
            # 5분 여유를 두고 만료 시간 설정
            self._token_expires_at = now + timedelta(seconds=expires_in - 300)

            logger.info(f"KIS OAuth2 token issued, expires at {self._token_expires_at}")
            return self._token

        except Exception as e:
            logger.error(f"Failed to get KIS token: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def fetch_daily_prices(self, stock_code: str, days: int = 5) -> List[Dict]:
        """
        일봉 데이터 조회 (직전 N영업일)

        Args:
            stock_code: 종목코드 (6자리)
            days: 조회할 영업일 수

        Returns:
            일봉 데이터 리스트
        """
        try:
            token = self._get_valid_token()

            end_date = datetime.now().strftime('%Y%m%d')
            # 영업일 고려하여 충분한 기간 설정
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST03010100",
                "custtype": "P"  # 개인
            }
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
                "FID_PERIOD_DIV_CODE": "D",  # 일봉
                "FID_ORG_ADJ_PRC": "0"  # 수정주가 미사용
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            # API 응답 검증
            if data.get('rt_cd') != '0':
                logger.warning(f"KIS API warning: {data.get('msg1', 'Unknown error')}")
                return []

            prices = data.get('output2', [])
            # 최근 N일만 반환
            result = prices[:days] if len(prices) > days else prices

            logger.info(f"Fetched {len(result)} daily prices for {stock_code}")
            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching daily prices for {stock_code}: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch daily prices for {stock_code}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def fetch_intraday_prices(self, stock_code: str) -> List[Dict]:
        """
        당일 분봉 데이터 조회 (9:00~현재)

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            분봉 데이터 리스트
        """
        try:
            # 장 시간 확인 (9:00~15:30)
            now = datetime.now()
            current_time = now.time()

            market_open = now.replace(hour=self.settings.MARKET_OPEN_HOUR, minute=self.settings.MARKET_OPEN_MINUTE, second=0, microsecond=0).time()
            market_close = now.replace(hour=self.settings.MARKET_CLOSE_HOUR, minute=self.settings.MARKET_CLOSE_MINUTE, second=0, microsecond=0).time()

            # 장 시간 외에는 빈 리스트 반환
            if not (market_open <= current_time <= market_close):
                logger.info(f"Market is closed. Current time: {current_time}")
                return []

            # 평일(월~금)이 아니면 빈 리스트 반환
            if now.weekday() >= 5:  # 5=토요일, 6=일요일
                logger.info(f"Market is closed (weekend)")
                return []

            token = self._get_valid_token()

            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST03010200",
                "custtype": "P"  # 개인
            }
            params = {
                "FID_ETC_CLS_CODE": "",
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_HOUR_1": "090000",  # 9시부터
                "FID_PW_DATA_INCU_YN": "Y"  # 데이터 포함
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            # API 응답 검증
            if data.get('rt_cd') != '0':
                logger.warning(f"KIS API warning: {data.get('msg1', 'Unknown error')}")
                return []

            prices = data.get('output2', [])

            logger.info(f"Fetched {len(prices)} intraday prices for {stock_code}")
            return prices

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching intraday prices for {stock_code}: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch intraday prices for {stock_code}: {e}")
            # 분봉 조회 실패 시 빈 리스트 반환 (일봉만으로도 분석 가능)
            return []

    def get_latest_price(self, stock_code: str) -> Optional[int]:
        """
        최신 주가 조회 (간단 버전)

        Args:
            stock_code: 종목코드

        Returns:
            최신 주가 또는 None
        """
        daily_prices = self.fetch_daily_prices(stock_code, days=1)
        if daily_prices:
            return int(daily_prices[0].get('stck_clpr', 0))
        return None
