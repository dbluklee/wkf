#!/usr/bin/env python3
"""
네이버 뉴스 스크래퍼 테스트
"""

import requests
from bs4 import BeautifulSoup

# 테스트할 URL
url = "https://n.news.naver.com/mnews/article/018/0006200888"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers)
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'lxml')

# 제목 찾기
print("\n=== 제목 찾기 ===")

# 패턴 1: h2#title_area
title1 = soup.select_one('h2#title_area')
if title1:
    print(f"✓ h2#title_area: {title1.get_text(strip=True)}")

# 패턴 2: .media_end_head_headline
title2 = soup.select_one('.media_end_head_headline')
if title2:
    print(f"✓ .media_end_head_headline: {title2.get_text(strip=True)}")

# 패턴 3: h2.media_end_head_headline
title3 = soup.select_one('h2.media_end_head_headline')
if title3:
    print(f"✓ h2.media_end_head_headline: {title3.get_text(strip=True)}")

# 본문 찾기
print("\n=== 본문 찾기 ===")

# 패턴 1: #dic_area
content1 = soup.select_one('#dic_area')
if content1:
    text = content1.get_text(separator='\n', strip=True)
    print(f"✓ #dic_area: {len(text)} chars")
    print(f"Preview: {text[:200]}...")

# 패턴 2: #newsct_article
content2 = soup.select_one('#newsct_article')
if content2:
    # 광고 등 제거
    for tag in content2.find_all(['script', 'style', 'iframe', 'ins', '.ad_area']):
        tag.decompose()
    text = content2.get_text(separator='\n', strip=True)
    print(f"✓ #newsct_article: {len(text)} chars")
    print(f"Preview: {text[:200]}...")

# 패턴 3: article.go_trans
content3 = soup.select_one('article.go_trans')
if content3:
    text = content3.get_text(separator='\n', strip=True)
    print(f"✓ article.go_trans: {len(text)} chars")
    print(f"Preview: {text[:200]}...")

print("\n완료!")
