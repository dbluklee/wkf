-- 자동 매매 거래 기록 테이블 생성
-- stock_trades: 실제 매수/매도 거래 기록

CREATE TABLE IF NOT EXISTS stock_trades (
    id SERIAL PRIMARY KEY,
    holding_id INTEGER NOT NULL REFERENCES stock_holdings(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    llm_model VARCHAR(50) NOT NULL,

    -- 거래 정보
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price INTEGER NOT NULL CHECK (price > 0),
    total_amount BIGINT NOT NULL,

    -- KIS API 주문 정보
    kis_order_id VARCHAR(100),
    trade_status VARCHAR(20) DEFAULT 'pending',  -- pending, submitted, filled, failed

    -- 시간 정보
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_trades_holding ON stock_trades(holding_id);
CREATE INDEX IF NOT EXISTS idx_trades_llm ON stock_trades(llm_model, trade_type);
CREATE INDEX IF NOT EXISTS idx_trades_status ON stock_trades(trade_status);
CREATE INDEX IF NOT EXISTS idx_trades_created ON stock_trades(created_at);

-- 코멘트 추가
COMMENT ON TABLE stock_trades IS '자동 매매 거래 기록 (매수/매도)';
COMMENT ON COLUMN stock_trades.trade_type IS '거래 유형: buy(매수), sell(매도)';
COMMENT ON COLUMN stock_trades.trade_status IS '거래 상태: pending(대기), submitted(주문전송), filled(체결완료), failed(실패)';
COMMENT ON COLUMN stock_trades.kis_order_id IS '한국투자증권 API 주문번호';
