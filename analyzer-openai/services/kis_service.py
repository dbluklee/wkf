"""
한국투자증권 (KIS) API 서비스 (큐잉 및 캐싱 지원)
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from config.settings import AnalyzerSettings
from utils.logger import get_logger
from wkf_analyzer.services.kis_queue_service import get_kis_queue_service

logger = get_logger(__name__)


class KISService:
    """한국투자증권 OpenAPI 서비스"""

    def __init__(self, settings: AnalyzerSettings):
        self.settings = settings
        self.base_url = settings.KIS_BASE_URL
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET

        # 큐 서비스 가져오기 (싱글톤)
        self.queue_service = get_kis_queue_service()

        # 데이터베이스 설정 (토큰 공유용)
        self.queue_service.configure_database({
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'dbname': settings.DB_NAME,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD
        })

        # KIS API 설정 (첫 번째 인스턴스만 설정됨)
        self.queue_service.configure_kis_api(
            self.base_url,
            self.app_key,
            self.app_secret
        )

        # 큐 서비스가 시작되지 않았으면 시작
        if not self.queue_service.is_running:
            self.queue_service.start()

    def _get_valid_token(self) -> str:
        """
        유효한 OAuth2 토큰 반환 (공유 토큰 사용)
        모든 analyzer가 동일한 토큰을 사용하여 중복 요청 방지

        Returns:
            Access token
        """
        return self.queue_service.get_shared_token()

    def fetch_daily_prices(self, stock_code: str, days: int = 5) -> List[Dict]:
        """
        일봉 데이터 조회 (직전 N영업일) - 큐잉 및 캐싱 지원

        Args:
            stock_code: 종목코드 (6자리)
            days: 조회할 영업일 수

        Returns:
            일봉 데이터 리스트
        """
        # 캐시 키: daily_{종목코드}_{날짜}
        today = datetime.now().strftime('%Y%m%d')
        cache_key = f"daily_{stock_code}_{today}"

        # 큐 서비스를 통해 요청
        return self.queue_service.enqueue_request(
            cache_key,
            self._fetch_daily_prices_internal,
            stock_code,
            days
        )

    def _fetch_daily_prices_internal(self, stock_code: str, days: int = 5) -> List[Dict]:
        """
        일봉 데이터 조회 내부 구현 (큐 워커에서 실행)
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

            response = requests.get(url, headers=headers, params=params, timeout=10)
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

    def fetch_intraday_prices(self, stock_code: str) -> List[Dict]:
        """
        당일 분봉 데이터 조회 (9:00~현재) - 큐잉 및 캐싱 지원

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            분봉 데이터 리스트
        """
        # 캐시 키: intraday_{종목코드}_{날짜}_{시간(분단위)}
        now = datetime.now()
        cache_key = f"intraday_{stock_code}_{now.strftime('%Y%m%d_%H%M')}"

        # 큐 서비스를 통해 요청
        return self.queue_service.enqueue_request(
            cache_key,
            self._fetch_intraday_prices_internal,
            stock_code
        )

    def _fetch_intraday_prices_internal(self, stock_code: str) -> List[Dict]:
        """
        당일 분봉 데이터 조회 내부 구현 (큐 워커에서 실행)
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

            response = requests.get(url, headers=headers, params=params, timeout=10)
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

    def fetch_current_price(self, stock_code: str) -> int:
        """
        현재가 실시간 조회

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            현재가 (원)

        Raises:
            Exception: API 호출 실패 시
        """
        try:
            token = self._get_valid_token()

            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010100",
                "custtype": "P"
            }
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": stock_code
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('rt_cd') != '0':
                error_msg = data.get('msg1', 'Unknown error')
                logger.error(f"Failed to fetch current price for {stock_code}: {error_msg}")
                raise Exception(f"KIS API error: {error_msg}")

            current_price = int(data['output']['stck_prpr'])
            logger.debug(f"Current price for {stock_code}: {current_price:,}원")

            return current_price

        except Exception as e:
            logger.error(f"Failed to fetch current price for {stock_code}: {e}")
            raise

    def buy_stock(self, stock_code: str, quantity: int) -> Dict:
        """
        시장가 매수 주문

        Args:
            stock_code: 종목코드 (6자리)
            quantity: 수량

        Returns:
            {
                "order_id": "주문번호",
                "status": "submitted",
                "message": "주문 메시지"
            }

        Raises:
            Exception: 주문 실패 시
        """
        try:
            token = self._get_valid_token()

            # 실전/모의 구분
            is_real = self.settings.KIS_IS_REAL_ACCOUNT
            tr_id = "TTTC0802U" if is_real else "VTTC0802U"

            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id,
                "custtype": "P"
            }

            # 계좌번호 분리
            account_parts = self.settings.KIS_ACCOUNT_NUMBER.split('-')
            if len(account_parts) != 2:
                raise ValueError(f"Invalid account number format: {self.settings.KIS_ACCOUNT_NUMBER}")

            data = {
                "CANO": account_parts[0],
                "ACNT_PRDT_CD": account_parts[1],
                "PDNO": stock_code,
                "ORD_DVSN": "01",  # 01: 시장가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": "0"    # 시장가는 0
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()

            if result.get('rt_cd') != '0':
                error_msg = result.get('msg1', 'Unknown error')
                logger.error(f"Buy order failed for {stock_code}: {error_msg}")
                raise Exception(f"Buy order failed: {error_msg}")

            order_id = result['output'].get('KRX_FWDG_ORD_ORGNO', '') + result['output'].get('ODNO', '')
            message = result.get('msg1', '주문 성공')

            logger.info(f"✓ Buy order submitted: {stock_code} x {quantity}, order_id={order_id}")

            return {
                "order_id": order_id,
                "status": "submitted",
                "message": message
            }

        except Exception as e:
            logger.error(f"Failed to buy {stock_code}: {e}")
            raise

    def sell_stock(self, stock_code: str, quantity: int) -> Dict:
        """
        시장가 매도 주문

        Args:
            stock_code: 종목코드 (6자리)
            quantity: 수량

        Returns:
            {
                "order_id": "주문번호",
                "status": "submitted",
                "message": "주문 메시지"
            }

        Raises:
            Exception: 주문 실패 시
        """
        try:
            token = self._get_valid_token()

            # 실전/모의 구분
            is_real = self.settings.KIS_IS_REAL_ACCOUNT
            tr_id = "TTTC0801U" if is_real else "VTTC0801U"

            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id,
                "custtype": "P"
            }

            # 계좌번호 분리
            account_parts = self.settings.KIS_ACCOUNT_NUMBER.split('-')
            if len(account_parts) != 2:
                raise ValueError(f"Invalid account number format: {self.settings.KIS_ACCOUNT_NUMBER}")

            data = {
                "CANO": account_parts[0],
                "ACNT_PRDT_CD": account_parts[1],
                "PDNO": stock_code,
                "ORD_DVSN": "01",  # 01: 시장가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": "0"    # 시장가는 0
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()

            if result.get('rt_cd') != '0':
                error_msg = result.get('msg1', 'Unknown error')
                logger.error(f"Sell order failed for {stock_code}: {error_msg}")
                raise Exception(f"Sell order failed: {error_msg}")

            order_id = result['output'].get('KRX_FWDG_ORD_ORGNO', '') + result['output'].get('ODNO', '')
            message = result.get('msg1', '주문 성공')

            logger.info(f"✓ Sell order submitted: {stock_code} x {quantity}, order_id={order_id}")

            return {
                "order_id": order_id,
                "status": "submitted",
                "message": message
            }

        except Exception as e:
            logger.error(f"Failed to sell {stock_code}: {e}")
            raise
