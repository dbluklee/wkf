-- 뉴스/공시 통합 지원을 위한 스키마 수정
-- article_id 또는 disclosure_id 중 하나를 사용할 수 있도록 변경

-- 1. stock_recommendations 테이블 수정
-- disclosure_id 컬럼 추가
ALTER TABLE stock_recommendations
ADD COLUMN IF NOT EXISTS disclosure_id INTEGER REFERENCES disclosures(id);

-- source_type 컬럼 추가
ALTER TABLE stock_recommendations
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'news' CHECK (source_type IN ('news', 'disclosure'));

-- 기존 article_id를 nullable로 변경 (이미 nullable일 수 있음)
ALTER TABLE stock_recommendations
ALTER COLUMN article_id DROP NOT NULL;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_recommendations_disclosure ON stock_recommendations(disclosure_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_source_type ON stock_recommendations(source_type);

-- 2. stock_analysis_results 테이블 수정
-- disclosure_id 컬럼 추가
ALTER TABLE stock_analysis_results
ADD COLUMN IF NOT EXISTS disclosure_id INTEGER REFERENCES disclosures(id);

-- source_type 컬럼 추가
ALTER TABLE stock_analysis_results
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'news' CHECK (source_type IN ('news', 'disclosure'));

-- 기존 article_id를 nullable로 변경
ALTER TABLE stock_analysis_results
ALTER COLUMN article_id DROP NOT NULL;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_analysis_disclosure ON stock_analysis_results(disclosure_id);
CREATE INDEX IF NOT EXISTS idx_analysis_source_type ON stock_analysis_results(source_type);

-- 3. stock_holdings 테이블에 source_type 추가
ALTER TABLE stock_holdings
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'news' CHECK (source_type IN ('news', 'disclosure'));

CREATE INDEX IF NOT EXISTS idx_holdings_source_type ON stock_holdings(source_type);

-- 4. llm_performance_tracking 테이블에 source_type 추가
ALTER TABLE llm_performance_tracking
ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) DEFAULT 'news' CHECK (source_type IN ('news', 'disclosure'));

CREATE INDEX IF NOT EXISTS idx_performance_source_type ON llm_performance_tracking(source_type);

-- 코멘트 추가
COMMENT ON COLUMN stock_recommendations.source_type IS '데이터 소스: news(뉴스), disclosure(공시)';
COMMENT ON COLUMN stock_analysis_results.source_type IS '데이터 소스: news(뉴스), disclosure(공시)';
COMMENT ON COLUMN stock_holdings.source_type IS '데이터 소스: news(뉴스), disclosure(공시)';
COMMENT ON COLUMN llm_performance_tracking.source_type IS '데이터 소스: news(뉴스), disclosure(공시)';
