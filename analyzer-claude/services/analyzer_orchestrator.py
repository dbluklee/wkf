"""
분석 워크플로우 오케스트레이터
"""

import time
from typing import Dict

from config.settings import AnalyzerSettings
from services.claude_service import ClaudeService
from services.kis_service import KISService
from services.telegram_service import TelegramService
from database.repositories import Repositories
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalyzerOrchestrator:
    """전체 분석 워크플로우를 조율하는 오케스트레이터"""

    def __init__(
        self,
        settings: AnalyzerSettings,
        claude_service: ClaudeService,
        kis_service: KISService,
        repositories: Repositories,
        telegram_service: TelegramService = None
    ):
        self.settings = settings
        self.claude = claude_service
        self.kis = kis_service
        self.repos = repositories
        self.telegram = telegram_service

    def analyze_article(self, article_id: int):
        """
        새 기사에 대한 전체 분석 워크플로우 실행

        Args:
            article_id: 분석할 기사 ID

        워크플로우:
            1. 기사 조회
            2. Claude Phase 1: 종목 추천
            3. 추천 종목별로:
               - KIS API: 주가 데이터 조회
               - Claude Phase 2: 상승 확률 예측
               - threshold 이상이면 holdings에 추가
            4. 로그 기록
        """
        start_time = time.time()

        try:
            # 1. 기사 조회
            article = self.repos.news_repo.get_article_by_id(article_id)
            if not article:
                logger.warning(f"Article {article_id} not found")
                return

            logger.info(f"Starting analysis for article {article_id}: {article.title[:50]}...")

            # 2. Phase 1: Claude에서 종목 추천
            try:
                recommendations = self.claude.recommend_stocks(
                    article.title,
                    article.content
                )
            except Exception as e:
                logger.error(f"Claude recommendation failed: {e}")
                self.repos.log_repo.log_analysis(
                    article_id, 'failed', 'recommendation',
                    str(e), time.time() - start_time
                )
                return

            if not recommendations:
                logger.info(f"No stocks recommended for article {article_id}")
                self.repos.log_repo.log_analysis(
                    article_id, 'success', 'recommendation',
                    'No recommendations', time.time() - start_time
                )
                return

            logger.info(f"Claude recommended {len(recommendations)} stocks")

            # 3. 각 추천 종목에 대해 분석
            success_count = 0
            for rec in recommendations:
                try:
                    if self._analyze_stock(article, rec):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to analyze {rec.get('stock_code', 'unknown')}: {e}")
                    continue

            # 4. 로그 기록
            execution_time = time.time() - start_time
            status = 'success' if success_count > 0 else 'partial'
            self.repos.log_repo.log_analysis(
                article_id, status, 'complete',
                None, execution_time
            )

            logger.info(
                f"Analysis completed for article {article_id} "
                f"({success_count}/{len(recommendations)} stocks analyzed) "
                f"in {execution_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Analysis failed for article {article_id}: {e}")
            self.repos.log_repo.log_analysis(
                article_id, 'failed', None,
                str(e), time.time() - start_time
            )

    def analyze_disclosure(self, disclosure_id: int):
        """
        새 공시에 대한 분석 워크플로우 실행

        Args:
            disclosure_id: 분석할 공시 ID

        워크플로우:
            1. 공시 조회
            2. 종목코드가 있으면:
               - KIS API: 주가 데이터 조회
               - Claude: 공시 분석 및 매수 여부 판단
               - threshold 이상이면 holdings에 추가
            3. 로그 기록
        """
        start_time = time.time()

        try:
            # 1. 공시 조회
            disclosure = self.repos.disclosure_repo.get_disclosure_by_id(disclosure_id)
            if not disclosure:
                logger.warning(f"Disclosure {disclosure_id} not found")
                return

            logger.info(f"Starting disclosure analysis for {disclosure.corp_name}: {disclosure.report_nm}")

            # 2. 종목코드 확인
            if not disclosure.stock_code:
                logger.info(f"Disclosure {disclosure_id} has no stock_code, skipping analysis")
                return

            stock_code = disclosure.stock_code
            corp_name = disclosure.corp_name

            # 3. KIS API로 주가 데이터 조회
            try:
                daily_prices = self.kis.fetch_daily_prices(
                    stock_code,
                    days=self.settings.STOCK_HISTORY_DAYS
                )
                intraday_prices = self.kis.fetch_intraday_prices(stock_code)

                logger.info(
                    f"Fetched prices for {stock_code}: "
                    f"{len(daily_prices)} daily, {len(intraday_prices)} intraday"
                )
            except Exception as e:
                logger.error(f"Failed to fetch prices for {stock_code}: {e}")
                self.repos.log_repo.log_analysis(
                    None, 'failed', 'price_fetch',
                    str(e), time.time() - start_time
                )
                return

            # 주가 데이터가 없으면 분석 불가
            if not daily_prices:
                logger.warning(f"No price data available for {stock_code}, skipping analysis")
                return

            # 4. 주가 데이터 저장
            self.repos.price_repo.save_prices(stock_code, daily_prices, 'daily')
            if intraday_prices:
                self.repos.price_repo.save_prices(stock_code, intraday_prices, 'intraday')

            # 5. Claude로 공시 분석
            try:
                analysis = self.claude.analyze_disclosure(
                    corp_name,
                    stock_code,
                    disclosure.report_nm,
                    disclosure.rcept_dt,
                    daily_prices,
                    intraday_prices
                )
            except Exception as e:
                logger.error(f"Claude disclosure analysis failed for {stock_code}: {e}")
                self.repos.log_repo.log_analysis(
                    None, 'failed', 'analysis',
                    str(e), time.time() - start_time
                )
                return

            probability = analysis.get('probability', 0)
            reasoning = analysis.get('reasoning', '')
            target_price = analysis.get('target_price')
            stop_loss = analysis.get('stop_loss')

            logger.info(
                f"Disclosure analysis for {corp_name}({stock_code}): "
                f"{probability}% probability"
            )

            # 6. 분석 결과 저장 (disclosure는 recommendation 과정이 없으므로 직접 analysis에 저장)
            # 편의상 disclosure_id를 article_id 자리에 사용 (또는 별도 테이블 생성 가능)
            # 여기서는 간단히 article_id를 NULL로, recommendation_id도 생성

            # 먼저 더미 recommendation 생성 (공시 기반)
            rec_id = self.repos.recommendation_repo.save_recommendation(
                disclosure_id,  # article_id 대신 disclosure_id 사용
                stock_code,
                corp_name,
                f"공시: {disclosure.report_nm}",
                llm_model=self.claude.get_model_name(),
                llm_version=self.claude.get_model_version()
            )

            analysis_id = self.repos.analysis_repo.save_analysis(
                disclosure_id,  # article_id 대신 disclosure_id 사용
                rec_id,
                stock_code,
                probability,
                reasoning,
                target_price,
                stop_loss,
                llm_model=self.claude.get_model_name(),
                llm_version=self.claude.get_model_version()
            )

            # 7. threshold 이상이면 holdings에 추가
            will_buy = probability >= self.settings.ANALYSIS_THRESHOLD_PERCENT

            if will_buy:
                self.repos.holdings_repo.add_holding(
                    analysis_id,
                    stock_code,
                    corp_name,
                    target_price,
                    stop_loss,
                    llm_model=self.claude.get_model_name(),
                    llm_version=self.claude.get_model_version()
                )
                logger.info(
                    f"✓ Added {corp_name}({stock_code}) to holdings based on disclosure "
                    f"(probability: {probability}%)"
                )
            else:
                logger.info(
                    f"✗ {corp_name}({stock_code}) below threshold "
                    f"({probability}% < {self.settings.ANALYSIS_THRESHOLD_PERCENT}%)"
                )

            # 텔레그램 알림 - 분석 결과 (threshold 무관)
            if self.telegram:
                self.telegram.notify_analysis_result(
                    stock_code,
                    corp_name,
                    probability,
                    reasoning,
                    will_buy
                )

            # 8. 로그 기록
            execution_time = time.time() - start_time
            self.repos.log_repo.log_analysis(
                disclosure_id, 'success', 'complete',
                None, execution_time
            )

            logger.info(
                f"Disclosure analysis completed for {corp_name}({stock_code}) "
                f"in {execution_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Disclosure analysis failed for disclosure {disclosure_id}: {e}")
            self.repos.log_repo.log_analysis(
                disclosure_id, 'failed', None,
                str(e), time.time() - start_time
            )

    def _analyze_stock(self, article, recommendation: Dict) -> bool:
        """
        개별 종목 분석

        Args:
            article: NewsArticle 객체
            recommendation: 추천 정보 dict

        Returns:
            성공 여부
        """
        stock_code = recommendation.get('stock_code')
        stock_name = recommendation.get('stock_name')
        reasoning = recommendation.get('reasoning', '')

        logger.info(f"Analyzing {stock_name}({stock_code})...")

        try:
            # 1. 추천 저장
            rec_id = self.repos.recommendation_repo.save_recommendation(
                article.id, stock_code, stock_name, reasoning,
                llm_model=self.claude.get_model_name(),
                llm_version=self.claude.get_model_version()
            )

            # 2. KIS API로 주가 데이터 조회
            try:
                daily_prices = self.kis.fetch_daily_prices(
                    stock_code,
                    days=self.settings.STOCK_HISTORY_DAYS
                )
                intraday_prices = self.kis.fetch_intraday_prices(stock_code)

                logger.info(
                    f"Fetched prices for {stock_code}: "
                    f"{len(daily_prices)} daily, {len(intraday_prices)} intraday"
                )
            except Exception as e:
                logger.error(f"Failed to fetch prices for {stock_code}: {e}")
                # 주가 조회 실패 시 분석 중단
                return False

            # 주가 데이터가 없으면 분석 불가
            if not daily_prices:
                logger.warning(f"No price data available for {stock_code}, skipping analysis")
                return False

            # 3. 주가 데이터 저장
            self.repos.price_repo.save_prices(stock_code, daily_prices, 'daily')
            if intraday_prices:
                self.repos.price_repo.save_prices(stock_code, intraday_prices, 'intraday')

            # 4. Phase 2: Claude로 상승 확률 예측
            try:
                prediction = self.claude.predict_price_increase(
                    article.title,
                    article.content,
                    stock_code,
                    stock_name,
                    daily_prices,
                    intraday_prices
                )
            except Exception as e:
                logger.error(f"Claude prediction failed for {stock_code}: {e}")
                return False

            probability = prediction.get('probability', 0)
            pred_reasoning = prediction.get('reasoning', '')
            target_price = prediction.get('target_price')
            stop_loss = prediction.get('stop_loss')

            logger.info(
                f"Prediction for {stock_name}({stock_code}): "
                f"{probability}% probability"
            )

            # 5. 분석 결과 저장
            analysis_id = self.repos.analysis_repo.save_analysis(
                article.id,
                rec_id,
                stock_code,
                probability,
                pred_reasoning,
                target_price,
                stop_loss,
                llm_model=self.claude.get_model_name(),
                llm_version=self.claude.get_model_version()
            )

            # 6. threshold 이상이면 holdings에 추가
            will_buy = probability >= self.settings.ANALYSIS_THRESHOLD_PERCENT

            if will_buy:
                self.repos.holdings_repo.add_holding(
                    analysis_id,
                    stock_code,
                    stock_name,
                    target_price,
                    stop_loss,
                    llm_model=self.claude.get_model_name(),
                    llm_version=self.claude.get_model_version()
                )
                logger.info(
                    f"✓ Added {stock_name}({stock_code}) to holdings "
                    f"(probability: {probability}%)"
                )
            else:
                logger.info(
                    f"✗ {stock_name}({stock_code}) below threshold "
                    f"({probability}% < {self.settings.ANALYSIS_THRESHOLD_PERCENT}%)"
                )

            # 텔레그램 알림 - 분석 결과 (threshold 무관)
            if self.telegram:
                self.telegram.notify_analysis_result(
                    stock_code,
                    stock_name,
                    probability,
                    pred_reasoning,
                    will_buy
                )

            return True

        except Exception as e:
            logger.error(f"Error analyzing {stock_code}: {e}")
            return False
