-- 네이버 금융 뉴스 테이블 생성

-- news_articles 테이블: 수집된 뉴스 기사 저장
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(100) UNIQUE NOT NULL,  -- 네이버 뉴스 고유 ID
    title VARCHAR(500) NOT NULL,              -- 뉴스 제목
    content TEXT,                             -- 뉴스 본문
    url VARCHAR(1000) NOT NULL,               -- 뉴스 URL
    content_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA256 해시 (중복 방지)
    published_at TIMESTAMP,                   -- 발행 시각
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 스크래핑 시각
    section_id VARCHAR(50),                   -- 카테고리 ID (예: 101 - 증권)
    section_id2 VARCHAR(50),                  -- 하위 카테고리 ID (예: 258 - 시황)
    status VARCHAR(20) DEFAULT 'active',      -- active, archived, deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_news_article_id ON news_articles(article_id);
CREATE INDEX IF NOT EXISTS idx_news_content_hash ON news_articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_news_scraped_at ON news_articles(scraped_at);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_news_section ON news_articles(section_id, section_id2);

-- 코멘트 추가
COMMENT ON TABLE news_articles IS '네이버 금융 뉴스 기사';
COMMENT ON COLUMN news_articles.article_id IS '네이버 뉴스 고유 ID (URL에서 추출)';
COMMENT ON COLUMN news_articles.content_hash IS 'SHA256 해시 (제목+내용)로 중복 방지';
COMMENT ON COLUMN news_articles.published_at IS '네이버에 표시된 발행 시각';
COMMENT ON COLUMN news_articles.scraped_at IS '실제 스크래핑된 시각';


-- scraping_logs 테이블: 스크래핑 실행 이력 기록
CREATE TABLE IF NOT EXISTS scraping_logs (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 실행 시각
    status VARCHAR(20) NOT NULL,                -- success, partial, failed
    articles_found INTEGER DEFAULT 0,           -- 발견된 전체 기사 수
    articles_new INTEGER DEFAULT 0,             -- 신규 저장된 기사 수
    articles_duplicate INTEGER DEFAULT 0,       -- 중복 감지된 기사 수
    error_message TEXT,                         -- 에러 메시지 (실패 시)
    execution_time FLOAT,                       -- 실행 시간 (초)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_scraping_logs_run_at ON scraping_logs(run_at);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_status ON scraping_logs(status);

-- 코멘트 추가
COMMENT ON TABLE scraping_logs IS '스크래핑 실행 이력';
COMMENT ON COLUMN scraping_logs.status IS 'success: 성공, partial: 일부 성공, failed: 실패';
COMMENT ON COLUMN scraping_logs.execution_time IS '실행 소요 시간 (초)';


-- updated_at 자동 업데이트 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- updated_at 트리거 생성
DROP TRIGGER IF EXISTS update_news_articles_updated_at ON news_articles;
CREATE TRIGGER update_news_articles_updated_at
    BEFORE UPDATE ON news_articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 마이그레이션 완료 메시지
DO $$
BEGIN
    RAISE NOTICE 'Migration 001: News tables created successfully';
END $$;
