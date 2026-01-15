-- 공시 알림 트리거 생성

-- 새로운 공시가 삽입되면 analyzer들에게 알림을 보내는 함수
CREATE OR REPLACE FUNCTION notify_new_disclosure()
RETURNS TRIGGER AS $$
BEGIN
    -- new_disclosure 채널로 알림 전송 (payload: disclosure id)
    PERFORM pg_notify('new_disclosure', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
DROP TRIGGER IF EXISTS new_disclosure_trigger ON disclosures;

CREATE TRIGGER new_disclosure_trigger
AFTER INSERT ON disclosures
FOR EACH ROW
EXECUTE FUNCTION notify_new_disclosure();
