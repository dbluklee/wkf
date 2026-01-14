"""
네이버 금융 뉴스 스크래퍼

네이버 금융 뉴스 목록 및 상세 페이지를 스크래핑합니다.
"""

from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from scrapers.base_scraper import BaseScraper
from models.news import NewsArticle
from utils.hash_utils import generate_article_id, generate_content_hash
from utils.logger import get_logger
from utils.timezone_utils import naive_to_kst, remove_timezone
from config.settings import Settings

logger = get_logger(__name__)


class NaverFinanceScraper(BaseScraper):
    """네이버 금융 뉴스 스크래퍼"""

    def __init__(self, settings: Settings):
        """
        Args:
            settings: 설정 객체
        """
        super().__init__(settings)
        self.base_url = settings.TARGET_URL
        logger.info(f"NaverFinanceScraper initialized: {self.base_url}")

    def fetch_news_list(self) -> List[NewsArticle]:
        """
        뉴스 목록 페이지를 스크래핑하여 뉴스 기사 목록 반환

        Returns:
            NewsArticle 객체 리스트 (content는 None)
        """
        try:
            logger.info("Fetching news list...")

            response = self.get(self.base_url, referer='https://finance.naver.com/')

            if not response:
                logger.error("Failed to fetch news list page")
                return []

            # 네이버 인코딩 설정 (euc-kr)
            response.encoding = 'euc-kr'

            soup = BeautifulSoup(response.text, 'lxml')
            articles = []

            # 네이버 금융 뉴스 목록 파싱
            # 실제 HTML 구조에 따라 셀렉터 조정 필요
            # 가능한 셀렉터: .newsList .articleSubject, .newsflash_body .article, etc.

            # 패턴 1: .newsList .articleSubject
            news_items = soup.select('.newsList .articleSubject')

            # 패턴이 없으면 다른 셀렉터 시도
            if not news_items:
                news_items = soup.select('.newsflash_body .article')

            # 여전히 없으면 더 일반적인 셀렉터
            if not news_items:
                news_items = soup.select('td.title a')

            logger.info(f"Found {len(news_items)} news items with current selector")

            for item in news_items:
                try:
                    # a 태그 찾기
                    if item.name == 'a':
                        link_tag = item
                    else:
                        link_tag = item.find('a')

                    if not link_tag:
                        continue

                    title = link_tag.get_text(strip=True)
                    relative_url = link_tag.get('href')

                    if not title or not relative_url:
                        continue

                    # 절대 URL 생성
                    if relative_url.startswith('http'):
                        full_url = relative_url
                    elif relative_url.startswith('//'):
                        full_url = f'https:{relative_url}'
                    else:
                        full_url = f'https://finance.naver.com{relative_url}'

                    # article_id 생성
                    article_id = generate_article_id(full_url, title)

                    article = NewsArticle(
                        article_id=article_id,
                        title=title,
                        url=full_url
                    )

                    articles.append(article)

                except Exception as e:
                    logger.error(f"Failed to parse article item: {e}")
                    continue

            logger.info(f"Successfully parsed {len(articles)} articles from list page")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch news list: {e}")
            return []

    def fetch_article_content(self, article: NewsArticle) -> Optional[NewsArticle]:
        """
        개별 뉴스 기사 상세 페이지를 스크래핑하여 내용 추출

        Args:
            article: 기본 정보가 있는 NewsArticle 객체

        Returns:
            내용이 채워진 NewsArticle 객체 또는 None
        """
        try:
            logger.debug(f"Fetching article content: {article.article_id}")

            response = self.get(article.url, referer=self.base_url)

            if not response:
                logger.warning(f"Failed to fetch article: {article.article_id}")
                return None

            # 네이버 뉴스 인코딩 설정
            response.encoding = 'euc-kr'  # 일단 euc-kr로 읽기
            soup = BeautifulSoup(response.text, 'lxml')

            # JavaScript 리다이렉트 체크 (news_read.naver 페이지)
            # <SCRIPT>top.location.href='https://n.news.naver.com/...';</SCRIPT>
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.string
                if script_text and 'top.location.href' in script_text:
                    # JavaScript에서 URL 추출
                    import re
                    match = re.search(r"top\.location\.href\s*=\s*['\"](.+?)['\"]", script_text)
                    if match:
                        redirect_url = match.group(1)
                        logger.debug(f"Found JS redirect: {redirect_url}")

                        # 리다이렉트된 URL로 다시 요청
                        response = self.get(redirect_url, referer=article.url)
                        if not response:
                            logger.warning(f"Failed to fetch redirected article: {redirect_url}")
                            return None

                        response.encoding = 'utf-8'  # n.news.naver.com은 utf-8
                        soup = BeautifulSoup(response.text, 'lxml')
                        article.url = redirect_url  # URL 업데이트
                        break

            logger.debug(f"Final URL: {article.url}")

            # 제목 재추출 (목록 페이지의 제목이 불완전할 수 있음)
            title_elem = soup.select_one('h2#title_area, h2.media_end_head_headline, .article_info h3')
            if title_elem:
                article.title = title_elem.get_text(strip=True)

            # 기사 본문 추출 (여러 패턴 시도)
            content_div = None

            # 패턴 1: 새로운 네이버 뉴스 (n.news.naver.com)
            content_div = soup.select_one('#dic_area, article#dic_area')

            # 패턴 2: 구 네이버 금융 뉴스
            if not content_div:
                content_div = soup.select_one('#articleCont, #newsContentArea, #articeBody')

            # 패턴 3: class 기반
            if not content_div:
                content_div = soup.select_one('.article_body, .articleCont, .news_end, #content')

            # 패턴 4: newsct_article (새 형식)
            if not content_div:
                content_div = soup.select_one('#newsct_article, .newsct_article')

            if content_div:
                # 광고, 스크립트, 관련기사 등 제거
                for tag in content_div.find_all(['script', 'style', 'iframe', 'ins', 'aside']):
                    tag.decompose()

                # 광고 클래스 제거
                for ad_class in content_div.find_all(class_=['ad_area', 'relacionado', 'comp_feed_wrap']):
                    ad_class.decompose()

                article.content = content_div.get_text(separator='\n', strip=True)
            else:
                logger.warning(f"No content found for article: {article.article_id}")
                article.content = ""

            # 발행 시간 추출
            # 새 형식: .media_end_head_info_datestamp_time
            time_elem = soup.select_one('.media_end_head_info_datestamp_time, .media_end_head_info time')

            # 구 형식
            if not time_elem:
                time_elem = soup.select_one('.article_date, .article_info .date, .article_header .date, .author .date')

            if time_elem:
                # data-date-time 속성 우선 (정확한 시간)
                time_attr = time_elem.get('data-date-time')
                if time_attr:
                    article.published_at = self._parse_datetime(time_attr)
                else:
                    time_text = time_elem.get_text(strip=True)
                    article.published_at = self._parse_datetime(time_text)

            # content_hash 생성
            article.content_hash = generate_content_hash(article.title, article.content or "")

            logger.debug(f"Successfully scraped article: {article.article_id}")
            return article

        except Exception as e:
            logger.error(f"Failed to fetch article content for {article.url}: {e}")
            return None

    def _parse_datetime(self, time_text: str) -> Optional[datetime]:
        """
        네이버 시간 형식을 datetime 객체로 변환 (한국 시간대 적용)

        Args:
            time_text: 시간 문자열

        Returns:
            한국 시간대가 적용된 datetime 객체 또는 None (timezone-naive, DB 저장용)
        """
        try:
            # 불필요한 텍스트 제거
            time_text = time_text.replace('입력', '').replace('수정', '').replace('기사입력', '').strip()

            # dateutil.parser를 사용하여 자동 파싱
            parsed_dt = date_parser.parse(time_text, fuzzy=True)

            # 네이버 뉴스 시간은 기본적으로 한국 시간이므로 KST로 localize
            kst_dt = naive_to_kst(parsed_dt)

            # DB에 저장할 때는 timezone 정보 제거 (TIMESTAMP 타입용)
            return remove_timezone(kst_dt)

        except Exception as e:
            logger.debug(f"Failed to parse datetime: {time_text} - {e}")
            return None

    def scrape_with_content(self, max_articles: int = 20) -> List[NewsArticle]:
        """
        뉴스 목록을 가져온 후 각 기사의 상세 내용까지 스크래핑

        Args:
            max_articles: 스크래핑할 최대 기사 수

        Returns:
            상세 내용이 포함된 NewsArticle 리스트
        """
        logger.info(f"Starting full scrape (max {max_articles} articles)...")

        # 뉴스 목록 가져오기
        articles = self.fetch_news_list()

        if not articles:
            logger.warning("No articles found in list page")
            return []

        # 제한된 개수만 처리
        articles_to_scrape = articles[:max_articles]
        logger.info(f"Scraping content for {len(articles_to_scrape)} articles...")

        detailed_articles = []

        for i, article in enumerate(articles_to_scrape, 1):
            logger.debug(f"Processing article {i}/{len(articles_to_scrape)}: {article.article_id}")

            detailed = self.fetch_article_content(article)

            if detailed:
                detailed_articles.append(detailed)

            # 마지막 기사가 아니면 딜레이
            if i < len(articles_to_scrape):
                self.random_delay()

        logger.info(f"Scraping completed: {len(detailed_articles)}/{len(articles_to_scrape)} successful")
        return detailed_articles
