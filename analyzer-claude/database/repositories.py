"""
데이터 저장소 (Repository) 클래스들
"""

from typing import List, Optional
from datetime import datetime, date, time as time_type
from psycopg2.extras import RealDictCursor

from database.connection import AnalyzerDatabaseManager
from models.stock import StockRecommendation, StockPriceSnapshot, StockHolding
from models.analysis import AnalysisResult, AnalysisLog, NewsArticle, Disclosure
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsRepository:
    """뉴스 기사 조회 (scraper DB)"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def get_article_by_id(self, article_id: int) -> Optional[NewsArticle]:
        """
        ID로 기사 조회

        Args:
            article_id: 기사 ID

        Returns:
            NewsArticle 객체 또는 None
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, article_id, title, content, url, published_at, scraped_at
                        FROM news_articles
                        WHERE id = %s
                    """, (article_id,))

                    row = cursor.fetchone()
                    if row:
                        return NewsArticle(**dict(row))
                    return None
        except Exception as e:
            logger.error(f"Failed to get article {article_id}: {e}")
            return None


class RecommendationRepository:
    """종목 추천 저장소"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def save_recommendation(
        self,
        article_id: int,
        stock_code: str,
        stock_name: str,
        reasoning: str,
        llm_model: str = None,
        llm_version: str = None
    ) -> int:
        """
        종목 추천 저장

        Args:
            article_id: 기사 ID
            stock_code: 종목코드
            stock_name: 종목명
            reasoning: 추천 근거
            llm_model: LLM 모델명 ('claude', 'gemini', 'openai')
            llm_version: LLM 버전

        Returns:
            저장된 recommendation ID
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO stock_recommendations
                        (article_id, stock_code, stock_name, reasoning, llm_model, llm_version)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (article_id, stock_code, llm_model) DO UPDATE
                        SET reasoning = EXCLUDED.reasoning,
                            llm_version = EXCLUDED.llm_version
                        RETURNING id
                    """, (article_id, stock_code, stock_name, reasoning, llm_model, llm_version))

                    result = cursor.fetchone()
                    rec_id = result[0]
                    logger.info(f"Saved recommendation: {stock_name}({stock_code}) for article {article_id}")
                    return rec_id
        except Exception as e:
            logger.error(f"Failed to save recommendation: {e}")
            raise


class PriceRepository:
    """주가 데이터 저장소"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def save_prices(self, stock_code: str, prices: List[dict], data_type: str) -> int:
        """
        주가 데이터 일괄 저장

        Args:
            stock_code: 종목코드
            prices: KIS API 응답 데이터 리스트
            data_type: 'daily' or 'intraday'

        Returns:
            저장된 개수
        """
        if not prices:
            return 0

        try:
            saved_count = 0
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    for price_data in prices:
                        try:
                            if data_type == 'daily':
                                # 일봉 데이터
                                cursor.execute("""
                                    INSERT INTO stock_price_snapshots
                                    (stock_code, price_date, open_price, high_price, low_price, close_price, volume, data_type)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (stock_code, price_date, price_time, data_type) DO NOTHING
                                """, (
                                    stock_code,
                                    price_data.get('stck_bsop_date'),
                                    int(price_data.get('stck_oprc', 0)),
                                    int(price_data.get('stck_hgpr', 0)),
                                    int(price_data.get('stck_lwpr', 0)),
                                    int(price_data.get('stck_clpr', 0)),
                                    int(price_data.get('acml_vol', 0)),
                                    data_type
                                ))
                            else:
                                # 분봉 데이터
                                price_time_str = price_data.get('stck_cntg_hour', '000000')
                                price_time = time_type(
                                    int(price_time_str[0:2]),
                                    int(price_time_str[2:4]),
                                    int(price_time_str[4:6])
                                )

                                cursor.execute("""
                                    INSERT INTO stock_price_snapshots
                                    (stock_code, price_date, price_time, close_price, volume, data_type)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (stock_code, price_date, price_time, data_type) DO NOTHING
                                """, (
                                    stock_code,
                                    price_data.get('stck_bsop_date'),
                                    price_time,
                                    int(price_data.get('stck_prpr', 0)),
                                    int(price_data.get('cntg_vol', 0)),
                                    data_type
                                ))

                            saved_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to save single price data: {e}")
                            continue

            logger.info(f"Saved {saved_count}/{len(prices)} {data_type} prices for {stock_code}")
            return saved_count
        except Exception as e:
            logger.error(f"Failed to save prices: {e}")
            raise


class AnalysisRepository:
    """분석 결과 저장소"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def save_analysis(
        self,
        article_id: int,
        recommendation_id: int,
        stock_code: str,
        probability: int,
        reasoning: str,
        target_price: Optional[int] = None,
        stop_loss: Optional[int] = None,
        llm_model: str = None,
        llm_version: str = None
    ) -> int:
        """
        분석 결과 저장

        Args:
            article_id: 기사 ID
            recommendation_id: 추천 ID
            stock_code: 종목코드
            probability: 상승 확률 (0-100)
            reasoning: 분석 근거
            target_price: 목표가
            stop_loss: 손절가
            llm_model: LLM 모델명
            llm_version: LLM 버전

        Returns:
            저장된 analysis ID
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO stock_analysis_results
                        (article_id, recommendation_id, stock_code, probability, reasoning, target_price, stop_loss, llm_model, llm_version)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (recommendation_id) DO UPDATE
                        SET probability = EXCLUDED.probability,
                            reasoning = EXCLUDED.reasoning,
                            target_price = EXCLUDED.target_price,
                            stop_loss = EXCLUDED.stop_loss,
                            llm_model = EXCLUDED.llm_model,
                            llm_version = EXCLUDED.llm_version
                        RETURNING id
                    """, (article_id, recommendation_id, stock_code, probability, reasoning, target_price, stop_loss, llm_model, llm_version))

                    result = cursor.fetchone()
                    analysis_id = result[0]
                    logger.info(f"Saved analysis result: {stock_code} with {probability}% probability")
                    return analysis_id
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
            raise


class HoldingsRepository:
    """보유 종목 저장소"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def add_holding(
        self,
        analysis_id: int,
        stock_code: str,
        stock_name: str,
        target_price: Optional[int] = None,
        stop_loss: Optional[int] = None,
        llm_model: str = None,
        llm_version: str = None
    ) -> int:
        """
        보유 종목 추가

        Args:
            analysis_id: 분석 결과 ID
            stock_code: 종목코드
            stock_name: 종목명
            target_price: 목표가
            stop_loss: 손절가
            llm_model: LLM 모델명
            llm_version: LLM 버전

        Returns:
            저장된 holding ID
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO stock_holdings
                        (analysis_id, stock_code, stock_name, target_price, stop_loss, status, llm_model, llm_version)
                        VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s)
                        RETURNING id
                    """, (analysis_id, stock_code, stock_name, target_price, stop_loss, llm_model, llm_version))

                    result = cursor.fetchone()
                    holding_id = result[0]
                    logger.info(f"Added holding: {stock_name}({stock_code})")
                    return holding_id
        except Exception as e:
            logger.error(f"Failed to add holding: {e}")
            raise

    def get_pending_holdings(self) -> List[dict]:
        """
        대기중인 보유 종목 조회

        Returns:
            보유 종목 리스트
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, stock_code, stock_name, target_price, stop_loss, added_at
                        FROM stock_holdings
                        WHERE status = 'pending'
                        ORDER BY added_at DESC
                    """)
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get pending holdings: {e}")
            return []


class LogRepository:
    """분석 로그 저장소"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def log_analysis(
        self,
        article_id: Optional[int],
        status: str,
        step: Optional[str],
        error_message: Optional[str],
        execution_time: float
    ):
        """
        분석 실행 로그 저장

        Args:
            article_id: 기사 ID
            status: success, partial, failed
            step: recommendation, price_fetch, analysis, storage, complete
            error_message: 에러 메시지
            execution_time: 실행 시간 (초)
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO analysis_logs
                        (article_id, status, step, error_message, execution_time)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (article_id, status, step, error_message, execution_time))
                    logger.debug(f"Analysis log saved: {status} - {step}")
        except Exception as e:
            logger.error(f"Failed to log analysis: {e}")


class DisclosureRepository:
    """공시 조회 (disclosure-scraper DB)"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.db_manager = db_manager

    def get_disclosure_by_id(self, disclosure_id: int) -> Optional[Disclosure]:
        """
        ID로 공시 조회

        Args:
            disclosure_id: 공시 ID

        Returns:
            Disclosure 객체 또는 None
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, rcept_no, corp_name, stock_code, report_nm, rcept_dt,
                               corp_cls, corp_code, flr_nm, rm, scraped_at
                        FROM disclosures
                        WHERE id = %s
                    """, (disclosure_id,))

                    row = cursor.fetchone()
                    if row:
                        return Disclosure(**dict(row))
                    return None
        except Exception as e:
            logger.error(f"Failed to get disclosure {disclosure_id}: {e}")
            return None


class Repositories:
    """모든 Repository를 담는 컨테이너 클래스"""

    def __init__(self, db_manager: AnalyzerDatabaseManager):
        self.news_repo = NewsRepository(db_manager)
        self.disclosure_repo = DisclosureRepository(db_manager)
        self.recommendation_repo = RecommendationRepository(db_manager)
        self.price_repo = PriceRepository(db_manager)
        self.analysis_repo = AnalysisRepository(db_manager)
        self.holdings_repo = HoldingsRepository(db_manager)
        self.log_repo = LogRepository(db_manager)
