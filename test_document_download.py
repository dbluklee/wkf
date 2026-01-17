#!/usr/bin/env python3
"""
테스트 스크립트: 기존 공시의 document 다운로드 및 분석 트리거
"""
import os
import sys
import psycopg2
import requests
import zipfile
import io
from bs4 import BeautifulSoup
import re

# 환경변수 로드
OPENDART_API_KEY = os.getenv('OPENDART_API_KEY')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'finance_news')
DB_USER = os.getenv('DB_USER', 'wkf_user')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def fetch_document(rcept_no):
    """OpenDART에서 document 다운로드"""
    url = f"https://opendart.fss.or.kr/api/document.xml"
    params = {
        "crtfc_key": OPENDART_API_KEY,
        "rcept_no": rcept_no
    }

    print(f"Downloading document for {rcept_no}...")
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    # ZIP 파일 압축 해제
    all_text = []
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        file_list = zip_file.namelist()
        print(f"Found {len(file_list)} files in ZIP")

        for file_name in file_list:
            try:
                content = zip_file.read(file_name)
                soup = BeautifulSoup(content, 'html.parser')

                # script, style 태그 제거
                for tag in soup(['script', 'style']):
                    tag.decompose()

                text = soup.get_text(separator='\n', strip=True)
                all_text.append(text)
                print(f"  - {file_name}: {len(text)} characters")
            except Exception as e:
                print(f"  - Failed to parse {file_name}: {e}")

    # 모든 텍스트 결합
    full_text = '\n\n'.join(all_text)

    # 텍스트 정리
    full_text = re.sub(r'\n\s*\n+', '\n\n', full_text)
    full_text = re.sub(r' +', ' ', full_text)

    # 최대 20,000자로 제한
    if len(full_text) > 20000:
        print(f"Document truncated from {len(full_text)} to 20,000 characters")
        full_text = full_text[:20000] + "\n\n[문서가 너무 길어 일부 생략됨]"

    print(f"Total document length: {len(full_text)} characters")
    return full_text

def update_disclosure(disclosure_id, document_content):
    """데이터베이스에 document_content 업데이트"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    try:
        cursor = conn.cursor()

        # document_content 업데이트
        cursor.execute("""
            UPDATE disclosures
            SET document_content = %s
            WHERE id = %s
        """, (document_content, disclosure_id))

        conn.commit()
        print(f"Updated disclosure ID {disclosure_id} with document content")

        # NOTIFY 트리거 (analyzer들이 분석하도록)
        cursor.execute("NOTIFY new_disclosure, %s", (str(disclosure_id),))
        conn.commit()
        print(f"Triggered analysis for disclosure ID {disclosure_id}")

    finally:
        cursor.close()
        conn.close()

def main():
    # 테스트할 공시 ID와 rcept_no
    disclosure_id = 106868
    rcept_no = "20260116900953"
    corp_name = "신시웨이"
    report_nm = "대표이사변경"

    print("="*60)
    print(f"Testing Document Download & Analysis")
    print(f"Disclosure: {corp_name} - {report_nm}")
    print(f"ID: {disclosure_id}, rcept_no: {rcept_no}")
    print("="*60)
    print()

    # 1. Document 다운로드
    try:
        document_content = fetch_document(rcept_no)
        print()
        print("Document preview (first 500 chars):")
        print("-"*60)
        print(document_content[:500])
        print("-"*60)
        print()

        # 2. 데이터베이스 업데이트 및 분석 트리거
        update_disclosure(disclosure_id, document_content)
        print()
        print("✅ Success! Check analyzer logs for analysis results.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
