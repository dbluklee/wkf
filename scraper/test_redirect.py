#!/usr/bin/env python3
import requests

url = "https://finance.naver.com/news/news_read.naver?article_id=0006200888&office_id=018&mode=LSS2D&type=0&section_id=101&section_id2=258&section_id3=&date=20260115&page=1"

print(f"Original URL: {url}")

response = requests.get(url, allow_redirects=True)
print(f"Final URL: {response.url}")
print(f"Status: {response.status_code}")
print(f"'n.news.naver.com' in final URL: {'n.news.naver.com' in response.url}")
