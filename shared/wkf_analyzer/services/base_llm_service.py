"""
모든 LLM 서비스가 구현해야 하는 추상 베이스 클래스
"""
from abc import ABC, abstractmethod
from typing import List, Dict


class BaseLLMService(ABC):
    """LLM 서비스 추상 클래스"""

    @abstractmethod
    def get_model_name(self) -> str:
        """
        LLM 모델명 반환 (고정값)

        Returns:
            'claude', 'gemini', 'openai' 중 하나
        """
        pass

    @abstractmethod
    def get_model_version(self) -> str:
        """
        실제 사용 중인 모델 버전 반환

        Returns:
            예: 'claude-sonnet-4-5-20250929', 'gemini-2.0-flash-exp', 'gpt-4-turbo-preview'
        """
        pass

    @abstractmethod
    def recommend_stocks(self, article_title: str, article_content: str) -> List[Dict]:
        """
        Phase 1: 뉴스 기사로부터 투자 종목 추천

        Args:
            article_title: 기사 제목
            article_content: 기사 본문

        Returns:
            [
                {
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "reasoning": "추천 근거"
                },
                ...
            ]
        """
        pass

    @abstractmethod
    def predict_price_increase(
        self,
        article_title: str,
        article_content: str,
        stock_code: str,
        stock_name: str,
        price_history: List[Dict],
        intraday_prices: List[Dict]
    ) -> Dict:
        """
        Phase 2: 뉴스와 주가 데이터를 종합하여 단기 주가 상승 확률 예측

        Args:
            article_title: 기사 제목
            article_content: 기사 본문
            stock_code: 종목코드
            stock_name: 종목명
            price_history: 직전 5일 일봉 데이터
            intraday_prices: 당일 분봉 데이터

        Returns:
            {
                "stock_code": "005930",
                "probability": 75,
                "reasoning": "예측 근거",
                "target_price": 85000,
                "stop_loss": 78000
            }
        """
        pass

    @abstractmethod
    def analyze_disclosure(
        self,
        corp_name: str,
        stock_code: str,
        report_name: str,
        rcept_date: str,
        price_history: List[Dict],
        intraday_prices: List[Dict]
    ) -> Dict:
        """
        공시 데이터와 주가 데이터를 종합하여 매수 여부 판단

        Args:
            corp_name: 회사명
            stock_code: 종목코드
            report_name: 공시 보고서명
            rcept_date: 접수일자 (YYYYMMDD)
            price_history: 직전 5일 일봉 데이터
            intraday_prices: 당일 분봉 데이터

        Returns:
            {
                "stock_code": "005930",
                "probability": 80,
                "reasoning": "분석 근거",
                "target_price": 85000,
                "stop_loss": 78000
            }
        """
        pass
