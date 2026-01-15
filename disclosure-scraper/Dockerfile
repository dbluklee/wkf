# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY disclosure-scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY disclosure-scraper /app

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 애플리케이션 실행
CMD ["python", "-u", "main.py"]
