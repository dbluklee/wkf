# WKF Finance - Development Documentation

## Table of Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Development History](#development-history)
- [Local Development Setup](#local-development-setup)
- [AWS Free Tier Deployment](#aws-free-tier-deployment)
- [AWS Server Management](#aws-server-management)
- [Database Schema](#database-schema)
- [LLM Model Configuration](#llm-model-configuration)
- [Trading Logic](#trading-logic)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Cost Optimization](#cost-optimization)

---

## Project Overview

**WKF Finance** is an automated stock trading system that leverages multiple AI models (Claude, Gemini, ChatGPT) to analyze Korean financial disclosures in real-time and execute trades through the Korea Investment & Securities (KIS) API.

### Key Features

1. **Real-time Disclosure Scraping**
   - Fetches disclosures from OpenDART API every 60 seconds
   - Active during market hours (09:00-15:00 weekdays)
   - PostgreSQL NOTIFY/LISTEN event-driven architecture

2. **Multi-LLM Parallel Analysis**
   - 3 independent AI models analyze each disclosure simultaneously
   - Claude Haiku 3.5: Fast and cost-effective
   - Gemini 1.5 Flash: High-performance at low cost
   - GPT-4o Mini: Versatile and affordable
   - Each model provides probability predictions (0-100%)

3. **Automated Trading Execution**
   - Auto-buy when probability ≥ 70%
   - Auto-sell when profit target (+2%) or stop-loss (-1%) is reached
   - Forced liquidation at 15:20 daily
   - Real-time monitoring every 60 seconds

4. **Performance Tracking**
   - Per-LLM performance metrics (win rate, ROI, total profit)
   - Trade history with detailed analytics
   - Comparative analysis across models

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Docker Compose Network (wkf-network)            │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │ PostgreSQL   │ ◄──── Data persistence                          │
│  │    16        │                                                  │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         │ NOTIFY/LISTEN                                            │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────┐                                       │
│  │ Disclosure Scraper      │ ── OpenDART API                      │
│  │ (平日 09:00-15:00)       │                                       │
│  └────────┬────────────────┘                                       │
│           │                                                         │
│           │ INSERT + NOTIFY 'new_disclosure'                       │
│           │                                                         │
│           ├──────────────┬──────────────┬──────────────┐          │
│           │              │              │              │          │
│           ▼              ▼              ▼              │          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐      │          │
│  │ Analyzer   │  │ Analyzer   │  │ Analyzer   │      │          │
│  │  Claude    │  │  Gemini    │  │  OpenAI    │      │          │
│  │            │  │            │  │            │      │          │
│  │ • Listen   │  │ • Listen   │  │ • Listen   │      │          │
│  │ • Analyze  │  │ • Analyze  │  │ • Analyze  │      │          │
│  │ • Trade    │  │ • Trade    │  │ • Trade    │      │          │
│  └────────────┘  └────────────┘  └────────────┘      │          │
│           │              │              │              │          │
│           └──────────────┴──────────────┴──────────────┘          │
│                          │                                         │
│                          ▼                                         │
│                   PostgreSQL Storage                               │
│         (Analysis Results, Trade Records, Performance)             │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Disclosure Scraping**: Scraper → `disclosures` table INSERT
2. **Event Trigger**: PostgreSQL Trigger → NOTIFY 'new_disclosure'
3. **Parallel Analysis**: 3 analyzers simultaneously receive notification
4. **Independent Processing**: Each analyzer:
   - Phase 1: LLM recommends stocks from disclosure
   - Phase 2: Fetches price data (5-day daily + intraday)
   - Phase 3: LLM predicts probability (0-100%)
   - Phase 4: Saves results with `llm_model` tag
5. **Automated Trading**: Each analyzer's TradeExecutor:
   - Monitors `pending` holdings → Auto-buy
   - Monitors `bought` holdings → Auto-sell on conditions

---

## Technology Stack

### Core Technologies

- **Python 3.11**: Main programming language
- **PostgreSQL 16**: Relational database with NOTIFY/LISTEN
- **Docker Compose**: Multi-container orchestration
- **Ubuntu 22.04**: Deployment OS (AWS EC2)

### AI & LLM APIs

- **Anthropic Claude API** (`claude-3-5-haiku-20241022`)
  - Cost: $0.8/$4 per MTok (input/output)
  - Speed: ~1-2 seconds per request

- **Google Gemini API** (`gemini-1.5-flash`)
  - Cost: Free tier available, then $0.075/$0.3 per MTok
  - Speed: ~0.5-1 second per request

- **OpenAI API** (`gpt-4o-mini`)
  - Cost: $0.15/$0.6 per MTok
  - Speed: ~1-2 seconds per request

### Financial APIs

- **OpenDART API**: Korean Financial Supervisory Service disclosures
- **KIS OpenAPI**: Korea Investment & Securities (real-time quotes + trading)

### Python Libraries

```txt
psycopg2-binary==2.9.9      # PostgreSQL driver
anthropic==0.21.3           # Claude API client
google-generativeai==0.4.0  # Gemini API client
openai==1.12.0              # OpenAI API client
requests==2.31.0            # HTTP client
python-dotenv==1.0.1        # Environment variables
tenacity==8.2.3             # Retry logic
```

---

## Development History

### Phase 1: Initial Setup (Jan 2025)

1. **Docker Infrastructure**
   - Created 5-container architecture (postgres + scraper + 3 analyzers)
   - Implemented health checks and auto-restart policies
   - Added memory limits for AWS t3.micro (1GB RAM)

2. **Disclosure Scraper**
   - OpenDART API integration
   - Time-based scraping (weekdays 09:00-15:00 only)
   - PostgreSQL NOTIFY trigger implementation

3. **Multi-LLM Analyzer Framework**
   - Shared base class `BaseLLMService`
   - Independent analyzer services (Claude, Gemini, OpenAI)
   - 2-phase analysis process (recommend → predict)

4. **Trading System**
   - KIS API integration (OAuth2 token management)
   - Trade executor with monitoring loop
   - Profit target (+2%) and stop-loss (-1%) logic
   - Forced liquidation at 15:20

5. **Database Schema**
   - `disclosures`: Raw disclosure data
   - `stock_recommendations`: Phase 1 LLM recommendations
   - `stock_price_snapshots`: Historical price data
   - `stock_analysis_results`: Phase 2 probability predictions
   - `stock_holdings`: Current positions (pending/bought/sold)
   - `trade_orders`: Order execution records
   - `llm_performance_tracking`: Per-model performance metrics

### Phase 2: Cost Optimization (Jan 16, 2025)

**Problem**: Initial LLM model selection was too expensive
- Claude: Using `claude-sonnet-4-5-20250929` ($3/$15 per MTok)
- OpenAI: Using `gpt-4-turbo-preview` ($10/$30 per MTok)

**Solution**: Switched to cost-effective models
- Claude: → `claude-3-5-haiku-20241022` (**90% cost reduction**)
- Gemini: → `gemini-1.5-flash` (stable version)
- OpenAI: → `gpt-4o-mini` (**97% cost reduction**)

**Impact**: Reduced monthly API costs from ~$300 to ~$20 (expected)

### Phase 3: Bug Fixes (Jan 16, 2025)

**Critical Database Error**:
- Logs showed 1,451 database errors on Jan 16
- Error: "there is no unique or exclusion constraint matching the ON CONFLICT specification"
- Cause: Migrations not properly executed on AWS deployment
- Impact: No trades executed despite successful LLM API calls

**Resolution**: Documented proper AWS deployment procedure with migration verification

---

## Local Development Setup

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Minimum 2GB RAM, 10GB disk space

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/personal-finance.git
cd personal-finance
```

### Step 2: Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit with your API keys
nano .env
```

**Required Variables:**

```bash
# Database
DB_PASSWORD=secure_password_change_me

# OpenDART
OPENDART_API_KEY=your_opendart_key

# LLM APIs
ANTHROPIC_API_KEY=sk-ant-api03-XXX
GEMINI_API_KEY=AIzaSyXXX
OPENAI_API_KEY=sk-XXX

# KIS API
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
KIS_ACCOUNT_NUMBER=12345678-01
KIS_IS_REAL_ACCOUNT=false  # false = paper trading

# Trading Configuration
ANALYSIS_THRESHOLD_PERCENT=70    # Auto-buy threshold
PROFIT_TARGET_PERCENT=2.0        # +2% profit target
STOP_LOSS_PERCENT=1.0            # -1% stop loss
TRADE_AMOUNT_PER_STOCK=1000000   # 1M KRW per stock
```

### Step 3: Create Directories

```bash
mkdir -p data/postgres logs
chmod -R 755 data logs
```

### Step 4: Build and Start Services

```bash
# Build Docker images (5-10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 5: Verify Setup

```bash
# Check container status
docker-compose ps

# Connect to database
docker exec -it wkf-postgres psql -U wkf_user -d finance_news

# Check disclosures
SELECT COUNT(*) FROM disclosures;

# Check analyzer logs
docker-compose logs -f wkf-analyzer-claude
```

---

## AWS Free Tier Deployment

### Overview

Deploy the entire system on AWS Free Tier using:
- **EC2 t3.micro** (1GB RAM, 2 vCPU) - 750 hours/month free for 12 months
- **EBS gp3 30GB** - 30GB free for 12 months
- **Estimated Cost**: $0/month (within free tier limits)

### Step 1: Launch EC2 Instance

1. Go to **AWS Console** → **EC2** → "Launch Instance"
2. **Name**: `wkf-finance-server`
3. **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
4. **Instance Type**: t3.micro
5. **Key Pair**: Create new (e.g., `wkf-key.pem`) → **Download and save!**
6. **Security Group**:
   - SSH (22) - Source: My IP
7. **Storage**: 30GB gp3
8. Click "Launch Instance"

### Step 2: Connect to EC2

```bash
# On your local machine
chmod 400 ~/Downloads/wkf-key.pem
ssh -i ~/Downloads/wkf-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### Step 3: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker-compose --version

# Logout and login again for group changes
exit
```

### Step 4: Clone Repository via Git

```bash
# Reconnect to EC2
ssh -i ~/Downloads/wkf-key.pem ubuntu@<EC2_PUBLIC_IP>

# Install Git
sudo apt install -y git

# Clone your repository
git clone https://github.com/yourusername/personal-finance.git
cd personal-finance

# Or if private repo, use SSH
# git clone git@github.com:yourusername/personal-finance.git
```

### Step 5: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Important: Update these values:**
- Database password (strong password)
- All API keys (OpenDART, Claude, Gemini, OpenAI)
- KIS API credentials
- Set `KIS_IS_REAL_ACCOUNT=false` for paper trading

### Step 6: Add Swap Memory (RAM Optimization)

```bash
# Create 2GB swap file
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
```

### Step 7: Create Required Directories

```bash
mkdir -p data/postgres logs
chmod -R 755 data logs
```

### Step 8: Build and Start Services

```bash
# Build images (10-15 minutes on t3.micro)
docker-compose build

# Start services
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

### Step 9: Verify Deployment

```bash
# Check container status
docker-compose ps

# Should see:
# wkf-postgres           Up (healthy)
# wkf-disclosure-scraper Up
# wkf-analyzer-claude    Up
# wkf-analyzer-gemini    Up
# wkf-analyzer-openai    Up

# Check logs
docker-compose logs --tail=50 wkf-analyzer-claude

# Connect to database
docker exec -it wkf-postgres psql -U wkf_user -d finance_news

# Run queries
SELECT COUNT(*) FROM disclosures;
SELECT COUNT(*) FROM stock_analysis_results;
```

### Step 10: Enable Auto-Start (Optional)

Create systemd service for auto-start on reboot:

```bash
sudo nano /etc/systemd/system/wkf-finance.service
```

**Service file content:**

```ini
[Unit]
Description=WKF Finance Trading System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/personal-finance
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
```

**Enable service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable wkf-finance.service
sudo systemctl start wkf-finance.service

# Check status
sudo systemctl status wkf-finance.service
```

### Step 11: Git Workflow for Updates

```bash
# On AWS EC2, pull latest changes
cd ~/personal-finance
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

### Memory Optimization for t3.micro (1GB RAM)

The `docker-compose.yml` already includes memory limits:

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

  wkf-analyzer-gemini:
    deploy:
      resources:
        limits:
          memory: 192M

  wkf-analyzer-openai:
    deploy:
      resources:
        limits:
          memory: 192M
```

**Total: ~960MB** (within 1GB limit with 2GB swap)

---

## AWS Server Management

### 서버 접속 정보

**SSH 키 경로:**
```bash
~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem
```

**서버 주소:**
```bash
ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com
```

**기본 접속 명령어:**
```bash
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com
```

### 서비스 상태 확인

**모든 컨테이너 상태 확인:**
```bash
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose ps"
```

**특정 서비스 로그 확인:**
```bash
# Claude Analyzer 로그 (최근 50줄)
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose logs --tail=50 wkf-analyzer-claude"

# Gemini Analyzer 로그
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose logs --tail=50 wkf-analyzer-gemini"

# OpenAI Analyzer 로그
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose logs --tail=50 wkf-analyzer-openai"

# Disclosure Scraper 로그
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose logs --tail=50 wkf-disclosure-scraper"

# 모든 서비스 실시간 로그
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose logs -f"
```

**리소스 사용량 확인:**
```bash
# 컨테이너 리소스 사용량
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "docker stats --no-stream"

# 디스크 사용량
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "df -h"

# 메모리 사용량
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "free -h"
```

### 서비스 제어

**모든 서비스 중지:**
```bash
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose down"
```

**모든 서비스 시작:**
```bash
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose up -d"
```

**모든 서비스 재시작:**
```bash
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose restart"
```

**특정 서비스만 재시작:**
```bash
# Claude Analyzer만 재시작
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose restart wkf-analyzer-claude"

# Disclosure Scraper만 재시작
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose restart wkf-disclosure-scraper"
```

### 코드 업데이트 및 배포

**전체 업데이트 프로세스 (권장):**
```bash
# 1단계: 로컬에서 Git 상태 확인
git status
git log --oneline -5

# 2단계: 변경사항 커밋 및 푸시
git add -A
git commit -m "변경사항 설명"
git push origin main

# 3단계: AWS 서버 업데이트 (원라이너)
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose down && git pull origin main && docker-compose build --no-cache && docker-compose up -d"
```

**단계별 업데이트 (디버깅용):**
```bash
# 1. 서비스 중지
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose down"

# 2. 최신 코드 가져오기
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && git pull origin main"

# 3. 이미지 재빌드
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose build --no-cache"

# 4. 서비스 시작
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose up -d"

# 5. 상태 확인
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose ps"
```

**특정 서비스만 재빌드:**
```bash
# Disclosure Scraper만 재빌드
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && git pull origin main && docker-compose build --no-cache wkf-disclosure-scraper && docker-compose up -d wkf-disclosure-scraper"
```

### 데이터베이스 접속

**PostgreSQL 접속:**
```bash
# 서버 내부에서 접속
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "docker exec -it wkf-postgres psql -U wkf_user -d finance_news"
```

**로컬에서 원격 PostgreSQL 접속 (포트 포워딩):**
```bash
# 1. SSH 터널 생성 (별도 터미널)
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem -L 5433:localhost:5432 ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com

# 2. 로컬 클라이언트로 접속 (다른 터미널)
psql -h localhost -p 5433 -U wkf_user -d finance_news
# 비밀번호는 .env 파일의 DB_PASSWORD
```

**유용한 SQL 쿼리:**
```sql
-- 최근 공시 10건
SELECT id, corp_name, report_nm, rcept_dt
FROM disclosures
ORDER BY id DESC
LIMIT 10;

-- LLM별 분석 현황
SELECT
    llm_model,
    COUNT(*) as total_analyses,
    AVG(probability) as avg_probability
FROM stock_analysis_results
GROUP BY llm_model;

-- 현재 보유 포지션
SELECT
    llm_model,
    stock_code,
    stock_name,
    status,
    quantity,
    average_price
FROM stock_holdings
WHERE status = 'bought'
ORDER BY added_at DESC;

-- LLM별 성과
SELECT
    llm_model,
    COUNT(*) as total_trades,
    SUM(CASE WHEN roi_percent > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(roi_percent), 2) as avg_roi,
    SUM(profit_loss) as total_profit
FROM llm_performance_tracking
GROUP BY llm_model
ORDER BY avg_roi DESC;
```

### 문제 해결 (Troubleshooting)

**서비스가 반복적으로 재시작되는 경우:**
```bash
# 1. 로그 확인
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose logs --tail=100 [서비스명]"

# 2. 일반적인 원인:
# - 환경 변수 누락 (.env 파일 확인)
# - API 키 오류
# - 데이터베이스 연결 실패
# - 메모리 부족

# 3. 환경 변수 확인
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && cat .env | grep -v PASSWORD | grep -v KEY | grep -v SECRET"
```

**디스크 공간 부족:**
```bash
# Docker 이미지 정리
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "docker system prune -a -f"

# 로그 파일 정리
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && find logs -name '*.log' -mtime +7 -delete"
```

**메모리 부족:**
```bash
# Swap 메모리 확인
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "swapon --show"

# Swap 메모리 재생성 (없는 경우)
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
```

**데이터베이스 마이그레이션 실패:**
```bash
# 마이그레이션 수동 실행
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "docker exec -it wkf-postgres psql -U wkf_user -d finance_news -f /path/to/migration.sql"
```

**전체 시스템 재설정 (주의!):**
```bash
# 경고: 모든 데이터가 삭제됩니다!
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose down -v && docker system prune -a -f && rm -rf data/postgres/* && docker-compose up -d"
```

### 백업 및 복원

**데이터베이스 백업:**
```bash
# 백업 생성
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "docker exec wkf-postgres pg_dump -U wkf_user finance_news > ~/backup_\$(date +%Y%m%d_%H%M%S).sql"

# 로컬로 다운로드
scp -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com:~/backup_*.sql ~/Downloads/
```

**데이터베이스 복원:**
```bash
# 백업 파일 업로드
scp -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ~/Downloads/backup_20250117.sql ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com:~/

# 복원 실행
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "docker exec -i wkf-postgres psql -U wkf_user finance_news < ~/backup_20250117.sql"
```

### 서버 모니터링

**실시간 모니터링 스크립트:**
```bash
# watch를 사용한 실시간 모니터링 (로컬에서 실행)
watch -n 5 'ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && docker-compose ps"'
```

**자동화된 헬스 체크:**
```bash
# 모든 서비스 상태를 한 번에 확인
ssh -i ~/Documents/Private/Security/wk-aws-forwkf/wk-aws.pem ubuntu@ec2-52-65-220-245.ap-southeast-2.compute.amazonaws.com "cd ~/wkf && echo '=== Docker Compose Status ===' && docker-compose ps && echo -e '\n=== Disk Usage ===' && df -h / && echo -e '\n=== Memory Usage ===' && free -h && echo -e '\n=== Recent Errors ===' && docker-compose logs --tail=20 | grep -i error"
```

---

## Database Schema

### Core Tables

**1. disclosures** (Scraper output)
```sql
CREATE TABLE disclosures (
    id SERIAL PRIMARY KEY,
    rcept_no VARCHAR(20) UNIQUE NOT NULL,  -- Receipt number
    corp_code VARCHAR(10) NOT NULL,         -- Company code
    corp_name VARCHAR(100) NOT NULL,        -- Company name
    stock_code VARCHAR(10),                 -- Stock code (6 digits)
    report_nm VARCHAR(200) NOT NULL,        -- Report name
    rcept_dt VARCHAR(8) NOT NULL,           -- Receipt date (YYYYMMDD)
    flr_nm VARCHAR(100),                    -- Filer name
    rm TEXT,                                -- Remarks
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**2. stock_recommendations** (Phase 1: LLM recommends stocks)
```sql
CREATE TABLE stock_recommendations (
    id SERIAL PRIMARY KEY,
    disclosure_id INTEGER NOT NULL REFERENCES disclosures(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    reasoning TEXT,
    llm_model VARCHAR(20) NOT NULL,  -- 'claude', 'gemini', 'openai'
    recommended_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(disclosure_id, stock_code, llm_model)
);
```

**3. stock_analysis_results** (Phase 2: LLM predicts probability)
```sql
CREATE TABLE stock_analysis_results (
    id SERIAL PRIMARY KEY,
    disclosure_id INTEGER NOT NULL REFERENCES disclosures(id),
    recommendation_id INTEGER NOT NULL REFERENCES stock_recommendations(id),
    stock_code VARCHAR(10) NOT NULL,
    probability INTEGER NOT NULL CHECK (probability >= 0 AND probability <= 100),
    reasoning TEXT,
    target_price INTEGER,
    stop_loss INTEGER,
    llm_model VARCHAR(20) NOT NULL,
    analyzed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(recommendation_id)
);
```

**4. stock_holdings** (Current positions)
```sql
CREATE TABLE stock_holdings (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES stock_analysis_results(id),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 0,
    average_price INTEGER,
    target_price INTEGER,
    stop_loss INTEGER,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'bought', 'sold'
    llm_model VARCHAR(20) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**5. llm_performance_tracking** (Performance metrics)
```sql
CREATE TABLE llm_performance_tracking (
    id SERIAL PRIMARY KEY,
    holding_id INTEGER REFERENCES stock_holdings(id),
    llm_model VARCHAR(20) NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    buy_price INTEGER NOT NULL,
    sell_price INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    profit_loss INTEGER NOT NULL,           -- KRW
    roi_percent DECIMAL(10, 2) NOT NULL,    -- ROI %
    holding_days INTEGER,
    sell_reason VARCHAR(50),                -- 'profit_target', 'stop_loss', 'forced_liquidation'
    bought_at TIMESTAMP,
    sold_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## LLM Model Configuration

### Current Models (Cost-Optimized)

```python
# analyzer-claude/services/claude_service.py
self.model = "claude-3-5-haiku-20241022"

# analyzer-gemini/services/gemini_service.py
self.model = genai.GenerativeModel('gemini-1.5-flash')

# analyzer-openai/services/openai_service.py
self.model = "gpt-4o-mini"
```

### Cost Comparison

| Model | Input Cost | Output Cost | Speed | Use Case |
|-------|-----------|-------------|-------|----------|
| Claude Haiku 3.5 | $0.8/MTok | $4/MTok | Fast | Balanced |
| Gemini 1.5 Flash | $0.075/MTok | $0.3/MTok | Fastest | High volume |
| GPT-4o Mini | $0.15/MTok | $0.6/MTok | Fast | General |

### Previous Models (Before Optimization)

| Model | Input Cost | Output Cost | Savings |
|-------|-----------|-------------|---------|
| Claude Sonnet 4.5 | $3/MTok | $15/MTok | **90% ↓** |
| GPT-4 Turbo | $10/MTok | $30/MTok | **97% ↓** |

---

## Trading Logic

### Buy Logic

```python
def check_pending_holdings(self):
    """
    Check pending holdings and execute buy orders
    Runs during market hours (09:00-15:30)
    """
    # 1. Query pending holdings (status='pending', probability >= 70%)
    pending_holdings = self.db.get_pending_holdings()

    for holding in pending_holdings:
        # 2. Get current price from KIS API
        current_price = self.kis_service.get_current_price(holding['stock_code'])

        # 3. Calculate quantity (trade_amount / current_price)
        quantity = self.trade_amount // current_price

        # 4. Execute market buy order
        order = self.kis_service.market_buy(
            stock_code=holding['stock_code'],
            quantity=quantity
        )

        # 5. Update holding status to 'bought'
        self.db.update_holding(
            holding_id=holding['id'],
            status='bought',
            quantity=quantity,
            average_price=current_price
        )
```

### Sell Logic

```python
def monitor_bought_holdings(self):
    """
    Monitor bought holdings every 60 seconds
    Sell on profit target, stop loss, or forced liquidation
    """
    # 1. Query all bought holdings
    bought_holdings = self.db.get_bought_holdings()

    for holding in bought_holdings:
        # 2. Get current price
        current_price = self.kis_service.get_current_price(holding['stock_code'])

        # 3. Calculate ROI
        roi = ((current_price - holding['average_price']) / holding['average_price']) * 100

        # 4. Check sell conditions
        sell_reason = None

        if roi >= self.profit_target_percent:
            sell_reason = 'profit_target'  # +2%
        elif roi <= -self.stop_loss_percent:
            sell_reason = 'stop_loss'      # -1%
        elif current_time >= '15:20':
            sell_reason = 'forced_liquidation'

        if sell_reason:
            # 5. Execute market sell order
            self.kis_service.market_sell(
                stock_code=holding['stock_code'],
                quantity=holding['quantity']
            )

            # 6. Record performance
            self.db.record_performance(
                holding_id=holding['id'],
                sell_price=current_price,
                roi=roi,
                sell_reason=sell_reason
            )

            # 7. Update holding status to 'sold'
            self.db.update_holding(holding['id'], status='sold')
```

---

## Monitoring and Debugging

### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f wkf-analyzer-claude

# Filter for trades
docker-compose logs -f wkf-analyzer-claude | grep -i "buy\|sell"

# Filter for errors
docker-compose logs | grep -i error
```

### Check Database

```bash
# Connect to PostgreSQL
docker exec -it wkf-postgres psql -U wkf_user -d finance_news
```

**Useful Queries:**

```sql
-- Recent disclosures
SELECT id, corp_name, report_nm, rcept_dt
FROM disclosures
ORDER BY id DESC
LIMIT 10;

-- Analysis results by LLM
SELECT
    llm_model,
    COUNT(*) as total_analyses,
    AVG(probability) as avg_probability,
    MAX(probability) as max_probability
FROM stock_analysis_results
GROUP BY llm_model;

-- Current holdings
SELECT
    llm_model,
    stock_code,
    stock_name,
    status,
    quantity,
    average_price,
    target_price,
    stop_loss
FROM stock_holdings
WHERE status = 'bought'
ORDER BY added_at DESC;

-- LLM performance comparison
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

### Check Resource Usage

```bash
# Container status
docker-compose ps

# Resource usage (CPU, Memory)
docker stats

# Memory usage only
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}"
```

### Common Issues

**1. Container keeps restarting**

```bash
# Check logs for errors
docker-compose logs --tail=100 wkf-analyzer-claude

# Common causes:
# - Out of memory (add swap)
# - Invalid API key (check .env)
# - Database connection failed (restart postgres)
```

**2. No disclosures scraped**

```bash
# Check scraper logs
docker-compose logs wkf-disclosure-scraper | tail -50

# Verify time (should be weekday 09:00-15:00 KST)
docker exec -it wkf-disclosure-scraper date

# Test OpenDART API key
curl "https://opendart.fss.or.kr/api/list.json?crtfc_key=YOUR_KEY&bgn_de=20250101&pblntf_ty=A"
```

**3. No trades executed**

```bash
# Check TradeExecutor logs
docker-compose logs wkf-analyzer-claude | grep -i "trade\|buy\|sell"

# Verify market hours (weekday 09:00-15:30 KST)
date

# Check pending holdings
docker exec -it wkf-postgres psql -U wkf_user -d finance_news -c "
SELECT COUNT(*) as pending_count
FROM stock_holdings
WHERE status = 'pending' AND llm_model = 'claude';
"
```

---

## Cost Optimization

### Current Monthly Costs (Estimated)

**API Costs:**
- Claude Haiku 3.5: ~$5-10/month (100K requests)
- Gemini 1.5 Flash: ~$2-5/month (100K requests)
- GPT-4o Mini: ~$3-8/month (100K requests)
- OpenDART: Free
- KIS API: Free (paper trading)

**AWS Costs (Free Tier):**
- EC2 t3.micro: $0 (750 hours/month free)
- EBS 30GB: $0 (30GB free)
- Data transfer: $0 (1GB/month free)

**Total: ~$10-25/month** (after free tier expires: +$10 for EC2)

### Cost-Saving Tips

1. **Use smaller models**
   - Already using Haiku, Flash, and Mini (cheapest options)

2. **Cache LLM responses**
   - Implement response caching for duplicate disclosures
   - Save ~30% on repeated analysis

3. **Reduce analysis frequency**
   - Currently: Analyze every disclosure immediately
   - Alternative: Batch analysis every 5 minutes (reduce API calls)

4. **Limit max recommendations**
   - Currently: `MAX_RECOMMENDATIONS_PER_ARTICLE=3`
   - Reduce to 1 to cut API costs by 66%

5. **AWS Reserved Instances**
   - After free tier, use Reserved Instance (save ~30%)

---

## Future Improvements

### Short-term (1-2 months)

- [ ] Web dashboard (React + FastAPI)
- [ ] Telegram notification bot
- [ ] Backtesting framework
- [ ] LLM response caching

### Mid-term (3-6 months)

- [ ] Migrate to AWS RDS PostgreSQL
- [ ] CloudWatch logging and alerts
- [ ] Auto-scaling with ECS Fargate
- [ ] Multi-account support

### Long-term (6+ months)

- [ ] Deep learning models (LSTM, Transformer)
- [ ] News sentiment analysis pipeline
- [ ] Portfolio optimization algorithm
- [ ] RESTful API for external access

---

## Disclaimer

- This system is for **educational and research purposes only**
- **You are responsible** for any losses incurred from real trading
- AI predictions are **not 100% accurate**, and past performance does not guarantee future returns
- Excessive API usage may result in **unexpected costs** or account suspension
- Always test with **paper trading** before using real money

---

## Contact

For questions or issues, open a GitHub issue: [GitHub Issues](https://github.com/yourusername/personal-finance/issues)

---

**Developed with Claude Code by Anthropic**
