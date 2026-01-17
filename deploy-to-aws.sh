#!/bin/bash

# AWS 배포 스크립트
# Usage: ./deploy-to-aws.sh <EC2_HOST>

set -e  # 에러 발생 시 즉시 중단

EC2_HOST="${1}"
EC2_USER="ubuntu"
PROJECT_DIR="~/personal-finance"

if [ -z "$EC2_HOST" ]; then
    echo "Usage: ./deploy-to-aws.sh <EC2_HOST>"
    echo "Example: ./deploy-to-aws.sh ec2-user@13.125.123.45"
    exit 1
fi

echo "=========================================="
echo "AWS 배포 시작: $EC2_HOST"
echo "=========================================="

# SSH 명령어 함수
ssh_exec() {
    ssh -o StrictHostKeyChecking=no "$EC2_HOST" "$@"
}

echo ""
echo "[1/7] 최신 코드 Pull..."
ssh_exec "cd $PROJECT_DIR && git pull origin main"

echo ""
echo "[2/7] 데이터베이스 마이그레이션 실행..."
ssh_exec "cd $PROJECT_DIR && docker exec wkf-postgres psql -U wkf_user -d finance_news -c \"
ALTER TABLE disclosures ADD COLUMN IF NOT EXISTS document_content TEXT;
CREATE INDEX IF NOT EXISTS idx_disclosures_has_content ON disclosures(id) WHERE document_content IS NOT NULL;
\""

echo ""
echo "[3/7] Docker 이미지 재빌드..."
ssh_exec "cd $PROJECT_DIR && docker-compose build --no-cache wkf-disclosure-scraper"

echo ""
echo "[4/7] 서비스 재시작..."
ssh_exec "cd $PROJECT_DIR && docker-compose down && docker-compose up -d"

echo ""
echo "[5/7] 서비스 상태 확인 (10초 대기)..."
sleep 10
ssh_exec "cd $PROJECT_DIR && docker-compose ps"

echo ""
echo "[6/7] Scraper 로그 확인..."
ssh_exec "cd $PROJECT_DIR && docker-compose logs --tail=20 wkf-disclosure-scraper"

echo ""
echo "[7/7] 배포 완료!"
echo ""
echo "=========================================="
echo "다음 명령어로 로그 모니터링:"
echo "ssh $EC2_HOST 'cd $PROJECT_DIR && docker-compose logs -f wkf-disclosure-scraper'"
echo "=========================================="
