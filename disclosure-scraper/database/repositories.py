"""
공시 데이터 Repository
"""
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class DisclosureRepository:
    """공시 데이터 Repository"""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DisclosureDatabaseManager 인스턴스
        """
        self.db_manager = db_manager

    def _calculate_content_hash(self, disclosure: Dict) -> str:
        """
        공시 내용 해시 계산 (중복 방지용)

        Args:
            disclosure: 공시 데이터

        Returns:
            SHA-256 해시 값
        """
        # rcept_no를 기반으로 해시 생성 (접수번호는 고유함)
        rcept_no = disclosure.get("rcept_no", "")
        content = f"{rcept_no}"
        return hashlib.sha256(content.encode()).hexdigest()

    def save_disclosure(self, disclosure: Dict) -> Optional[int]:
        """
        공시 데이터 저장

        Args:
            disclosure: 공시 데이터

        Returns:
            저장된 공시 ID 또는 None (중복 시)
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        try:
            content_hash = self._calculate_content_hash(disclosure)

            # 종목코드 추출 (stock_code 필드가 없으면 빈 문자열)
            stock_code = disclosure.get("stock_code", "")

            cursor.execute("""
                INSERT INTO disclosures (
                    rcept_no, corp_cls, corp_code, corp_name, stock_code,
                    report_nm, flr_nm, rcept_dt, rm, content_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
                RETURNING id
            """, (
                disclosure.get("rcept_no"),
                disclosure.get("corp_cls"),
                disclosure.get("corp_code"),
                disclosure.get("corp_name"),
                stock_code,
                disclosure.get("report_nm"),
                disclosure.get("flr_nm"),
                disclosure.get("rcept_dt"),
                disclosure.get("rm"),
                content_hash
            ))

            result = cursor.fetchone()
            conn.commit()

            if result:
                disclosure_id = result[0]
                logger.info(f"Saved disclosure: {disclosure.get('corp_name')} - {disclosure.get('report_nm')} (ID: {disclosure_id})")
                return disclosure_id
            else:
                logger.debug(f"Duplicate disclosure skipped: {disclosure.get('rcept_no')}")
                return None

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save disclosure: {e}")
            logger.error(f"Disclosure data: {disclosure}")
            return None
        finally:
            cursor.close()

    def save_disclosures_batch(self, disclosures: List[Dict]) -> Dict:
        """
        공시 데이터 일괄 저장

        Args:
            disclosures: 공시 데이터 리스트

        Returns:
            저장 결과 통계 및 새로 저장된 공시 목록
        """
        new_count = 0
        duplicate_count = 0
        error_count = 0
        new_disclosures = []  # 새로 저장된 공시 목록

        for disclosure in disclosures:
            try:
                result = self.save_disclosure(disclosure)
                if result is not None:
                    new_count += 1
                    # 새로 저장된 공시 정보 추가
                    new_disclosures.append({
                        "id": result,
                        "rcept_no": disclosure.get("rcept_no"),
                        "corp_name": disclosure.get("corp_name"),
                        "stock_code": disclosure.get("stock_code", ""),
                        "report_nm": disclosure.get("report_nm"),
                        "rcept_dt": disclosure.get("rcept_dt")
                    })
                else:
                    duplicate_count += 1
            except Exception as e:
                logger.error(f"Error saving disclosure: {e}")
                error_count += 1

        logger.info(f"Batch save completed: {new_count} new, {duplicate_count} duplicates, {error_count} errors")

        return {
            "new_count": new_count,
            "duplicate_count": duplicate_count,
            "error_count": error_count,
            "total": len(disclosures),
            "new_disclosures": new_disclosures
        }

    def get_latest_rcept_dt(self) -> Optional[str]:
        """
        가장 최근 공시 접수일자 조회

        Returns:
            접수일자 (YYYYMMDD) 또는 None
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT rcept_dt
                FROM disclosures
                ORDER BY rcept_dt DESC, scraped_at DESC
                LIMIT 1
            """)

            result = cursor.fetchone()
            if result:
                return result[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get latest rcept_dt: {e}")
            return None
        finally:
            cursor.close()

    def update_document_content(self, disclosure_id: int, document_content: str) -> bool:
        """
        공시 상세 내용 업데이트

        Args:
            disclosure_id: 공시 ID
            document_content: 공시 상세 내용

        Returns:
            성공 여부
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE disclosures
                SET document_content = %s
                WHERE id = %s
            """, (document_content, disclosure_id))

            conn.commit()
            logger.debug(f"Updated document content for disclosure ID {disclosure_id}: {len(document_content)} characters")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update document content for disclosure ID {disclosure_id}: {e}")
            return False
        finally:
            cursor.close()


class ScrapingLogRepository:
    """스크래핑 로그 Repository"""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DisclosureDatabaseManager 인스턴스
        """
        self.db_manager = db_manager

    def log_scraping(
        self,
        bgn_de: str,
        end_de: str,
        total_fetched: int,
        new_count: int,
        duplicate_count: int,
        error_count: int,
        execution_time: float
    ):
        """
        스크래핑 로그 저장

        Args:
            bgn_de: 시작일자
            end_de: 종료일자
            total_fetched: 총 조회 건수
            new_count: 신규 저장 건수
            duplicate_count: 중복 건수
            error_count: 에러 건수
            execution_time: 실행 시간 (초)
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO disclosure_scraping_logs (
                    bgn_de, end_de, total_fetched, new_count, duplicate_count,
                    error_count, execution_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                bgn_de, end_de, total_fetched, new_count, duplicate_count,
                error_count, execution_time
            ))

            conn.commit()
            logger.debug(f"Scraping log saved: {bgn_de} ~ {end_de}, {new_count} new disclosures")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save scraping log: {e}")
        finally:
            cursor.close()
