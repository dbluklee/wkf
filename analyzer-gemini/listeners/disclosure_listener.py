"""
PostgreSQL NOTIFY/LISTEN 리스너 (공시)
"""

import select
import psycopg2
from typing import Callable

from database.connection import AnalyzerDatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)


class DisclosureListener:
    """새 공시 알림 리스너"""

    def __init__(self, db_manager: AnalyzerDatabaseManager, callback: Callable[[int], None]):
        """
        Args:
            db_manager: 데이터베이스 매니저
            callback: 새 공시 ID를 받아 처리할 함수
        """
        self.db_manager = db_manager
        self.callback = callback
        self.connection = None

    def start_listening(self):
        """
        LISTEN 시작 (무한 루프)

        새 공시가 INSERT되면 trigger가 NOTIFY를 보내고,
        이 함수가 알림을 받아서 callback 함수 호출
        """
        logger.info("Starting PostgreSQL LISTEN on channel 'new_disclosure'")

        try:
            # 전용 연결 생성 (LISTEN용)
            self.connection = psycopg2.connect(
                host=self.db_manager.settings.DB_HOST,
                port=self.db_manager.settings.DB_PORT,
                database=self.db_manager.settings.DB_NAME,
                user=self.db_manager.settings.DB_USER,
                password=self.db_manager.settings.DB_PASSWORD
            )

            # AUTOCOMMIT 모드 설정 (LISTEN/NOTIFY에 필요)
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            cursor = self.connection.cursor()
            cursor.execute("LISTEN new_disclosure;")

            logger.info("Now listening for new disclosures...")

            # 무한 루프로 알림 대기
            while True:
                # 5초 타임아웃으로 select 대기
                if select.select([self.connection], [], [], 5) == ([], [], []):
                    # 타임아웃 - 연결 유지 확인 (아무것도 안 함)
                    continue

                # 알림 poll
                self.connection.poll()

                # 대기 중인 모든 알림 처리
                while self.connection.notifies:
                    notify = self.connection.notifies.pop(0)
                    disclosure_id = int(notify.payload)

                    logger.info(f"Received notification: new disclosure_id={disclosure_id}")

                    # 콜백 함수 호출
                    try:
                        self.callback(disclosure_id)
                    except Exception as e:
                        logger.error(f"Error processing disclosure {disclosure_id}: {e}")
                        # 에러가 발생해도 리스너는 계속 동작

        except KeyboardInterrupt:
            logger.info("DisclosureListener interrupted by user")
            raise
        except Exception as e:
            logger.error(f"DisclosureListener error: {e}")
            raise
        finally:
            if self.connection:
                self.connection.close()
                logger.info("PostgreSQL LISTEN connection closed")

    def stop_listening(self):
        """LISTEN 중지"""
        if self.connection:
            try:
                cursor = self.connection.cursor()
                cursor.execute("UNLISTEN new_disclosure;")
                self.connection.close()
                logger.info("Stopped listening for new disclosures")
            except Exception as e:
                logger.warning(f"Error stopping listener: {e}")
