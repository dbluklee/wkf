"""
텔레그램 알림 서비스
"""
import requests
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class TelegramService:
    """텔레그램 봇 알림 서비스"""

    def __init__(self, bot_token: str, chat_id: str, llm_name: str = ""):
        """
        Args:
            bot_token: 텔레그램 봇 토큰
            chat_id: 텔레그램 채팅방 ID
            llm_name: LLM 이름 (claude, gemini, openai)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.llm_name = llm_name
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token and chat_id)

        if not self.enabled:
            logger.warning("Telegram service is disabled (missing bot_token or chat_id)")
        else:
            logger.info(f"Telegram service initialized for {llm_name}")

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        텔레그램 메시지 전송

        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드 (Markdown, HTML)

        Returns:
            성공 여부
        """
        if not self.enabled:
            logger.debug(f"Telegram disabled, skipping message: {message[:50]}...")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.debug(f"Telegram message sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def notify_service_start(self):
        """서비스 시작 알림"""
        message = f"""
🚀 *{self.llm_name.upper()} Analyzer 시작*

장 시작 - 자동 매매 시스템 가동
• 공시 모니터링 시작
• 자동 매매 준비 완료
"""
        self.send_message(message.strip())

    def notify_service_stop(self):
        """서비스 종료 알림"""
        message = f"""
🛑 *{self.llm_name.upper()} Analyzer 종료*

서비스가 정상적으로 종료되었습니다.
"""
        self.send_message(message.strip())

    def notify_holding_added(self, stock_code: str, stock_name: str, probability: int, reasoning: str):
        """
        Holdings 추가 알림

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            probability: 상승 확률 (%)
            reasoning: 추천 이유
        """
        message = f"""
📊 *{self.llm_name.upper()}: 새 종목 추가*

*{stock_name}* ({stock_code})
• 상승 확률: *{probability}%*
• 이유: {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}

매수 대기 중...
"""
        self.send_message(message.strip())

    def notify_buy_order(self, stock_code: str, stock_name: str, quantity: int, price: int):
        """
        매수 주문 알림

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 매수가
        """
        total = quantity * price
        message = f"""
💰 *{self.llm_name.upper()}: 매수 체결*

*{stock_name}* ({stock_code})
• 수량: {quantity:,}주
• 가격: {price:,}원
• 총액: {total:,}원
"""
        self.send_message(message.strip())

    def notify_sell_order(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        buy_price: int,
        sell_price: int,
        profit_loss: int,
        profit_rate: float,
        reason: str
    ):
        """
        매도 주문 알림

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            buy_price: 매수가
            sell_price: 매도가
            profit_loss: 손익 (원)
            profit_rate: 수익률 (%)
            reason: 매도 이유
        """
        profit_emoji = "📈" if profit_loss > 0 else "📉" if profit_loss < 0 else "➖"
        profit_sign = "+" if profit_loss > 0 else ""

        message = f"""
{profit_emoji} *{self.llm_name.upper()}: 매도 체결*

*{stock_name}* ({stock_code})
• 수량: {quantity:,}주
• 매수가: {buy_price:,}원
• 매도가: {sell_price:,}원
• 손익: *{profit_sign}{profit_loss:,}원* ({profit_sign}{profit_rate:.2f}%)
• 사유: {reason}
"""
        self.send_message(message.strip())

    def notify_force_sell(self, total_holdings: int):
        """
        15:20 강제 매도 알림

        Args:
            total_holdings: 강제 매도할 종목 수
        """
        message = f"""
⏰ *{self.llm_name.upper()}: 장 마감 강제 매도*

15:20 도달 - {total_holdings}개 종목 강제 매도 중...
"""
        self.send_message(message.strip())

    def notify_error(self, error_type: str, error_message: str):
        """
        에러 알림

        Args:
            error_type: 에러 타입
            error_message: 에러 메시지
        """
        message = f"""
⚠️ *{self.llm_name.upper()}: 에러 발생*

• 타입: {error_type}
• 메시지: {error_message[:200]}
"""
        self.send_message(message.strip())
