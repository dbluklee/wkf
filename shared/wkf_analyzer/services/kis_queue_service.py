"""
KIS API 요청 큐잉 및 캐싱 서비스

여러 analyzer가 동시에 KIS API를 호출할 때:
1. 큐를 통해 순차적으로 처리
2. 동일 종목에 대한 조회는 캐시에서 반환 (TTL: 60초)
3. OAuth2 토큰을 모든 analyzer가 공유 (DB 기반 중복 요청 방지)
"""
import threading
import time
import requests
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from queue import Queue
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """캐시 항목"""
    data: any
    expires_at: datetime


class KISQueueService:
    """KIS API 요청 큐잉 및 캐싱 서비스 (Singleton)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.request_queue = Queue()
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_lock = threading.Lock()
        self.is_running = False
        self.worker_thread = None

        # 캐시 TTL (초)
        self.CACHE_TTL_SECONDS = 60

        # 요청 간 최소 간격 (초) - KIS API rate limit 고려
        self.MIN_REQUEST_INTERVAL = 0.2  # 200ms

        # OAuth2 토큰 관리 (DB 기반 공유)
        self._token_lock = threading.Lock()

        # KIS API 설정 (첫 번째 KISService 인스턴스가 설정)
        self._base_url = None
        self._app_key = None
        self._app_secret = None

        # Database settings (will be set by configure_database)
        self._db_settings = None

        logger.info("KISQueueService initialized (Singleton)")

    def start(self):
        """워커 스레드 시작"""
        if self.is_running:
            logger.warning("KISQueueService already running")
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("KISQueueService worker thread started")

    def stop(self):
        """워커 스레드 중지"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("KISQueueService stopped")

    def _worker(self):
        """워커 스레드 - 큐에서 요청을 꺼내 순차적으로 처리"""
        logger.info("KISQueueService worker thread running")
        last_request_time = 0

        while self.is_running:
            try:
                # 큐에서 요청 가져오기 (1초 타임아웃)
                if not self.request_queue.empty():
                    request = self.request_queue.get(timeout=1)

                    # 최소 요청 간격 확보
                    elapsed = time.time() - last_request_time
                    if elapsed < self.MIN_REQUEST_INTERVAL:
                        time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)

                    # 요청 실행
                    try:
                        cache_key = request['cache_key']
                        func = request['func']
                        args = request['args']
                        kwargs = request['kwargs']
                        result_holder = request['result_holder']

                        logger.debug(f"Processing KIS API request: {cache_key}")
                        result = func(*args, **kwargs)

                        # 결과 저장
                        result_holder['result'] = result
                        result_holder['error'] = None

                        # 캐시 저장 (성공한 경우만)
                        if result is not None:
                            self._set_cache(cache_key, result)

                        last_request_time = time.time()

                    except Exception as e:
                        logger.error(f"Error processing KIS API request: {e}")
                        result_holder['result'] = None
                        result_holder['error'] = e

                    finally:
                        result_holder['done'] = True
                        self.request_queue.task_done()

                else:
                    # 큐가 비어있으면 잠시 대기
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                time.sleep(0.5)

        logger.info("KISQueueService worker thread stopped")

    def _get_cache(self, key: str) -> Optional[any]:
        """캐시에서 데이터 가져오기 (만료되지 않은 경우)"""
        with self.cache_lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry.expires_at:
                    logger.debug(f"Cache HIT: {key}")
                    return entry.data
                else:
                    # 만료된 캐시 삭제
                    logger.debug(f"Cache EXPIRED: {key}")
                    del self.cache[key]

            logger.debug(f"Cache MISS: {key}")
            return None

    def _set_cache(self, key: str, data: any):
        """캐시에 데이터 저장"""
        with self.cache_lock:
            expires_at = datetime.now() + timedelta(seconds=self.CACHE_TTL_SECONDS)
            self.cache[key] = CacheEntry(data=data, expires_at=expires_at)
            logger.debug(f"Cache SET: {key} (expires at {expires_at.strftime('%H:%M:%S')})")

    def configure_database(self, db_settings):
        """
        데이터베이스 설정 (토큰 공유용)

        Args:
            db_settings: Database connection settings (host, port, dbname, user, password)
        """
        if self._db_settings is None:
            self._db_settings = db_settings
            logger.info("KIS Queue Service database configured")

    def configure_kis_api(self, base_url: str, app_key: str, app_secret: str):
        """
        KIS API 설정 (첫 번째 KISService 인스턴스가 호출)

        Args:
            base_url: KIS API base URL
            app_key: App key
            app_secret: App secret
        """
        if self._base_url is None:
            self._base_url = base_url
            self._app_key = app_key
            self._app_secret = app_secret
            logger.info("KIS API credentials configured")

    def _get_db_connection(self):
        """데이터베이스 연결 생성"""
        if not self._db_settings:
            raise ValueError("Database not configured. Call configure_database() first.")

        return psycopg2.connect(
            host=self._db_settings['host'],
            port=self._db_settings['port'],
            dbname=self._db_settings['dbname'],
            user=self._db_settings['user'],
            password=self._db_settings['password']
        )

    def _get_token_from_db(self) -> Optional[tuple]:
        """
        데이터베이스에서 토큰 조회

        Returns:
            (access_token, expires_at) tuple or None
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT access_token, expires_at
                FROM kis_shared_token
                WHERE id = 1 AND expires_at > NOW()
            """)

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                logger.debug("Retrieved token from database")
                return result

            return None

        except Exception as e:
            logger.warning(f"Failed to get token from database: {e}")
            return None

    def _save_token_to_db(self, access_token: str, expires_at: datetime):
        """
        데이터베이스에 토큰 저장

        Args:
            access_token: OAuth2 access token
            expires_at: Token expiration timestamp
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO kis_shared_token (id, access_token, expires_at)
                VALUES (1, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = CURRENT_TIMESTAMP
            """, (access_token, expires_at))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Saved token to database, expires at {expires_at}")

        except Exception as e:
            logger.error(f"Failed to save token to database: {e}")

    def get_shared_token(self) -> str:
        """
        공유 OAuth2 토큰 반환 (DB 기반, 모든 컨테이너 공유)

        1. DB에서 유효한 토큰 조회
        2. 없으면 새로 발급하여 DB에 저장
        3. 다른 컨테이너가 동시에 발급 시도하면 재시도

        Returns:
            Access token
        """
        import random

        with self._token_lock:
            # 1. DB에서 유효한 토큰 조회
            db_token = self._get_token_from_db()
            if db_token:
                access_token, expires_at = db_token
                logger.debug(f"Using shared token from DB (expires at {expires_at})")
                return access_token

            # 2. DB에 토큰이 없으면 새로 발급
            if not all([self._base_url, self._app_key, self._app_secret]):
                raise ValueError("KIS API credentials not configured. Call configure_kis_api() first.")

            # 컨테이너 간 경합 방지를 위한 재시도 로직
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 재시도 전 DB 재확인 (다른 컨테이너가 이미 발급했을 수 있음)
                    if attempt > 0:
                        delay = random.uniform(0.1, 0.5)
                        logger.info(f"Retrying KIS token request (attempt {attempt + 1}/{max_retries}) after {delay:.2f}s delay")
                        time.sleep(delay)

                        # DB 재확인
                        db_token = self._get_token_from_db()
                        if db_token:
                            access_token, expires_at = db_token
                            logger.info(f"Another container issued token, using shared token from DB")
                            return access_token

                    url = f"{self._base_url}/oauth2/tokenP"
                    headers = {"content-type": "application/json"}
                    data = {
                        "grant_type": "client_credentials",
                        "appkey": self._app_key,
                        "appsecret": self._app_secret
                    }

                    logger.info("Requesting new KIS OAuth2 token...")
                    response = requests.post(url, json=data, headers=headers, timeout=10)
                    response.raise_for_status()
                    result = response.json()

                    access_token = result['access_token']
                    expires_in = result['expires_in']
                    # 5분 여유를 두고 만료 시간 설정
                    expires_at = datetime.now() + timedelta(seconds=expires_in - 300)

                    # 3. DB에 저장
                    self._save_token_to_db(access_token, expires_at)

                    logger.info(f"KIS OAuth2 token issued and saved to DB, expires at {expires_at}")
                    return access_token

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 403 and attempt < max_retries - 1:
                        # 403 에러는 다른 컨테이너가 동시 요청했을 가능성
                        logger.warning(f"Got 403 error (likely concurrent request), will retry")
                        continue
                    else:
                        logger.error(f"Failed to get KIS token: {e}")
                        raise
                except Exception as e:
                    logger.error(f"Failed to get KIS token: {e}")
                    raise

    def enqueue_request(
        self,
        cache_key: str,
        func: Callable,
        *args,
        **kwargs
    ) -> any:
        """
        KIS API 요청을 큐에 추가하고 결과 대기

        Args:
            cache_key: 캐시 키 (예: "daily_005930", "intraday_005930", "current_005930")
            func: 실행할 함수
            *args, **kwargs: 함수 인자

        Returns:
            API 응답 결과 (또는 캐시된 결과)
        """
        # 1. 캐시 확인
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data

        # 2. 큐에 요청 추가
        result_holder = {
            'result': None,
            'error': None,
            'done': False
        }

        request = {
            'cache_key': cache_key,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'result_holder': result_holder
        }

        self.request_queue.put(request)
        logger.debug(f"Enqueued KIS API request: {cache_key} (queue size: {self.request_queue.qsize()})")

        # 3. 결과 대기 (최대 30초)
        start_time = time.time()
        timeout = 30

        while not result_holder['done']:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"KIS API request timeout: {cache_key}")
            time.sleep(0.1)

        # 4. 에러 발생 시 예외 발생
        if result_holder['error']:
            raise result_holder['error']

        return result_holder['result']

    def clear_cache(self):
        """캐시 전체 삭제"""
        with self.cache_lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared {count} cache entries")

    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        with self.cache_lock:
            cache_size = len(self.cache)

        return {
            'cache_size': cache_size,
            'queue_size': self.request_queue.qsize(),
            'is_running': self.is_running
        }


# 전역 싱글톤 인스턴스
_kis_queue_service = KISQueueService()


def get_kis_queue_service() -> KISQueueService:
    """KIS 큐 서비스 싱글톤 인스턴스 반환"""
    return _kis_queue_service
