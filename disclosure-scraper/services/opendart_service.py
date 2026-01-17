"""
OpenDART API 서비스
"""
import requests
import zipfile
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
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

    def fetch_disclosure_document(self, rcept_no: str) -> Optional[str]:
        """
        공시 원본 문서 다운로드 및 텍스트 추출

        Args:
            rcept_no: 접수번호 (예: 20260116000001)

        Returns:
            공시 본문 텍스트 (최대 20,000자) 또는 None (실패 시)
        """
        url = f"{self.base_url}/api/document.xml"

        params = {
            "crtfc_key": self.api_key,
            "rcept_no": rcept_no
        }

        try:
            logger.debug(f"Fetching disclosure document: {rcept_no}")
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # ZIP 파일 내 모든 파일 목록
                file_list = zip_file.namelist()
                logger.debug(f"Found {len(file_list)} files in ZIP: {file_list}")

                # 모든 파일의 텍스트 추출 (XML/HTML 파싱)
                all_text = []
                for file_name in file_list:
                    try:
                        content = zip_file.read(file_name)

                        # HTML/XML 파싱
                        soup = BeautifulSoup(content, 'html.parser')

                        # script, style 태그 제거
                        for tag in soup(['script', 'style']):
                            tag.decompose()

                        # 텍스트 추출
                        text = soup.get_text(separator='\n', strip=True)
                        all_text.append(text)
                        logger.debug(f"Extracted {len(text)} characters from {file_name}")
                    except Exception as e:
                        logger.warning(f"Failed to parse {file_name}: {e}")

                # 모든 텍스트 결합
                full_text = '\n\n'.join(all_text)

                # 텍스트 정리 (연속된 공백/줄바꿈 제거)
                import re
                full_text = re.sub(r'\n\s*\n+', '\n\n', full_text)
                full_text = re.sub(r' +', ' ', full_text)

                # 최대 20,000자로 제한 (LLM 컨텍스트 고려)
                if len(full_text) > 20000:
                    logger.info(f"Document text truncated from {len(full_text)} to 20,000 characters")
                    full_text = full_text[:20000] + "\n\n[문서가 너무 길어 일부 생략됨]"

                logger.info(f"Successfully fetched document for {rcept_no}: {len(full_text)} characters")
                return full_text

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching document {rcept_no}: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            return None
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file for {rcept_no}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch disclosure document {rcept_no}: {e}")
            return None
