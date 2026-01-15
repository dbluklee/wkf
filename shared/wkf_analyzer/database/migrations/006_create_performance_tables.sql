-- LLM 성과 추적 테이블 생성
-- llm_performance_tracking: 각 매매 건별 성과 기록
-- llm_daily_stats: 일별 집계 통계
-- llm_weekly_stats: 주별 집계 통계
-- llm_monthly_stats: 월별 집계 통계

-- 1. 매매 건별 성과 추적 테이블
CREATE TABLE IF NOT EXISTS llm_performance_tracking (
    id SERIAL PRIMARY KEY,
    llm_model VARCHAR(50) NOT NULL,
    holding_id INTEGER NOT NULL REFERENCES stock_holdings(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,

    -- 매수 정보
    buy_price INTEGER NOT NULL,
    buy_quantity INTEGER NOT NULL,
    buy_date TIMESTAMP NOT NULL,

    -- 매도 정보
    sell_price INTEGER,
    sell_quantity INTEGER,
    sell_date TIMESTAMP,

    -- 수익률 계산
    profit_loss BIGINT,                  -- 실현 손익 (원)
    roi_percent FLOAT,                   -- 수익률 (%)
    holding_days INTEGER,                -- 보유 기간 (일)

    -- 분석 정보
    predicted_probability INTEGER,       -- 원래 예측 확률
    target_price INTEGER,
    stop_loss INTEGER,
    sell_reason VARCHAR(50),             -- 'target', 'stop_loss', 'manual'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_performance_llm ON llm_performance_tracking(llm_model);
CREATE INDEX IF NOT EXISTS idx_performance_dates ON llm_performance_tracking(buy_date, sell_date);
CREATE INDEX IF NOT EXISTS idx_performance_roi ON llm_performance_tracking(roi_percent);

-- 2. 일별 통계 테이블
CREATE TABLE IF NOT EXISTS llm_daily_stats (
    id SERIAL PRIMARY KEY,
    llm_model VARCHAR(50) NOT NULL,
    stat_date DATE NOT NULL,

    -- 거래 통계
    total_trades INTEGER DEFAULT 0,      -- 총 거래 수 (매도 기준)
    winning_trades INTEGER DEFAULT 0,    -- 수익 거래 수
    losing_trades INTEGER DEFAULT 0,     -- 손실 거래 수

    -- 수익률 통계
    total_profit_loss BIGINT DEFAULT 0,  -- 총 손익 (원)
    average_roi FLOAT,                   -- 평균 수익률 (%)
    win_rate FLOAT,                      -- 승률 (%)

    -- 추가 메트릭
    total_invested BIGINT DEFAULT 0,     -- 총 투자금
    total_returned BIGINT DEFAULT 0,     -- 총 회수금
    avg_holding_days FLOAT,              -- 평균 보유 기간

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(llm_model, stat_date)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_daily_stats_model ON llm_daily_stats(llm_model, stat_date);

-- 3. 주별 통계 테이블
CREATE TABLE IF NOT EXISTS llm_weekly_stats (
    id SERIAL PRIMARY KEY,
    llm_model VARCHAR(50) NOT NULL,
    stat_date DATE NOT NULL,             -- 해당 주의 월요일

    -- 거래 통계
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,

    -- 수익률 통계
    total_profit_loss BIGINT DEFAULT 0,
    average_roi FLOAT,
    win_rate FLOAT,

    -- 추가 메트릭
    total_invested BIGINT DEFAULT 0,
    total_returned BIGINT DEFAULT 0,
    avg_holding_days FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(llm_model, stat_date)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_weekly_stats_model ON llm_weekly_stats(llm_model, stat_date);

-- 4. 월별 통계 테이블
CREATE TABLE IF NOT EXISTS llm_monthly_stats (
    id SERIAL PRIMARY KEY,
    llm_model VARCHAR(50) NOT NULL,
    stat_date DATE NOT NULL,             -- 해당 월의 1일

    -- 거래 통계
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,

    -- 수익률 통계
    total_profit_loss BIGINT DEFAULT 0,
    average_roi FLOAT,
    win_rate FLOAT,

    -- 추가 메트릭
    total_invested BIGINT DEFAULT 0,
    total_returned BIGINT DEFAULT 0,
    avg_holding_days FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(llm_model, stat_date)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_monthly_stats_model ON llm_monthly_stats(llm_model, stat_date);

-- 코멘트 추가
COMMENT ON TABLE llm_performance_tracking IS 'LLM별 매매 건별 성과 추적';
COMMENT ON TABLE llm_daily_stats IS 'LLM별 일별 집계 통계';
COMMENT ON TABLE llm_weekly_stats IS 'LLM별 주별 집계 통계';
COMMENT ON TABLE llm_monthly_stats IS 'LLM별 월별 집계 통계';

COMMENT ON COLUMN llm_performance_tracking.sell_reason IS '매도 사유: target(목표가), stop_loss(손절가), manual(수동)';
