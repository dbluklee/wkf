-- PostgreSQL NOTIFY/LISTEN 트리거 설정

-- 새 기사 삽입 시 analyzer에 알림을 보내는 함수
CREATE OR REPLACE FUNCTION notify_new_article()
RETURNS TRIGGER AS $$
BEGIN
    -- new_article 채널로 새 기사 ID를 NOTIFY
    PERFORM pg_notify('new_article', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 기존 트리거 삭제 (있다면)
DROP TRIGGER IF EXISTS new_article_trigger ON news_articles;

-- news_articles 테이블에 INSERT 후 트리거 생성
CREATE TRIGGER new_article_trigger
AFTER INSERT ON news_articles
FOR EACH ROW
EXECUTE FUNCTION notify_new_article();

-- 마이그레이션 완료 메시지
DO $$
BEGIN
    RAISE NOTICE 'Migration 003: NOTIFY trigger created successfully';
    RAISE NOTICE 'Analyzer will receive notifications on channel: new_article';
END $$;
