#!/usr/bin/env python3
"""
디버그용 스크래퍼 테스트
"""

import sys
from config.settings import Settings
from scrapers.naver_finance_scraper import NaverFinanceScraper
from models.news import NewsArticle

# 설정 로드
settings = Settings.from_env()

# 스크래퍼 생성
scraper = NaverFinanceScraper(settings)

# 테스트 URL
test_url = "https://n.news.naver.com/mnews/article/018/0006200888"
test_article = NewsArticle(
    article_id="test_001",
    title="테스트",
    url=test_url
)

print(f"Testing URL: {test_url}")
print("=" * 60)

# 스크래핑 실행
result = scraper.fetch_article_content(test_article)

if result:
    print(f"✓ Article ID: {result.article_id}")
    print(f"✓ Title: {result.title}")
    print(f"✓ Content length: {len(result.content or '')} chars")
    print(f"✓ Content preview: {(result.content or '')[:200]}...")
    print(f"✓ Published at: {result.published_at}")
    print(f"✓ Content hash: {result.content_hash}")
else:
    print("✗ Failed to scrape article")

scraper.close()
