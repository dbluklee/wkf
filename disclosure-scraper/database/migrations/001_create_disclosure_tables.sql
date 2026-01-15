-- 공시 테이블 생성

-- 공시 데이터 테이블
CREATE TABLE IF NOT EXISTS disclosures (
    id SERIAL PRIMARY KEY,
    rcept_no VARCHAR(20) UNIQUE NOT NULL,  -- 접수번호
    corp_cls VARCHAR(1),  -- 법인구분 (Y: 유가증권, K: 코스닥, N: 코넥스, E: 기타)
    corp_code VARCHAR(8),  -- 고유번호
    corp_name VARCHAR(100),  -- 회사명
    stock_code VARCHAR(10),  -- 종목코드
    report_nm VARCHAR(200),  -- 보고서명
    flr_nm VARCHAR(100),  -- 공시제출인명
    rcept_dt VARCHAR(8),  -- 접수일자 (YYYYMMDD)
    rm TEXT,  -- 비고
    content_hash VARCHAR(64) UNIQUE NOT NULL,  -- 중복 방지용 해시
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_rcept_dt CHECK (rcept_dt ~ '^\d{8}$')
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_disclosures_rcept_dt ON disclosures(rcept_dt DESC);
CREATE INDEX IF NOT EXISTS idx_disclosures_stock_code ON disclosures(stock_code);
CREATE INDEX IF NOT EXISTS idx_disclosures_corp_name ON disclosures(corp_name);
CREATE INDEX IF NOT EXISTS idx_disclosures_corp_cls ON disclosures(corp_cls);
CREATE INDEX IF NOT EXISTS idx_disclosures_scraped_at ON disclosures(scraped_at DESC);

-- 공시 스크래핑 로그 테이블
CREATE TABLE IF NOT EXISTS disclosure_scraping_logs (
    id SERIAL PRIMARY KEY,
    bgn_de VARCHAR(8) NOT NULL,  -- 시작일자
    end_de VARCHAR(8) NOT NULL,  -- 종료일자
    total_fetched INTEGER NOT NULL DEFAULT 0,  -- 총 조회 건수
    new_count INTEGER NOT NULL DEFAULT 0,  -- 신규 저장 건수
    duplicate_count INTEGER NOT NULL DEFAULT 0,  -- 중복 건수
    error_count INTEGER NOT NULL DEFAULT 0,  -- 에러 건수
    execution_time FLOAT NOT NULL DEFAULT 0,  -- 실행 시간 (초)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_disclosure_logs_created_at ON disclosure_scraping_logs(created_at DESC);
