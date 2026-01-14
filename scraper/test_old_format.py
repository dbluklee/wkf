#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

url = "https://finance.naver.com/news/news_read.naver?article_id=0006200888&office_id=018&mode=LSS2D&type=0&section_id=101&section_id2=258&section_id3=&date=20260115&page=1"

print(f"Testing URL: {url}\n")

response = requests.get(url)
response.encoding = 'euc-kr'

soup = BeautifulSoup(response.text, 'lxml')

# 제목 찾기
print("=== 제목 찾기 ===")
title_selectors = [
    'h2#title_area',
    'h2.media_end_head_headline',
    '.article_info h3',
    'h3.article_subject',
    '.article h3',
    'h2.end_tit',
]

for sel in title_selectors:
    elem = soup.select_one(sel)
    if elem:
        print(f"✓ {sel}: {elem.get_text(strip=True)[:80]}")

# 본문 찾기
print("\n=== 본문 찾기 ===")
content_selectors = [
    '#dic_area',
    '#articleCont',
    '#newsContentArea',
    '#articeBody',
    '.article_body',
    '.articleCont',
    '#content',
    '.end_body_wrp',
]

for sel in content_selectors:
    elem = soup.select_one(sel)
    if elem:
        text = elem.get_text(separator='\n', strip=True)
        print(f"✓ {sel}: {len(text)} chars")
        print(f"  Preview: {text[:150]}...")
        break
else:
    print("✗ No content found with any selector")

# 실제 iframe 확인
print("\n=== iframe 확인 ===")
iframes = soup.find_all('iframe')
for i, iframe in enumerate(iframes):
    print(f"iframe {i+1}: src={iframe.get('src')}")
