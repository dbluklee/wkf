"""
Claude API 서비스 (BaseLLMService 구현)
"""

import anthropic
import json
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests.exceptions

from wkf_analyzer.services.base_llm_service import BaseLLMService
from wkf_analyzer.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeService(BaseLLMService):
    """Claude API 기반 주식 분석 서비스"""

    def __init__(self, settings):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-5-20250929"
        self.max_recommendations = settings.MAX_RECOMMENDATIONS_PER_ARTICLE

    def get_model_name(self) -> str:
        """LLM 모델명 반환"""
        return "claude"

    def get_model_version(self) -> str:
        """실제 사용 중인 모델 버전 반환"""
        return self.model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIError, requests.exceptions.RequestException))
    )
    def recommend_stocks(self, article_title: str, article_content: str) -> List[Dict]:
        """
        Phase 1: 뉴스 기사로부터 투자 종목 추천

        Args:
            article_title: 기사 제목
            article_content: 기사 본문

        Returns:
            추천 종목 리스트 [{"stock_code": "...", "stock_name": "...", "reasoning": "..."}]
        """
        system_prompt = f"""당신은 한국 증권 시장 전문 애널리스트입니다.
뉴스 기사를 분석하여 투자 가치가 있는 한국 상장 주식을 추천하세요.

출력 형식 (JSON):
{{
  "recommended_stocks": [
    {{
      "stock_code": "6자리 종목코드",
      "stock_name": "종목명",
      "reasoning": "추천 근거 (100자 이내)"
    }}
  ]
}}

규칙:
- 최대 {self.max_recommendations}개 종목까지 추천
- 종목코드는 정확한 6자리 숫자 (예: 005930은 삼성전자)
- 추천 근거는 간결하고 명확하게 작성
- 기사와 관련성이 낮으면 빈 배열 반환
- 반드시 JSON 형식으로만 응답"""

        user_prompt = f"""다음 뉴스 기사를 분석하여 투자 종목을 추천하세요.

제목: {article_title}

내용:
{article_content}"""

        try:
            logger.info(f"[Claude] Requesting stock recommendations for: {article_title[:50]}...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # JSON 파싱
            response_text = response.content[0].text.strip()

            # JSON 코드 블록 제거 (있다면)
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())
            recommendations = result.get('recommended_stocks', [])

            logger.info(f"[Claude] Recommended {len(recommendations)} stocks")
            return recommendations

        except json.JSONDecodeError as e:
            logger.error(f"[Claude] Failed to parse response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"[Claude] API error in recommend_stocks: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIError, requests.exceptions.RequestException))
    )
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
            {"probability": int, "reasoning": str, "target_price": int, "stop_loss": int}
        """
        system_prompt = """당신은 한국 증권 시장 전문 애널리스트입니다.
뉴스와 주가 데이터를 종합 분석하여 단기(1-3일) 주가 상승 확률을 예측하세요.

출력 형식 (JSON):
{
  "stock_code": "종목코드",
  "probability": 0-100 정수,
  "reasoning": "예측 근거 (200자 이내)",
  "target_price": 목표가(정수),
  "stop_loss": 손절가(정수)
}

규칙:
- probability는 보수적으로 산정 (과도한 낙관은 지양)
- reasoning은 뉴스의 영향과 차트 패턴 모두 언급
- target_price는 최근 종가 대비 3-7% 범위 권장
- stop_loss는 최근 종가 대비 -3% 정도 권장
- 반드시 JSON 형식으로만 응답"""

        # 주가 데이터 포맷팅
        price_summary = self._format_price_data(price_history, intraday_prices)

        user_prompt = f"""뉴스: {article_title}

{article_content}

주가 데이터:
{price_summary}

이 정보를 바탕으로 {stock_name}({stock_code})의 단기 상승 확률을 예측하세요."""

        try:
            logger.info(f"[Claude] Requesting price prediction for {stock_name}({stock_code})")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # JSON 파싱
            response_text = response.content[0].text.strip()

            # JSON 코드 블록 제거 (있다면)
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())

            logger.info(f"[Claude] Predicted {result.get('probability')}% for {stock_name}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[Claude] Failed to parse response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise
        except Exception as e:
            logger.error(f"[Claude] API error in predict_price_increase: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIError, requests.exceptions.RequestException))
    )
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
            {"stock_code": str, "probability": int, "reasoning": str, "target_price": int, "stop_loss": int}
        """
        system_prompt = """당신은 한국 증권 시장 전문 애널리스트입니다.
기업 공시와 주가 데이터를 종합 분석하여 단기(1-3일) 주가 상승 확률을 예측하고 매수 여부를 판단하세요.

출력 형식 (JSON):
{
  "stock_code": "종목코드",
  "probability": 0-100 정수,
  "reasoning": "분석 근거 (200자 이내)",
  "target_price": 목표가(정수),
  "stop_loss": 손절가(정수)
}

규칙:
- probability는 보수적으로 산정 (과도한 낙관은 지양)
- reasoning은 공시의 의미와 주가 영향을 모두 언급
- 장중 주가 흐름(분봉 데이터)을 분석하여 공시 직전 주가 방향성과 거래량 변화를 고려
- 공시 전 주가가 급등했다면 이미 반영되었을 가능성 고려
- 공시 전 거래량이 급증했다면 정보 유출 또는 기대감 반영 가능성 고려
- target_price는 최근 종가 대비 3-7% 범위 권장
- stop_loss는 최근 종가 대비 -3% 정도 권장
- 공시가 주가에 부정적이거나 중립적이면 낮은 확률(30% 이하) 부여
- 반드시 JSON 형식으로만 응답"""

        # 주가 데이터 포맷팅
        price_summary = self._format_price_data(price_history, intraday_prices)

        # 접수일자 포맷팅 (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = f"{rcept_date[:4]}-{rcept_date[4:6]}-{rcept_date[6:8]}"

        user_prompt = f"""공시 정보:
- 회사명: {corp_name}
- 종목코드: {stock_code}
- 공시명: {report_name}
- 공시일자: {formatted_date}

주가 데이터:
{price_summary}

이 공시가 {corp_name}({stock_code})의 주가에 미치는 영향을 분석하고 매수 여부를 판단하세요."""

        try:
            logger.info(f"[Claude] Analyzing disclosure for {corp_name}({stock_code}): {report_name}")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # JSON 파싱
            response_text = response.content[0].text.strip()

            # JSON 코드 블록 제거
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())

            logger.info(f"[Claude] Disclosure analysis: {result.get('probability')}% for {corp_name}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[Claude] Failed to parse disclosure analysis response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise
        except Exception as e:
            logger.error(f"[Claude] API error in analyze_disclosure: {e}")
            raise

    def _format_price_data(self, price_history: List[Dict], intraday_prices: List[Dict]) -> str:
        """
        주가 데이터를 Claude가 읽기 쉬운 포맷으로 변환

        Args:
            price_history: 일봉 데이터
            intraday_prices: 분봉 데이터

        Returns:
            포맷된 문자열
        """
        lines = []

        # 직전 5일 일봉
        if price_history:
            lines.append("직전 5영업일 일봉:")
            for price in price_history:
                date = price.get('stck_bsop_date', '')
                open_p = int(price.get('stck_oprc', 0))
                high = int(price.get('stck_hgpr', 0))
                low = int(price.get('stck_lwpr', 0))
                close = int(price.get('stck_clpr', 0))
                volume = int(price.get('acml_vol', 0))

                lines.append(f"  {date}: 시가 {open_p:,}원, 고가 {high:,}원, 저가 {low:,}원, 종가 {close:,}원, 거래량 {volume:,}주")
        else:
            lines.append("직전 5영업일 일봉: 데이터 없음")

        lines.append("")

        # 당일 분봉 - 장중 주가 흐름 상세 분석
        if intraday_prices:
            total_count = len(intraday_prices)

            # 분봉 데이터가 있으면 요약 통계 먼저 표시
            if total_count > 0:
                first_price = int(intraday_prices[-1].get('stck_prpr', 0))  # 가장 오래된 데이터 (장 시작)
                latest_price = int(intraday_prices[0].get('stck_prpr', 0))  # 가장 최근 데이터

                # 최고가/최저가 계산
                all_prices = [int(p.get('stck_prpr', 0)) for p in intraday_prices]
                high_price = max(all_prices)
                low_price = min(all_prices)

                # 변화율 계산
                change_rate = ((latest_price - first_price) / first_price * 100) if first_price > 0 else 0

                lines.append(f"금일 장중 주가 흐름 (총 {total_count}개 분봉):")
                lines.append(f"  장 시작 가격: {first_price:,}원")
                lines.append(f"  현재 가격: {latest_price:,}원 ({change_rate:+.2f}%)")
                lines.append(f"  장중 최고가: {high_price:,}원")
                lines.append(f"  장중 최저가: {low_price:,}원")
                lines.append("")

                # 최근 30개 분봉 상세 데이터 (공시 직전 주가 움직임 파악용)
                display_count = min(30, total_count)
                lines.append(f"  최근 {display_count}개 분봉 상세:")
                for price in intraday_prices[:display_count]:
                    time_str = price.get('stck_cntg_hour', '000000')
                    time_formatted = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
                    current_price = int(price.get('stck_prpr', 0))
                    volume = int(price.get('cntg_vol', 0))

                    lines.append(f"    {time_formatted}: {current_price:,}원, 거래량 {volume:,}주")
        else:
            lines.append("금일 분봉: 데이터 없음 (장 시간 외이거나 데이터 수집 실패)")

        return "\n".join(lines)
