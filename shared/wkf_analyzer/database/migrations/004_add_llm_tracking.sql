-- 기존 테이블에 LLM 추적 필드 추가
-- stock_recommendations, stock_analysis_results, stock_holdings 테이블에
-- llm_model, llm_version 컬럼 추가

-- stock_recommendations 테이블에 LLM 추적 필드 추가
ALTER TABLE stock_recommendations
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(50),
ADD COLUMN IF NOT EXISTS llm_version VARCHAR(50);

-- UNIQUE 제약조건 수정 (llm_model 포함)
ALTER TABLE stock_recommendations
DROP CONSTRAINT IF EXISTS stock_recommendations_article_id_stock_code_key;

ALTER TABLE stock_recommendations
ADD CONSTRAINT stock_recommendations_article_id_stock_code_llm_unique
UNIQUE (article_id, stock_code, llm_model);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_recommendations_llm ON stock_recommendations(llm_model);

-- stock_analysis_results 테이블에 LLM 추적 필드 추가
ALTER TABLE stock_analysis_results
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(50),
ADD COLUMN IF NOT EXISTS llm_version VARCHAR(50);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_analysis_llm ON stock_analysis_results(llm_model);

-- stock_holdings 테이블에 LLM 추적 필드 추가
ALTER TABLE stock_holdings
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(50),
ADD COLUMN IF NOT EXISTS llm_version VARCHAR(50);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_holdings_llm ON stock_holdings(llm_model);
CREATE INDEX IF NOT EXISTS idx_holdings_status_llm ON stock_holdings(status, llm_model);

-- analysis_logs 테이블에 LLM 추적 필드 추가
ALTER TABLE analysis_logs
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(50);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_logs_llm ON analysis_logs(llm_model, created_at);
