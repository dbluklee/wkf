"""
데이터베이스 연결 및 쿼리
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from config import settings


class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self):
        self.db_config = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "database": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
        }

    def get_connection(self):
        """데이터베이스 연결 생성"""
        return psycopg2.connect(**self.db_config)

    def get_disclosures_by_date(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """날짜별 뉴스 기사 조회"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        id,
                        article_id,
                        title,
                        content,
                        url,
                        published_at,
                        scraped_at
                    FROM news_articles
                    WHERE status = 'active'
                """
                params = []

                if start_date:
                    query += " AND DATE(scraped_at) >= %s"
                    params.append(start_date)

                if end_date:
                    query += " AND DATE(scraped_at) <= %s"
                    params.append(end_date)

                query += " ORDER BY scraped_at DESC, id DESC LIMIT 100"

                cur.execute(query, params)
                return cur.fetchall()

    def get_analysis_results(self, article_id: int) -> List[Dict[str, Any]]:
        """특정 기사의 LLM 분석 결과 조회"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        sar.id,
                        sar.article_id,
                        sar.stock_code,
                        sar.probability,
                        sar.reasoning,
                        sar.target_price,
                        sar.stop_loss,
                        sar.llm_model,
                        sar.analyzed_at,
                        sr.stock_name,
                        sr.reasoning as recommendation_reasoning
                    FROM stock_analysis_results sar
                    LEFT JOIN stock_recommendations sr ON sar.recommendation_id = sr.id
                    WHERE sar.article_id = %s
                    ORDER BY sar.probability DESC, sar.llm_model
                """
                cur.execute(query, [article_id])
                return cur.fetchall()

    def get_stock_recommendations(self, article_id: int) -> List[Dict[str, Any]]:
        """특정 기사의 종목 추천 조회"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        id,
                        article_id,
                        stock_code,
                        stock_name,
                        reasoning,
                        llm_model,
                        recommended_at
                    FROM stock_recommendations
                    WHERE article_id = %s
                    ORDER BY llm_model, recommended_at
                """
                cur.execute(query, [article_id])
                return cur.fetchall()

    def get_holdings_by_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """분석 결과에 대한 거래 정보 조회"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        id,
                        analysis_id,
                        stock_code,
                        stock_name,
                        quantity,
                        average_price,
                        target_price,
                        stop_loss,
                        status,
                        llm_model,
                        added_at,
                        updated_at
                    FROM stock_holdings
                    WHERE analysis_id = %s
                """
                cur.execute(query, [analysis_id])
                return cur.fetchone()

    def get_llm_performance_summary(self) -> List[Dict[str, Any]]:
        """LLM별 성과 요약"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        llm_model,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN roi_percent > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN roi_percent <= 0 THEN 1 ELSE 0 END) as losses,
                        ROUND(AVG(roi_percent)::numeric, 2) as avg_roi,
                        SUM(profit_loss) as total_profit,
                        ROUND((100.0 * SUM(CASE WHEN roi_percent > 0 THEN 1 ELSE 0 END) / COUNT(*))::numeric, 1) as win_rate
                    FROM llm_performance_tracking
                    GROUP BY llm_model
                    ORDER BY avg_roi DESC
                """
                cur.execute(query)
                return cur.fetchall()

    def get_recent_stats(self) -> Dict[str, Any]:
        """최근 통계 정보"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 총 기사 수
                cur.execute("SELECT COUNT(*) as total FROM news_articles WHERE status = 'active'")
                total_articles = cur.fetchone()["total"]

                # 오늘 기사 수
                today = datetime.now().date()
                cur.execute(
                    "SELECT COUNT(*) as today FROM news_articles WHERE DATE(scraped_at) = %s AND status = 'active'",
                    [today],
                )
                today_articles = cur.fetchone()["today"]

                # 총 분석 수
                cur.execute("SELECT COUNT(*) as total FROM stock_analysis_results")
                total_analyses = cur.fetchone()["total"]

                # 진행 중인 거래
                cur.execute(
                    "SELECT COUNT(*) as active FROM stock_holdings WHERE status = 'bought'"
                )
                active_trades = cur.fetchone()["active"]

                return {
                    "total_disclosures": total_articles,
                    "today_disclosures": today_articles,
                    "total_analyses": total_analyses,
                    "active_trades": active_trades,
                }
