# WKF Finance - AI 기반 주식 자동 매매 시스템

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-20.10+-blue.svg)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-Private-red.svg)]()

한국 금융시장을 위한 멀티-LLM 기반 공시 분석 및 실시간 자동 매매 시스템입니다.

## 📋 목차

- [개요](#-개요)
- [주요 특징](#-주요-특징)
- [시스템 아키텍처](#-시스템-아키텍처)
- [기술 스택](#-기술-스택)
- [프로젝트 구조](#-프로젝트-구조)
- [빠른 시작](#-빠른-시작)
- [환경 변수 설정](#-환경-변수-설정)
- [AWS 배포](#-aws-배포)
- [사용 방법](#-사용-방법)
- [모니터링](#-모니터링)
- [문제 해결](#-문제-해결)
- [성능 최적화](#-성능-최적화)
- [보안 고려사항](#-보안-고려사항)
- [향후 개선](#-향후-개선)

---

## 🎯 개요

**WKF Finance**는 한국 금융시장의 공시 정보를 실시간으로 수집하고, **3개의 독립적인 AI 모델**(Claude, Gemini, ChatGPT)이 동시에 분석하여 투자 기회를 발굴한 후, **한국투자증권 API를 통해 자동으로 매매를 실행**하는 통합 시스템입니다.

### 핵심 기능

1. **공시 실시간 수집** (평일 09:00-15:00)
   - OpenDART API를 통한 공시 자동 수집
   - PostgreSQL NOTIFY/LISTEN 기반 이벤트 구동

2. **멀티-LLM 병렬 분석**
   - 3개 AI 모델의 독립적 분석 및 비교
   - 각 모델의 종목 추천 및 상승 확률 예측
   - 70% 이상 확률 시 자동 매수 대기열 추가

3. **실시간 자동 매매**
   - 한국투자증권 KIS OpenAPI 연동
   - 목표 수익률 2% 도달 시 자동 매도
   - 손절률 1% 도달 시 자동 손절
   - 15:20 강제 청산 (모든 포지션)

4. **성과 추적 및 비교**
   - LLM별 매매 성과 실시간 추적
   - 승률, ROI, 수익금 통계

---

## ✨ 주요 특징

### 🤖 멀티-LLM 분석 엔진

- **Claude Sonnet 4.5**: Anthropic의 최신 모델, 정확도 중심
- **Gemini 2.0 Flash**: Google의 고속 추론, 비용 효율적
- **GPT-4 Turbo**: OpenAI의 범용성, 다양한 관점

각 LLM은 **완전히 독립적으로 동작**하며, 서로의 판단에 영향을 받지 않습니다.

### 📊 2-Phase 분석 프로세스

**Phase 1: 종목 추천**
- 공시 내용 분석
- 관련 종목 추천 (최대 3개)
- 추천 근거 제시

**Phase 2: 상승 확률 예측**
- 직전 5일 일봉 데이터 수집
- 당일 분봉 데이터 수집
- 뉴스 + 주가 데이터 종합 분석
- 상승 확률 0-100% 예측
- 목표가 및 손절가 제안

### ⚡ 실시간 자동 매매

**매수 로직**
```
공시 발생 → LLM 분석 → 확률 ≥ 70% → holdings 추가 (pending)
→ TradeExecutor 감지 → KIS API 매수 주문 → status: bought
```

**매도 로직** (1분 간격 모니터링)
```
현재가 조회 → 수익률 계산
├─ 수익률 ≥ +2% → 목표가 도달 → 자동 매도
├─ 수익률 ≤ -1% → 손절가 도달 → 자동 손절
└─ 15:20 도달 → 수익률 무관 강제 매도
```

### 🔒 시간 제약 조건

- **공시 수집**: 평일 09:00-15:00만
- **자동 매매**: 평일 09:00-15:30만
- **강제 청산**: 매일 15:20 (모든 포지션 시장가 매도)
- **모니터링 중지**: 15:20 이후 다음 거래일까지 대기

### 🐳 Docker 마이크로서비스

- 5개 독립 컨테이너 (postgres, scraper, 3 analyzers)
- 자동 재시작 및 헬스체크
- 로그 영구 저장 및 데이터 백업

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                      wkf-network (Docker Bridge)                │
│                                                                 │
│  ┌──────────────┐                                              │
│  │ wkf-postgres │ ◄─────┐                                      │
│  │ PostgreSQL16 │       │ INSERT                               │
│  └──────┬───────┘       │                                      │
│         │               │                                      │
│         ▼               │                                      │
│  ┌─────────────────────┴────┐                                 │
│  │ wkf-disclosure-scraper   │                                 │
│  │ OpenDART API 공시 수집   │                                 │
│  │ (평일 09:00-15:00)       │                                 │
│  └──────────────────────────┘                                 │
│         │                                                       │
│         │ PostgreSQL NOTIFY 'new_disclosure'                   │
│         │                                                       │
│         ├────────────────┬────────────────┬───────────────┐    │
│         │                │                │               │    │
│         ▼                ▼                ▼               │    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │    │
│  │ wkf-analyzer │ │ wkf-analyzer │ │ wkf-analyzer │     │    │
│  │   -claude    │ │   -gemini    │ │   -openai    │     │    │
│  │              │ │              │ │              │     │    │
│  │ • LISTEN     │ │ • LISTEN     │ │ • LISTEN     │     │    │
│  │ • Analyze    │ │ • Analyze    │ │ • Analyze    │     │    │
│  │ • KIS API    │ │ • KIS API    │ │ • KIS API    │     │    │
│  │ • Auto Trade │ │ • Auto Trade │ │ • Auto Trade │     │    │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘     │    │
│         │                │                │             │    │
│         └────────────────┴────────────────┴─────────────┘    │
│                          │                                    │
│                          ▼                                    │
│                   wkf-postgres                                │
│          (분석 결과, 매매 기록, 성과 추적)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

1. **공시 수집**: `disclosure-scraper` → `disclosures` 테이블 INSERT
2. **이벤트 발생**: PostgreSQL Trigger → NOTIFY 'new_disclosure'
3. **병렬 분석**: 3개 analyzer가 동시에 LISTEN으로 알림 수신
4. **독립 처리**: 각 analyzer가 독립적으로:
   - LLM API 호출 (종목 추천)
   - KIS API 호출 (주가 데이터)
   - LLM API 호출 (상승 확률 예측)
   - DB 저장 (분석 결과 + llm_model 태그)
5. **자동 매매**: 각 analyzer의 TradeExecutor가:
   - pending holdings 조회 → 매수 실행
   - bought holdings 모니터링 → 조건 충족 시 매도

---

## 🛠️ 기술 스택

### Backend & Infrastructure
- **Python 3.11**: 메인 언어
- **PostgreSQL 16**: 데이터베이스
- **Docker & Docker Compose**: 컨테이너화
- **Ubuntu 22.04**: 서버 OS (AWS EC2)

### AI & LLM APIs
- **Anthropic Claude API** (claude-sonnet-4-5-20250929)
- **Google Gemini API** (gemini-2.0-flash-exp)
- **OpenAI API** (gpt-4-turbo-preview)

### Financial APIs
- **OpenDART API**: 금융감독원 공시 데이터
- **한국투자증권 KIS OpenAPI**: 실시간 주가 조회 및 매매

### Python Libraries
- `psycopg2`: PostgreSQL 연결
- `anthropic`: Claude API 클라이언트
- `google-generativeai`: Gemini API 클라이언트
- `openai`: OpenAI API 클라이언트
- `requests`: HTTP 통신
- `python-dotenv`: 환경 변수 관리
- `tenacity`: API 재시도 로직

---

## 📁 프로젝트 구조

```
personal-finance/
├── docker-compose.yml           # 5개 서비스 정의
├── .env                         # 환경 변수 (gitignore)
├── .env.example                 # 환경 변수 템플릿
├── README.md
├── .gitignore
│
├── data/                        # PostgreSQL 데이터 영구 저장
│   └── postgres/
│
├── logs/                        # 각 서비스별 로그 파일
│   ├── scraper.log
│   ├── analyzer-claude.log
│   ├── analyzer-gemini.log
│   └── analyzer-openai.log
│
├── disclosure-scraper/          # 공시 스크래핑 서비스
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── scrapers/
│   │   └── opendart_scraper.py
│   ├── services/
│   │   └── opendart_service.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── repositories.py
│   │   └── migrations/
│   │       └── 001_create_disclosure_tables.sql
│   └── utils/
│       └── logger.py
│
├── analyzer-claude/             # Claude 분석 서비스
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── services/
│   │   ├── claude_service.py
│   │   ├── kis_service.py
│   │   ├── trade_executor.py        # 자동 매매 실행
│   │   └── analyzer_orchestrator.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── repositories.py
│   │   └── migrations/
│   │       ├── 002_create_analyzer_tables.sql
│   │       └── 003_create_notify_trigger.sql
│   ├── listeners/
│   │   └── disclosure_listener.py
│   └── utils/
│       └── logger.py
│
├── analyzer-gemini/             # Gemini 분석 서비스
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config/
│   │   └── settings.py
│   ├── services/
│   │   ├── gemini_service.py
│   │   ├── kis_service.py
│   │   ├── trade_executor.py
│   │   └── analyzer_orchestrator.py
│   ├── database/
│   │   ├── connection.py
│   │   └── repositories.py
│   ├── listeners/
│   │   └── disclosure_listener.py
│   └── utils/
│       └── logger.py
│
└── analyzer-openai/             # OpenAI 분석 서비스
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── config/
    │   └── settings.py
    ├── services/
    │   ├── openai_service.py
    │   ├── kis_service.py
    │   ├── trade_executor.py
    │   └── analyzer_orchestrator.py
    ├── database/
    │   ├── connection.py
    │   └── repositories.py
    ├── listeners/
    │   └── disclosure_listener.py
    └── utils/
        └── logger.py
```

---

## 🚀 빠른 시작

### 사전 요구사항

- Docker 20.10+
- Docker Compose 2.0+
- Git
- 최소 2GB RAM, 10GB 디스크 공간

### 1. 프로젝트 클론

```bash
git clone https://github.com/dbluklee/wkf.git
cd wkf
```

### 2. 환경 변수 설정

```bash
# 템플릿 복사
cp .env.example .env

# 편집기로 열어서 API 키 입력
nano .env
```

**필수 설정:**
- `DB_PASSWORD`: PostgreSQL 비밀번호 (강력한 비밀번호 사용)
- `OPENDART_API_KEY`: OpenDART API 키 ([발급 링크](https://opendart.fss.or.kr/))
- `ANTHROPIC_API_KEY`: Claude API 키 ([발급 링크](https://console.anthropic.com/))
- `GEMINI_API_KEY`: Gemini API 키 ([발급 링크](https://ai.google.dev/))
- `OPENAI_API_KEY`: OpenAI API 키 ([발급 링크](https://platform.openai.com/))
- `KIS_APP_KEY`: 한국투자증권 앱 키
- `KIS_APP_SECRET`: 한국투자증권 시크릿
- `KIS_ACCOUNT_NUMBER`: 계좌번호 (예: 12345678-01)

### 3. 디렉토리 생성

```bash
mkdir -p data/postgres logs
chmod -R 755 data logs
```

### 4. 서비스 빌드 및 실행

```bash
# 이미지 빌드 (5-10분 소요)
docker-compose build

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 5. 동작 확인

```bash
# 컨테이너 상태 확인
docker-compose ps

# 데이터베이스 접속
docker exec -it wkf-postgres psql -U wkf_user -d finance_news

# 공시 수 확인
SELECT COUNT(*) FROM disclosures;

# analyzer 로그 확인
docker-compose logs -f wkf-analyzer-claude
```

---

## 🔧 환경 변수 설정

### .env 파일 전체 예시

```bash
# ===================================================================
# Database Configuration
# ===================================================================
DB_HOST=wkf-postgres
DB_PORT=5432
DB_NAME=finance_news
DB_USER=wkf_user
DB_PASSWORD=your_secure_password_here_change_me  # 반드시 변경!

POSTGRES_DB=finance_news
POSTGRES_USER=wkf_user
POSTGRES_PASSWORD=your_secure_password_here_change_me

# ===================================================================
# Disclosure Scraper Configuration
# ===================================================================
OPENDART_API_KEY=your_opendart_api_key_here
OPENDART_BASE_URL=https://opendart.fss.or.kr/api
SCRAPING_INTERVAL_SECONDS=60
CORP_CLS=                    # 빈 값 = 전체, Y = 상장, K = 코스닥
PAGE_COUNT=100

# ===================================================================
# Multi-LLM Analyzer Configuration
# ===================================================================

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-XXXX...

# Google Gemini API
GEMINI_API_KEY=AIzaSyXXXX...

# OpenAI API
OPENAI_API_KEY=sk-XXXX...

# Analysis Configuration
ANALYSIS_THRESHOLD_PERCENT=70         # 매수 확률 임계값 (%)
MAX_RECOMMENDATIONS_PER_ARTICLE=3     # 기사당 최대 추천 종목

# ===================================================================
# Korea Investment & Securities (KIS) API
# ===================================================================
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
KIS_ACCOUNT_NUMBER=12345678-01
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_IS_REAL_ACCOUNT=false             # false = 모의투자, true = 실전투자

# ===================================================================
# Market Configuration
# ===================================================================
MARKET_OPEN_HOUR=9
MARKET_OPEN_MINUTE=0
MARKET_CLOSE_HOUR=15
MARKET_CLOSE_MINUTE=30
STOCK_HISTORY_DAYS=5                  # 일봉 조회 일수

# ===================================================================
# Trading Configuration
# ===================================================================
PROFIT_TARGET_PERCENT=2.0             # 목표 수익률 (%)
STOP_LOSS_PERCENT=1.0                 # 손절 수익률 (%)
TRADE_MONITORING_INTERVAL_SECONDS=60  # 매매 모니터링 주기 (초)
TRADE_AMOUNT_PER_STOCK=1000000        # 종목당 매수 금액 (원)

# ===================================================================
# API Retry Configuration
# ===================================================================
MAX_API_RETRIES=3
RETRY_BACKOFF_FACTOR=2

# ===================================================================
# Logging
# ===================================================================
LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/analyzer.log
```

### 주요 설정 설명

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ANALYSIS_THRESHOLD_PERCENT` | 70 | 이 확률 이상이어야 매수 대기열 추가 |
| `PROFIT_TARGET_PERCENT` | 2.0 | 이 수익률 도달 시 자동 매도 |
| `STOP_LOSS_PERCENT` | 1.0 | 이 손실률 도달 시 자동 손절 |
| `TRADE_AMOUNT_PER_STOCK` | 1000000 | 종목당 매수할 금액 (원) |
| `KIS_IS_REAL_ACCOUNT` | false | 실전투자 사용 여부 (주의!) |

---

## ☁️ AWS 배포

### AWS 무료 티어 사용

**리소스:**
- EC2 t3.micro (1GB RAM, 2 vCPU)
- 무료 티어: 750시간/월 (12개월)
- EBS 30GB gp3
- 예상 비용: $0/월 (무료 기간 중)

### 빠른 배포 가이드

#### 1. EC2 인스턴스 생성

1. **AWS Console** → **EC2** → "인스턴스 시작"
2. **AMI**: Ubuntu Server 22.04 LTS
3. **인스턴스 유형**: t3.micro
4. **키 페어**: 새로 생성 (예: `wkf-key.pem`) → **다운로드 필수!**
5. **보안 그룹**: SSH (22) 허용, 소스: 내 IP
6. **스토리지**: 30GB gp3
7. "인스턴스 시작"

#### 2. SSH 접속 및 Docker 설치

```bash
# 로컬에서 EC2 접속
chmod 400 ~/Downloads/wkf-key.pem
ssh -i ~/Downloads/wkf-key.pem ubuntu@<EC2_PUBLIC_IP>

# EC2 인스턴스에서 실행
sudo apt update && sudo apt upgrade -y

# Docker 설치
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Docker 그룹 추가 및 재접속
sudo usermod -aG docker $USER
exit
```

#### 3. 프로젝트 배포

```bash
# 재접속
ssh -i ~/Downloads/wkf-key.pem ubuntu@<EC2_PUBLIC_IP>

# Git 설치 및 클론
sudo apt install -y git
git clone https://github.com/dbluklee/wkf.git
cd wkf

# 환경 변수 설정
nano .env
# (API 키 등 입력)

# 디렉토리 생성
mkdir -p data/postgres logs

# Swap 메모리 추가 (RAM 부족 대비)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 서비스 시작
docker-compose build
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

#### 4. 자동 시작 설정

```bash
# systemd 서비스 생성
sudo nano /etc/systemd/system/wkf-finance.service
```

**서비스 파일 내용:**
```ini
[Unit]
Description=WKF Finance Trading System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/wkf
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
```

**서비스 활성화:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable wkf-finance.service
sudo systemctl start wkf-finance.service
```

### 메모리 최적화 (t3.micro 1GB RAM)

`docker-compose.yml`에 메모리 제한 추가:

```yaml
services:
  wkf-postgres:
    deploy:
      resources:
        limits:
          memory: 256M

  wkf-disclosure-scraper:
    deploy:
      resources:
        limits:
          memory: 128M

  wkf-analyzer-claude:
    deploy:
      resources:
        limits:
          memory: 192M

  # gemini, openai 동일
```

**총 메모리 사용량:** ~960MB (1GB 이내)

---

## 📖 사용 방법

### 서비스 제어

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose stop

# 서비스 재시작
docker-compose restart

# 특정 서비스만 재시작
docker-compose restart wkf-analyzer-claude

# 서비스 중지 및 컨테이너 삭제 (데이터 유지)
docker-compose down

# 완전 삭제 (데이터 포함)
docker-compose down -v
sudo rm -rf data/postgres
```

### 로그 확인

```bash
# 전체 로그 실시간
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f wkf-analyzer-claude

# 최근 100줄만
docker-compose logs --tail=100 wkf-analyzer-gemini

# 로그 파일로 저장
docker-compose logs > full-logs.txt
```

### 데이터베이스 쿼리

```bash
# PostgreSQL 접속
docker exec -it wkf-postgres psql -U wkf_user -d finance_news
```

**유용한 쿼리:**

```sql
-- 전체 공시 수
SELECT COUNT(*) FROM disclosures;

-- 최근 공시 10개
SELECT rcept_no, corp_name, report_nm, rcept_dt
FROM disclosures
ORDER BY rcept_dt DESC, id DESC
LIMIT 10;

-- LLM별 분석 결과 수
SELECT
    llm_model,
    COUNT(*) as total_analyses,
    AVG(probability) as avg_probability
FROM stock_analysis_results
GROUP BY llm_model;

-- 현재 보유 종목 (bought 상태)
SELECT
    llm_model,
    stock_code,
    stock_name,
    quantity,
    average_price,
    target_price,
    stop_loss,
    added_at
FROM stock_holdings
WHERE status = 'bought'
ORDER BY added_at DESC;

-- 매매 완료 기록
SELECT
    llm_model,
    stock_code,
    stock_name,
    buy_price,
    sell_price,
    profit_loss,
    roi_percent,
    holding_days,
    sell_reason
FROM llm_performance_tracking
ORDER BY updated_at DESC
LIMIT 20;

-- LLM별 성과 비교
SELECT
    llm_model,
    COUNT(*) as total_trades,
    SUM(CASE WHEN roi_percent > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN roi_percent <= 0 THEN 1 ELSE 0 END) as losses,
    ROUND(AVG(roi_percent), 2) as avg_roi,
    SUM(profit_loss) as total_profit,
    ROUND(100.0 * SUM(CASE WHEN roi_percent > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
FROM llm_performance_tracking
GROUP BY llm_model
ORDER BY avg_roi DESC;
```

---

## 📊 모니터링

### 실시간 상태 확인

```bash
# 컨테이너 상태
docker-compose ps

# 리소스 사용량
docker stats

# 메모리 사용량만
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}"
```

### 로그 모니터링

```bash
# Analyzer 로그 (매매 활동)
tail -f logs/analyzer-claude.log | grep -E "Buy|Sell|Trade"

# Scraper 로그 (공시 수집)
tail -f logs/scraper.log | grep -E "New|Scraping"

# 에러만 확인
docker-compose logs | grep -i error
```

### 헬스체크

```bash
# PostgreSQL 헬스체크
docker inspect wkf-postgres | grep -A 10 Health

# 특정 서비스 재시작 횟수 확인
docker inspect wkf-analyzer-claude --format='{{.RestartCount}}'
```

---

## 🔍 문제 해결

### 1. 컨테이너가 계속 재시작됨

**증상:**
```bash
docker-compose ps
# wkf-analyzer-claude  Restarting
```

**원인 및 해결:**

**A. 메모리 부족 (OOM)**
```bash
# 로그 확인
docker-compose logs wkf-analyzer-claude | tail -50

# Swap 메모리 추가
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**B. API 키 오류**
```bash
# 로그에서 API 키 에러 확인
docker-compose logs wkf-analyzer-claude | grep -i "api key"

# .env 파일 수정
nano .env
# ANTHROPIC_API_KEY 확인

# 서비스 재시작
docker-compose restart wkf-analyzer-claude
```

**C. DB 연결 실패**
```bash
# PostgreSQL 상태 확인
docker-compose logs wkf-postgres

# DB 재시작
docker-compose restart wkf-postgres

# 5초 후 analyzer 재시작
sleep 5
docker-compose restart wkf-analyzer-claude wkf-analyzer-gemini wkf-analyzer-openai
```

### 2. 공시가 수집되지 않음

**확인 사항:**

```bash
# 1. Scraper 로그 확인
docker-compose logs wkf-disclosure-scraper | tail -50

# 2. OpenDART API 키 확인
docker exec -it wkf-disclosure-scraper env | grep OPENDART

# 3. 시간대 확인 (평일 9:00-15:00만 수집)
docker exec -it wkf-disclosure-scraper date

# 4. 네트워크 확인
docker exec -it wkf-disclosure-scraper ping -c 3 opendart.fss.or.kr
```

### 3. 매매가 실행되지 않음

**확인 사항:**

```bash
# 1. TradeExecutor 로그 확인
docker-compose logs wkf-analyzer-claude | grep -i "trade"

# 2. holdings 확인
docker exec -it wkf-postgres psql -U wkf_user -d finance_news -c "
SELECT status, COUNT(*)
FROM stock_holdings
GROUP BY status;
"

# 3. 장 시간 확인 (평일 9:00-15:30만 매매)
date

# 4. KIS API 연결 확인
docker-compose logs wkf-analyzer-claude | grep -i "kis"
```

### 4. 디스크 공간 부족

```bash
# 디스크 사용량 확인
df -h

# Docker 정리
docker system prune -a --volumes -f

# 오래된 로그 삭제 (7일 이상)
find ~/wkf/logs -type f -name "*.log" -mtime +7 -delete

# PostgreSQL 데이터 압축 (주의: 시간 소요)
docker exec wkf-postgres vacuumdb -U wkf_user -d finance_news --full --analyze
```

### 5. 특정 LLM API 오류

**Claude API 오류:**
```bash
# 로그 확인
docker-compose logs wkf-analyzer-claude | grep -i "anthropic\|claude"

# API 키 테스트
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5-20250929","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'
```

**Gemini API 오류:**
```bash
# 로그 확인
docker-compose logs wkf-analyzer-gemini | grep -i "gemini"

# API 키 테스트
curl "https://generativelanguage.googleapis.com/v1/models?key=$GEMINI_API_KEY"
```

**OpenAI API 오류:**
```bash
# 로그 확인
docker-compose logs wkf-analyzer-openai | grep -i "openai"

# API 키 테스트
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

## ⚡ 성능 최적화

### 1. PostgreSQL 튜닝

```bash
# postgresql.conf 수정
docker exec -it wkf-postgres bash

# 설정 파일 편집
apt update && apt install -y nano
nano /var/lib/postgresql/data/postgresql.conf
```

**추천 설정 (1GB RAM 환경):**
```ini
shared_buffers = 128MB
effective_cache_size = 512MB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 50
```

**재시작:**
```bash
docker-compose restart wkf-postgres
```

### 2. 로그 로테이션

```bash
# 로그 로테이션 설정
sudo nano /etc/logrotate.d/wkf-finance
```

**로테이션 설정:**
```
/home/ubuntu/wkf/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
```

### 3. 백업 자동화

```bash
# 백업 스크립트 생성
nano ~/backup-db.sh
```

**backup-db.sh:**
```bash
#!/bin/bash

BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL 백업
docker exec wkf-postgres pg_dump -U wkf_user finance_news | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
```

**실행 권한 및 cron 등록:**
```bash
chmod +x ~/backup-db.sh

# 매일 새벽 3시 백업
crontab -e
# 추가: 0 3 * * * /home/ubuntu/backup-db.sh >> /home/ubuntu/logs/backup.log 2>&1
```

---

## 🔒 보안 고려사항

### 1. 환경 변수 보호

```bash
# .env 파일 권한 제한
chmod 600 .env

# Git에 절대 커밋하지 않기
echo ".env" >> .gitignore
```

### 2. PostgreSQL 외부 접근 차단

```yaml
# docker-compose.yml에서 포트 바인딩 제거 또는 localhost만 허용
services:
  wkf-postgres:
    ports:
      - "127.0.0.1:5432:5432"  # localhost만 허용
```

### 3. SSH 보안 강화 (AWS EC2)

```bash
# Fail2Ban 설치
sudo apt install -y fail2ban

# 방화벽 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
```

### 4. KIS API 실전투자 주의

- **절대 실전투자 계좌를 테스트에 사용하지 마세요!**
- `KIS_IS_REAL_ACCOUNT=false`로 설정하여 모의투자로 충분히 테스트
- 실전투자 전환 시 소액으로 시작

### 5. API 키 로그 노출 방지

모든 로그에서 API 키가 마스킹되도록 설정되어 있으나, 추가 확인:

```bash
# 로그에서 API 키 검색 (없어야 정상)
grep -r "sk-ant-" logs/
grep -r "AIzaSy" logs/
```

---

## 🎯 향후 개선

### 단기 (1-2개월)

- [ ] 웹 대시보드 추가 (React + FastAPI)
- [ ] 텔레그램 알림 봇 연동
- [ ] 백테스팅 기능 (과거 데이터로 전략 검증)
- [ ] LLM 응답 캐싱 (비용 절감)

### 중기 (3-6개월)

- [ ] RDS PostgreSQL로 마이그레이션
- [ ] CloudWatch 로그 수집 및 알림
- [ ] 자동 스케일링 (ECS Fargate)
- [ ] 다중 계좌 지원

### 장기 (6개월+)

- [ ] 딥러닝 모델 추가 (LSTM, Transformer)
- [ ] 뉴스 감성 분석 파이프라인
- [ ] 포트폴리오 최적화 알고리즘
- [ ] RESTful API 제공

---

## 📝 라이선스

개인 프로젝트 (Private)

---

## ⚠️ 면책 조항

- 본 시스템은 **교육 및 연구 목적**으로 제작되었습니다
- 실제 투자 시 발생하는 **손실에 대한 책임은 사용자에게 있습니다**
- AI 모델의 예측은 **100% 정확하지 않으며**, 과거 성과가 미래 수익을 보장하지 않습니다
- 웹 스크래핑은 **대상 사이트의 이용 약관**을 준수해야 합니다
- **과도한 API 호출**은 비용 발생 및 계정 정지를 초래할 수 있습니다

---

## 📞 문의

프로젝트 관련 문의: [GitHub Issues](https://github.com/dbluklee/wkf/issues)

---

**Made with ❤️ by WKF Team**
