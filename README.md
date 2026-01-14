# 네이버 금융 뉴스 스크래핑 시스템

네이버 금융 뉴스를 1분 간격으로 자동 수집하여 PostgreSQL DB에 저장하는 Docker 기반 마이크로서비스입니다.

## 주요 특징

- ⚡ **실시간 모니터링**: 1분 간격으로 새 뉴스 자동 수집
- 🐳 **Docker 컨테이너화**: 간편한 배포 및 확장
- 🔒 **스크래핑 방지 우회**: User-Agent 로테이션, 랜덤 딜레이, Proxy 지원
- 💾 **데이터 영구성**: 로컬 볼륨 마운트로 데이터 보존
- 🔄 **중복 방지**: 다중 레벨 중복 체크 (article_id, content_hash)
- 📊 **로깅 및 통계**: 상세한 스크래핑 이력 기록

## 기술 스택

- Python 3.11
- PostgreSQL 16
- Docker & Docker Compose
- BeautifulSoup4
- requests

## 프로젝트 구조

```
personal-finance/
├── docker-compose.yml          # Docker Compose 설정
├── .env                        # 환경 변수 (gitignore)
├── .env.example               # 환경 변수 템플릿
├── data/                      # PostgreSQL 데이터 (gitignore)
├── logs/                      # 로그 파일 (gitignore)
└── scraper/                   # 스크래퍼 애플리케이션
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── config/
    ├── scrapers/
    ├── models/
    ├── database/
    ├── utils/
    └── scheduler/
```

## 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 파일 생성
cp .env.example .env

# .env 파일 편집하여 비밀번호 설정
nano .env
```

### 2. 디렉토리 생성

```bash
mkdir -p data/postgres logs
```

### 3. 서비스 시작

```bash
# 빌드 및 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f wkf-scraper
```

### 4. 상태 확인

```bash
# 컨테이너 상태
docker-compose ps

# 데이터베이스 접속
docker exec -it wkf-postgres psql -U wkf_user -d finance_news

# 수집된 뉴스 개수 확인
SELECT COUNT(*) FROM news_articles;
```

## 서비스 관리

### 서비스 제어

```bash
# 중지
docker-compose stop

# 재시작
docker-compose restart

# 중지 및 컨테이너 삭제 (데이터는 유지)
docker-compose down

# 완전 삭제 (데이터 포함)
docker-compose down -v
rm -rf data/postgres
```

### 로그 확인

```bash
# 실시간 로그
docker-compose logs -f wkf-scraper

# 최근 100줄
docker-compose logs --tail=100 wkf-scraper

# 특정 서비스만
docker-compose logs wkf-postgres
```

## 데이터베이스

### 접속

```bash
docker exec -it wkf-postgres psql -U wkf_user -d finance_news
```

### 유용한 쿼리

```sql
-- 전체 뉴스 개수
SELECT COUNT(*) FROM news_articles;

-- 최근 뉴스 5개
SELECT title, scraped_at FROM news_articles
ORDER BY scraped_at DESC LIMIT 5;

-- 오늘 수집된 뉴스
SELECT COUNT(*) FROM news_articles
WHERE DATE(scraped_at) = CURRENT_DATE;

-- 스크래핑 통계
SELECT
    status,
    AVG(articles_new) as avg_new_articles,
    AVG(execution_time) as avg_execution_time_seconds
FROM scraping_logs
GROUP BY status;
```

### 백업 및 복원

```bash
# 백업
docker exec wkf-postgres pg_dump -U wkf_user finance_news > backup.sql

# 복원
docker exec -i wkf-postgres psql -U wkf_user -d finance_news < backup.sql
```

## 스크래핑 방지 우회 전략

시스템은 다음과 같은 우회 전략을 사용합니다:

1. **User-Agent 로테이션**: 20+ 실제 브라우저 User-Agent 풀에서 랜덤 선택
2. **HTTP 헤더 다양화**: Accept, Referer 등 실제 브라우저 헤더 모방
3. **랜덤 딜레이**: 0.5~2초 불규칙 딜레이로 봇 패턴 방지
4. **Session 관리**: 쿠키 유지 및 연결 재사용
5. **Retry 전략**: Rate limiting 감지 시 자동 재시도
6. **Proxy 지원**: 필요 시 프록시 서버 사용 가능

## 환경 변수 설정

주요 환경 변수:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SCRAPING_INTERVAL_SECONDS` | 60 | 스크래핑 간격 (초) |
| `MIN_DELAY_SECONDS` | 0.5 | 최소 랜덤 딜레이 |
| `MAX_DELAY_SECONDS` | 2.0 | 최대 랜덤 딜레이 |
| `PROXY_ENABLED` | false | 프록시 사용 여부 |
| `LOG_LEVEL` | INFO | 로그 레벨 (DEBUG, INFO, WARNING, ERROR) |

## 문제 해결

### 컨테이너가 시작하지 않는 경우

```bash
# 로그 확인
docker-compose logs wkf-scraper

# 환경 변수 확인
docker-compose config
```

### 데이터베이스 연결 실패

```bash
# PostgreSQL 상태 확인
docker-compose logs wkf-postgres

# healthcheck 상태 확인
docker inspect wkf-postgres | grep -A 10 Health
```

### 스크래핑이 차단된 경우

1. `.env`에서 `MIN_REQUEST_INTERVAL` 값 증가
2. `PROXY_ENABLED=true` 설정 후 프록시 서버 설정
3. `SCRAPING_INTERVAL_SECONDS` 값 증가 (예: 120초)

## 향후 확장

이 시스템은 확장 가능하도록 설계되었습니다. 새 서비스 추가 예시:

### API 서비스 추가

```yaml
# docker-compose.yml에 추가
wkf-api:
  build: ./api
  container_name: wkf-api
  environment:
    DB_HOST: wkf-postgres
    DB_PORT: 5432
    DB_NAME: ${DB_NAME}
    DB_USER: ${DB_USER}
    DB_PASSWORD: ${DB_PASSWORD}
  ports:
    - "8000:8000"
  depends_on:
    - wkf-postgres
  networks:
    - wkf-network
  restart: always
```

## 라이선스

개인 프로젝트

## 주의사항

- 웹 스크래핑은 대상 사이트의 이용 약관을 준수해야 합니다
- 과도한 요청은 IP 차단을 초래할 수 있습니다
- 프로덕션 환경에서는 `.env` 파일 보안에 주의하세요
- 정기적으로 `data/postgres` 디렉토리를 백업하세요
