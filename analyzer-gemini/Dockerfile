FROM python:3.11-slim

WORKDIR /app

# 시스템 종속성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 공유 라이브러리 먼저 설치
COPY shared /app/shared
RUN cd /app/shared && pip install --no-cache-dir -e .

# Python 의존성 설치
COPY analyzer-gemini/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY analyzer-gemini /app/analyzer-gemini
WORKDIR /app/analyzer-gemini

# 애플리케이션 실행
CMD ["python", "-u", "main.py"]
