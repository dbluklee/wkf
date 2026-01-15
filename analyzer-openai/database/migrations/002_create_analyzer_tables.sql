-- 주식 분석 관련 테이블 생성

-- stock_recommendations 테이블: Claude Phase 1 종목 추천 결과
CREATE TABLE IF NOT EXISTS stock_recommendations (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES news_articles(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    reasoning TEXT,
    recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, stock_code)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_stock_rec_article ON stock_recommendations(article_id);
CREATE INDEX IF NOT EXISTS idx_stock_rec_code ON stock_recommendations(stock_code);
CREATE INDEX IF NOT EXISTS idx_stock_rec_time ON stock_recommendations(recommended_at);

-- 코멘트 추가
COMMENT ON TABLE stock_recommendations IS 'Claude Phase 1 기반 주식 추천 결과';
COMMENT ON COLUMN stock_recommendations.article_id IS '관련 뉴스 기사 ID';
COMMENT ON COLUMN stock_recommendations.stock_code IS '종목코드 (6자리)';
COMMENT ON COLUMN stock_recommendations.reasoning IS 'Claude가 추천한 근거';


-- stock_price_snapshots 테이블: KIS API에서 가져온 주가 데이터
CREATE TABLE IF NOT EXISTS stock_price_snapshots (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    price_date DATE NOT NULL,
    price_time TIME,
    open_price INTEGER,
    high_price INTEGER,
    low_price INTEGER,
    close_price INTEGER,
    volume BIGINT,
    data_type VARCHAR(20) NOT NULL,  -- 'daily' or 'intraday'
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, price_date, price_time, data_type)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_price_snapshot_code ON stock_price_snapshots(stock_code);
CREATE INDEX IF NOT EXISTS idx_price_snapshot_date ON stock_price_snapshots(price_date);
CREATE INDEX IF NOT EXISTS idx_price_snapshot_type ON stock_price_snapshots(data_type);

-- 코멘트 추가
COMMENT ON TABLE stock_price_snapshots IS 'KIS API에서 가져온 주가 스냅샷 데이터';
COMMENT ON COLUMN stock_price_snapshots.data_type IS 'daily: 일봉, intraday: 분봉';


-- stock_analysis_results 테이블: Claude Phase 2 분석 결과
CREATE TABLE IF NOT EXISTS stock_analysis_results (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES news_articles(id),
    recommendation_id INTEGER NOT NULL REFERENCES stock_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    probability INTEGER NOT NULL CHECK (probability >= 0 AND probability <= 100),
    reasoning TEXT,
    target_price INTEGER,
    stop_loss INTEGER,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(recommendation_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_analysis_article ON stock_analysis_results(article_id);
CREATE INDEX IF NOT EXISTS idx_analysis_code ON stock_analysis_results(stock_code);
CREATE INDEX IF NOT EXISTS idx_analysis_probability ON stock_analysis_results(probability);
CREATE INDEX IF NOT EXISTS idx_analysis_time ON stock_analysis_results(analyzed_at);

-- 코멘트 추가
COMMENT ON TABLE stock_analysis_results IS 'Claude Phase 2 기반 주가 상승 확률 분석 결과';
COMMENT ON COLUMN stock_analysis_results.probability IS '주가 상승 확률 (0-100)';
COMMENT ON COLUMN stock_analysis_results.target_price IS 'Claude가 제시한 목표가';
COMMENT ON COLUMN stock_analysis_results.stop_loss IS 'Claude가 제시한 손절가';


-- stock_holdings 테이블: threshold 이상인 종목 목록
CREATE TABLE IF NOT EXISTS stock_holdings (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES stock_analysis_results(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 0,
    average_price INTEGER,
    target_price INTEGER,
    stop_loss INTEGER,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, bought, sold
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_holdings_code ON stock_holdings(stock_code);
CREATE INDEX IF NOT EXISTS idx_holdings_status ON stock_holdings(status);
CREATE INDEX IF NOT EXISTS idx_holdings_added ON stock_holdings(added_at);

-- 코멘트 추가
COMMENT ON TABLE stock_holdings IS 'threshold 이상 확률의 보유 종목 목록';
COMMENT ON COLUMN stock_holdings.status IS 'pending: 대기중, bought: 매수완료, sold: 매도완료';


-- analysis_logs 테이블: 분석 실행 로그
CREATE TABLE IF NOT EXISTS analysis_logs (
    id SERIAL PRIMARY KEY,
    article_id INTEGER REFERENCES news_articles(id),
    status VARCHAR(20) NOT NULL,  -- success, partial, failed
    step VARCHAR(50),  -- 'recommendation', 'price_fetch', 'analysis', 'storage', 'complete'
    error_message TEXT,
    execution_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_analysis_logs_article ON analysis_logs(article_id);
CREATE INDEX IF NOT EXISTS idx_analysis_logs_status ON analysis_logs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_logs_time ON analysis_logs(created_at);

-- 코멘트 추가
COMMENT ON TABLE analysis_logs IS '주식 분석 실행 이력';
COMMENT ON COLUMN analysis_logs.step IS '실패 시 어느 단계에서 실패했는지 기록';


-- updated_at 자동 업데이트 트리거 (stock_holdings)
DROP TRIGGER IF EXISTS update_stock_holdings_updated_at ON stock_holdings;
CREATE TRIGGER update_stock_holdings_updated_at
    BEFORE UPDATE ON stock_holdings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- 마이그레이션 완료 메시지
DO $$
BEGIN
    RAISE NOTICE 'Migration 002: Analyzer tables created successfully';
END $$;
