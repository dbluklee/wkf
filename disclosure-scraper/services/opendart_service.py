"""
OpenDART API 서비스
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenDartService:
    """OpenDART API 서비스"""

    def __init__(self, api_key: str, base_url: str = "https://opendart.fss.or.kr"):
        """
        Args:
            api_key: OpenDART API 인증키
            base_url: OpenDART API 기본 URL
        """
        self.api_key = api_key
        self.base_url = base_url

    def fetch_disclosures(
        self,
        bgn_de: str,
        end_de: str,
        corp_cls: str = "",
        page_no: int = 1,
        page_count: int = 100
    ) -> Dict:
        """
        공시 목록 조회

        Args:
            bgn_de: 시작일자 (YYYYMMDD)
            end_de: 종료일자 (YYYYMMDD)
            corp_cls: 법인구분 (Y: 유가증권, K: 코스닥, N: 코넥스, E: 기타, 빈 값: 전체)
            page_no: 페이지 번호
            page_count: 페이지당 건수 (최대 100)

        Returns:
            API 응답 데이터
        """
        url = f"{self.base_url}/api/list.json"

        params = {
            "crtfc_key": self.api_key,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_no": page_no,
            "page_count": page_count,
        }

        # corp_cls가 있으면 추가
        if corp_cls:
            params["corp_cls"] = corp_cls

        try:
            logger.debug(f"Fetching disclosures: {bgn_de} ~ {end_de}, page {page_no}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # API 응답 상태 확인
            status = data.get("status")
            message = data.get("message")

            if status == "000":
                # 정상
                disclosures = data.get("list", [])
                logger.info(f"Fetched {len(disclosures)} disclosures (page {page_no})")
                return data
            elif status == "013":
                # 조회된 데이터가 없음
                logger.info(f"No disclosures found for {bgn_de} ~ {end_de}")
                return {"status": status, "message": message, "list": []}
            else:
                # 에러
                logger.error(f"OpenDART API error: {status} - {message}")
                return {"status": status, "message": message, "list": []}

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching disclosures: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            return {"status": "error", "message": str(e), "list": []}
        except Exception as e:
            logger.error(f"Failed to fetch disclosures: {e}")
            return {"status": "error", "message": str(e), "list": []}

    def fetch_disclosures_today(self, corp_cls: str = "", page_count: int = 100) -> List[Dict]:
        """
        오늘의 공시 목록 조회 (모든 페이지)

        Args:
            corp_cls: 법인구분
            page_count: 페이지당 건수

        Returns:
            공시 목록
        """
        today = datetime.now().strftime("%Y%m%d")
        return self.fetch_disclosures_range(today, today, corp_cls, page_count)

    def fetch_disclosures_range(
        self,
        bgn_de: str,
        end_de: str,
        corp_cls: str = "",
        page_count: int = 100
    ) -> List[Dict]:
        """
        기간별 공시 목록 조회 (모든 페이지)

        Args:
            bgn_de: 시작일자 (YYYYMMDD)
            end_de: 종료일자 (YYYYMMDD)
            corp_cls: 법인구분
            page_count: 페이지당 건수

        Returns:
            공시 목록
        """
        all_disclosures = []
        page_no = 1

        while True:
            result = self.fetch_disclosures(bgn_de, end_de, corp_cls, page_no, page_count)

            status = result.get("status")
            if status != "000" and status != "013":
                # 에러 발생
                break

            disclosures = result.get("list", [])
            if not disclosures:
                # 더 이상 데이터가 없음
                break

            all_disclosures.extend(disclosures)

            # 다음 페이지
            page_no += 1

            # 최대 페이지 제한 (무한 루프 방지)
            if page_no > 100:
                logger.warning("Reached maximum page limit (100)")
                break

        logger.info(f"Total fetched {len(all_disclosures)} disclosures for {bgn_de} ~ {end_de}")
        return all_disclosures

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """
        종목코드로 고유번호 조회

        Args:
            stock_code: 종목코드 (6자리)

        Returns:
            고유번호 (8자리) 또는 None

        Note:
            실제 구현 시 corp_code.xml을 다운로드하여 매핑 필요
            현재는 간단한 구현으로 None 반환
        """
        # TODO: corp_code.xml 다운로드 및 파싱 구현
        # https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key=API_KEY
        return None
