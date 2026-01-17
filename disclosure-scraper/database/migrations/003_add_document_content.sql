-- 공시 상세 내용 컬럼 추가

-- disclosures 테이블에 document_content 컬럼 추가
ALTER TABLE disclosures
ADD COLUMN IF NOT EXISTS document_content TEXT;

-- 인덱스 추가 (document_content가 NULL이 아닌 행을 빠르게 찾기 위해)
CREATE INDEX IF NOT EXISTS idx_disclosures_has_content
ON disclosures(id)
WHERE document_content IS NOT NULL;
