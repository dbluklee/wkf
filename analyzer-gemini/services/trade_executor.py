"""
자동 매매 실행 및 모니터링 서비스

백그라운드 스레드로 실행되며:
1. pending holdings를 조회하여 매수
2. bought holdings의 현재가를 체크하여 목표가/손절가 도달 시 매도
"""
import threading
import time
from datetime import datetime, time as time_type
from typing import List, Dict
from utils.logger import get_logger

logger = get_logger(__name__)


class TradeExecutor:
    """자동 매매 실행 서비스"""

    def __init__(self, settings, kis_service, repositories, telegram_service=None):
        """
        Args:
            settings: 설정 객체
            kis_service: KISService 인스턴스
            repositories: Repository 모음
            telegram_service: TelegramService 인스턴스
        """
        self.settings = settings
        self.kis = kis_service
        self.repos = repositories
        self.telegram = telegram_service
        self.is_running = False
        self.monitor_thread = None

    def start_monitoring(self):
        """백그라운드 모니터링 시작"""
        if self.is_running:
            logger.warning("TradeExecutor already running")
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🤖 TradeExecutor monitoring started")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("TradeExecutor monitoring stopped")

    def _monitor_loop(self):
        """메인 모니터링 루프"""
        logger.info(f"TradeExecutor loop started (interval: {self.settings.TRADE_MONITORING_INTERVAL_SECONDS}s)")
        logger.info("Force sell time: 15:20 (all positions closed)")

        while self.is_running:
            try:
                # 장 시간 확인
                if not self._is_market_open():
                    logger.debug("Market closed, skipping trade monitoring")
                    time.sleep(self.settings.TRADE_MONITORING_INTERVAL_SECONDS)
                    continue

                # 15:20 강제 매도 체크
                now = datetime.now()
                current_time = now.time()
                force_sell_time = time_type(15, 20)

                if current_time >= force_sell_time:
                    logger.info("⏰ Force sell time (15:20) reached - selling all positions")
                    self._force_sell_all_holdings()
                    logger.info("📴 Trading and monitoring stopped until next trading day")
                    # 15:20 이후에는 모니터링도 중지 - 다음날까지 대기
                    time.sleep(3600)  # 1시간마다 체크 (다음날 아침까지 대기)
                    continue

                # 1. 매수 처리
                self._process_pending_buys()

                # 2. 매도 모니터링
                self._monitor_bought_holdings()

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            # 대기
            time.sleep(self.settings.TRADE_MONITORING_INTERVAL_SECONDS)

        logger.info("TradeExecutor monitor loop stopped")

    def _is_market_open(self) -> bool:
        """장 시간 확인 (09:00~15:30, 평일만)"""
        now = datetime.now()

        # 평일(월~금)이 아니면 False
        if now.weekday() >= 5:  # 5=토요일, 6=일요일
            return False

        current_time = now.time()
        market_open = time_type(self.settings.MARKET_OPEN_HOUR, self.settings.MARKET_OPEN_MINUTE)
        market_close = time_type(self.settings.MARKET_CLOSE_HOUR, self.settings.MARKET_CLOSE_MINUTE)

        return market_open <= current_time <= market_close

    def _process_pending_buys(self):
        """pending 상태의 holdings를 조회하여 매수 주문"""
        pending_holdings = self.repos.holdings_repo.get_pending_holdings()

        if not pending_holdings:
            logger.debug("No pending holdings to buy")
            return

        logger.info(f"Found {len(pending_holdings)} pending holdings")

        for holding in pending_holdings:
            try:
                self._execute_buy(holding)
            except Exception as e:
                logger.error(f"Failed to execute buy for holding {holding['id']}: {e}")

    def _execute_buy(self, holding: Dict):
        """매수 실행"""
        holding_id = holding['id']
        stock_code = holding['stock_code']
        stock_name = holding['stock_name']

        logger.info(f"💰 Buying {stock_name}({stock_code})...")

        try:
            # 1. status를 'buying'으로 변경
            self.repos.holdings_repo.update_holding_status(holding_id, 'buying')

            # 2. 매수 수량 계산
            quantity = self._calculate_buy_quantity(stock_code)

            if quantity == 0:
                logger.warning(f"Cannot buy {stock_code}: calculated quantity is 0")
                self.repos.holdings_repo.update_holding_status(holding_id, 'pending')
                return

            # 3. KIS API로 매수 주문
            order_result = self.kis.buy_stock(stock_code, quantity)

            # 4. 체결가 조회 (간단화: 현재가 사용)
            current_price = self.kis.fetch_current_price(stock_code)

            # 5. holdings 업데이트
            self.repos.holdings_repo.update_holding_after_buy(
                holding_id,
                quantity,
                current_price
            )

            logger.info(
                f"✅ Buy completed: {stock_name}({stock_code}) "
                f"x {quantity} @ {current_price:,}원 (total: {current_price * quantity:,}원)"
            )

            # 텔레그램 알림
            if self.telegram:
                self.telegram.notify_buy_order(stock_code, stock_name, quantity, current_price)

        except Exception as e:
            logger.error(f"Buy failed for {stock_code}: {e}")
            # status를 다시 pending으로 되돌림 (재시도 가능)
            self.repos.holdings_repo.update_holding_status(holding_id, 'pending')
            raise

    def _calculate_buy_quantity(self, stock_code: str) -> int:
        """
        매수 수량 계산

        Args:
            stock_code: 종목코드

        Returns:
            매수 수량 (주)
        """
        try:
            # 현재가 조회
            current_price = self.kis.fetch_current_price(stock_code)

            if current_price == 0:
                logger.warning(f"Current price for {stock_code} is 0")
                return 0

            # 설정된 매수 금액으로 수량 계산
            quantity = self.settings.TRADE_AMOUNT_PER_STOCK // current_price

            logger.debug(
                f"Calculated buy quantity for {stock_code}: "
                f"{quantity} shares (price: {current_price:,}원, budget: {self.settings.TRADE_AMOUNT_PER_STOCK:,}원)"
            )

            return max(1, quantity)  # 최소 1주

        except Exception as e:
            logger.error(f"Failed to calculate buy quantity for {stock_code}: {e}")
            return 0

    def _monitor_bought_holdings(self):
        """bought 상태의 holdings를 모니터링하여 매도 조건 확인"""
        bought_holdings = self.repos.holdings_repo.get_bought_holdings()

        if not bought_holdings:
            logger.debug("No bought holdings to monitor")
            return

        logger.info(f"Monitoring {len(bought_holdings)} bought holdings")

        for holding in bought_holdings:
            try:
                self._check_sell_conditions(holding)
            except Exception as e:
                logger.error(f"Failed to check sell conditions for holding {holding['id']}: {e}")

    def _check_sell_conditions(self, holding: Dict):
        """매도 조건 확인 및 실행"""
        holding_id = holding['id']
        stock_code = holding['stock_code']
        stock_name = holding['stock_name']
        quantity = holding['quantity']
        average_price = holding['average_price']

        try:
            # 현재가 조회
            current_price = self.kis.fetch_current_price(stock_code)

            # 수익률 계산
            profit_rate = ((current_price - average_price) / average_price) * 100

            logger.debug(
                f"{stock_name}({stock_code}): "
                f"buy={average_price:,}원, now={current_price:,}원, "
                f"profit={profit_rate:+.2f}%"
            )

            # 매도 조건 체크
            should_sell = False
            sell_reason = ""

            # 목표 수익률 도달
            if profit_rate >= self.settings.PROFIT_TARGET_PERCENT:
                should_sell = True
                sell_reason = f"목표 수익률 도달 ({profit_rate:+.2f}% >= {self.settings.PROFIT_TARGET_PERCENT}%)"

            # 손절률 도달 (음수 비교)
            elif profit_rate <= -self.settings.STOP_LOSS_PERCENT:
                should_sell = True
                sell_reason = f"손절률 도달 ({profit_rate:+.2f}% <= -{self.settings.STOP_LOSS_PERCENT}%)"

            if should_sell:
                logger.info(f"📊 Sell signal: {stock_name}({stock_code}) - {sell_reason}")
                self._execute_sell(holding, current_price, sell_reason)

        except Exception as e:
            logger.error(f"Failed to check sell conditions for {stock_code}: {e}")
            raise

    def _execute_sell(self, holding: Dict, current_price: int, reason: str):
        """매도 실행"""
        holding_id = holding['id']
        stock_code = holding['stock_code']
        stock_name = holding['stock_name']
        quantity = holding['quantity']
        average_price = holding['average_price']

        logger.info(f"💸 Selling {stock_name}({stock_code})... ({reason})")

        try:
            # 1. status를 'selling'으로 변경
            self.repos.holdings_repo.update_holding_status(holding_id, 'selling')

            # 2. KIS API로 매도 주문
            order_result = self.kis.sell_stock(stock_code, quantity)

            # 3. holdings status를 'sold'로 변경
            self.repos.holdings_repo.update_holding_after_sell(holding_id)

            # 4. 수익 계산
            profit_amount = (current_price - average_price) * quantity
            profit_rate = ((current_price - average_price) / average_price) * 100

            logger.info(
                f"✅ Sell completed: {stock_name}({stock_code}) "
                f"x {quantity} @ {current_price:,}원\n"
                f"   Buy: {average_price:,}원 → Sell: {current_price:,}원\n"
                f"   Profit: {profit_amount:+,}원 ({profit_rate:+.2f}%)\n"
                f"   Reason: {reason}"
            )

            # 텔레그램 알림
            if self.telegram:
                self.telegram.notify_sell_order(
                    stock_code,
                    stock_name,
                    quantity,
                    average_price,
                    current_price,
                    profit_amount,
                    profit_rate,
                    reason
                )

        except Exception as e:
            logger.error(f"Sell failed for {stock_code}: {e}")
            # status를 다시 bought로 되돌림 (재시도 가능)
            self.repos.holdings_repo.update_holding_status(holding_id, 'bought')
            raise

    def _force_sell_all_holdings(self):
        """15:20 강제 매도 - 모든 bought holdings를 수익률 무관하게 매도"""
        bought_holdings = self.repos.holdings_repo.get_bought_holdings()

        if not bought_holdings:
            logger.info("No bought holdings to force sell")
            return

        logger.info(f"🚨 Force selling {len(bought_holdings)} holdings at 15:20")

        for holding in bought_holdings:
            try:
                stock_code = holding['stock_code']
                stock_name = holding['stock_name']

                # 현재가 조회
                current_price = self.kis.fetch_current_price(stock_code)

                # 강제 매도 실행
                self._execute_sell(holding, current_price, "강제 매도 (15:20)")

            except Exception as e:
                logger.error(f"Failed to force sell {holding['stock_code']}: {e}")

        logger.info("✅ Force sell completed for all holdings")
