"""
Spider for crawling Cleveland Clinic Health Library articles.
"""

import scrapy
from datetime import datetime
from bs4 import BeautifulSoup
from scrapy_playwright.page import PageMethod
import asyncio

from vital_atlas.items import ArticleItem
from vital_atlas.utils.cleveland_clinic_metadata_extractor import ClevelandClinicMetadataExtractor


class ClevelandClinicSpider(scrapy.Spider):
    """
    Spider to crawl and scrape health information articles from Cleveland Clinic.
    """

    name = "cleveland_clinic"
    allowed_domains = ["my.clevelandclinic.org"]

    start_urls = [
        "https://my.clevelandclinic.org/health"
    ]

    custom_settings = {
        'SCRAPED_DATA_DIR': '../scraped_data/cleveland-clinic',
        'DOWNLOAD_DELAY': 1,  # Be polite
        'PLAYWRIGHT_MAX_PAGES_PER_CONTEXT': 3,
        'HTTPCACHE_ENABLED': False,

        # Timeout and retry settings
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 30000,  # 30 seconds
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],

        # Concurrent requests
        'CONCURRENT_REQUESTS': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }

    def __init__(self, *args, **kwargs):
        super(ClevelandClinicSpider, self).__init__(*args, **kwargs)
        self.metadata_extractor = ClevelandClinicMetadataExtractor()
        self.visited_urls = set()
        self.failed_urls = {}

        # If url argument provided via -a url=..., override start_urls
        if hasattr(self, 'url') and self.url:
            self.start_urls = [self.url]
            self.logger.info(f"Overriding start_urls with: {self.url}")

    async def start(self):
        """
        Generate initial requests with Playwright.
        """
        for url in self.start_urls:
            self.logger.info(f"Start request for {url}")

            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                },
                callback=self.parse_index,
                errback=self.errback_close_page,
            )

    async def parse_index(self, response):
        """
        Parse the main index page and make POST requests to get article links for each letter.
        """
        page = response.meta.get("playwright_page")
        if page:
            await page.close()

        self.logger.info(f"Processing alphabetical index: {response.url}")

        # Letters to iterate through
        letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ['#']  # # for numbers

        # Make POST requests to AJAX endpoint for each letter
        for letter in letters:
            self.logger.info(f"Requesting articles for letter: {letter}")

            yield scrapy.FormRequest(
                url='https://my.clevelandclinic.org/AtoZ/HealthInformationPages',
                formdata={
                    'letter': letter,
                    'type': '',
                    'instituteId': ''
                },
                callback=self.parse_ajax_response,
                meta={'letter': letter},
                dont_filter=True
            )

    def parse_ajax_response(self, response):
        """
        Parse the AJAX response containing article links for a specific letter.
        The response is JSON, not HTML.
        """
        letter = response.meta.get('letter', '?')

        try:
            # Parse JSON response
            articles = response.json()

            if articles:
                self.logger.info(f"Found {len(articles)} articles for letter {letter}")

                # Follow all discovered article links
                for article in articles:
                    url = article.get('url')
                    if not url:
                        continue

                    normalized_url = self._normalize_url(url)

                    if normalized_url not in self.visited_urls:
                        self.visited_urls.add(normalized_url)
                        yield scrapy.Request(
                            normalized_url,
                            meta={
                                "playwright": True,
                                "playwright_include_page": True,
                                "playwright_page_methods": [
                                    PageMethod("wait_for_load_state", "domcontentloaded"),
                                ],
                                "playwright_page_goto_kwargs": {
                                    "wait_until": "domcontentloaded",
                                    "timeout": 30000,  # 30 seconds - faster timeout
                                },
                            },
                            callback=self.parse_article,
                            errback=self.errback_close_page,
                            dont_filter=True
                        )
            else:
                self.logger.debug(f"No articles found for letter {letter}")

        except Exception as e:
            self.logger.error(f"Error parsing AJAX response for letter {letter}: {e}")

    async def parse_article(self, response):
        """
        Parse an individual article page and extract content and metadata.
        Also extract and follow links to other articles.
        """
        page = response.meta.get("playwright_page")
        if page:
            await page.close()

        self.logger.info(f"Scraping article: {response.url}")

        # Create item
        item = ArticleItem()

        # Basic info
        item['url'] = response.url
        item['date_scraped'] = datetime.now().isoformat()

        # Extract title
        item['title'] = self.metadata_extractor.extract_title(response)

        # Extract main content
        item['content_html'] = self._extract_main_content(response)

        # Extract metadata
        dates = self.metadata_extractor.extract_dates(response)
        item['date_last_update'] = dates.get('last_update')
        item['date_next_review'] = dates.get('next_review')

        # Extract breadcrumbs and categories
        item['breadcrumbs'] = self.metadata_extractor.extract_categories(response)
        item['sidebar_links'] = self.metadata_extractor.extract_sidebar_links(response)
        item['images'] = self.metadata_extractor.extract_images(response)

        # Related articles
        item['related_articles'] = self._extract_related_articles(response)

        # Additional metadata
        item['page_type'] = self._determine_page_type(response.url)
        item['tags'] = []

        yield item

        # NOTE: We don't need to follow links from article pages because we already
        # get ALL article URLs from the AJAX alphabetical index (parse_ajax_response).
        # Following links here can cause hanging issues and is redundant.

    def _extract_main_content(self, response):
        """
        Extract the main content area of the page.
        Cleveland Clinic uses div.container for main article content.
        """
        # Try to find the main content container
        # Look for div with "container" class that contains substantial content
        containers = response.css('div.container')

        # Find the container with the most text content
        best_container = None
        max_length = 0

        for container in containers:
            text = container.css('::text').getall()
            text_length = len(''.join(text))
            if text_length > max_length:
                max_length = text_length
                best_container = container.get()

        # Require at least 500 characters to be considered valid content
        if best_container and max_length > 500:
            soup = BeautifulSoup(best_container, 'html.parser')

            # Remove navigation, ads, and other non-content elements
            for selector in [
                'nav',
                '.advertisement',
                '.ad-container',
                '.social-share',
                'script',
                'style'
            ]:
                for element in soup.select(selector):
                    element.decompose()

            return str(soup)

        self.logger.warning(f"No main content found for: {response.url} (max length: {max_length})")
        return ""

    def _extract_related_articles(self, response):
        """
        Extract links to related articles.
        """
        related = []

        # Look for related article sections
        selectors = [
            '.related-articles a',
            '[class*="related"] a',
            '.more-info a'
        ]

        for selector in selectors:
            items = response.css(selector)
            for item in items:
                text = item.css('::text').get('').strip()
                url = item.css('::attr(href)').get('')
                if text and url and self._is_health_article(url):
                    related.append({
                        'text': text,
                        'url': response.urljoin(url)
                    })

        # Remove duplicates
        seen = set()
        unique_related = []
        for article in related:
            article_tuple = (article['text'], article['url'])
            if article_tuple not in seen:
                seen.add(article_tuple)
                unique_related.append(article)

        return unique_related

    def _is_health_article(self, url):
        """
        Check if URL is a Cleveland Clinic health article.
        """
        return 'my.clevelandclinic.org/health' in url and url != 'https://my.clevelandclinic.org/health'

    def _normalize_url(self, url):
        """
        Normalize URL by removing fragments to avoid duplicate crawling.
        """
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Empty fragment
        ))
        return normalized

    async def errback_close_page(self, failure):
        """
        Handle errors and close Playwright page with intelligent retry logic.
        """
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()

        url = failure.request.url
        error_msg = str(failure.value)

        # Check if this is a timeout error
        is_timeout = "Timeout" in error_msg or "timeout" in error_msg

        # Track retry attempts
        retry_count = self.failed_urls.get(url, 0)
        max_retries = 3

        if is_timeout and retry_count < max_retries:
            self.failed_urls[url] = retry_count + 1
            self.logger.warning(
                f"Timeout on {url} (attempt {retry_count + 1}/{max_retries}). "
                f"Retrying with longer timeout..."
            )

            # Retry with increased timeout
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                    "playwright_page_goto_kwargs": {
                        "timeout": 90000,  # 90 seconds for retries
                    },
                },
                callback=failure.request.callback,
                errback=self.errback_close_page,
                dont_filter=True,
                priority=5
            )
        else:
            # Log persistent failures
            if retry_count >= max_retries:
                self.logger.error(
                    f"Failed {url} after {max_retries} retries. "
                    f"Last error: {error_msg}"
                )
            else:
                self.logger.error(f"Error processing {url}: {error_msg}")

    def closed(self, reason):
        """
        Called when the spider closes. Report any failed URLs.
        """
        if self.failed_urls:
            self.logger.warning(f"\n{'='*80}")
            self.logger.warning(f"Spider closed: {reason}")
            self.logger.warning(f"Failed to scrape {len(self.failed_urls)} URLs after retries:")
            self.logger.warning(f"{'='*80}")
            for url, retry_count in sorted(self.failed_urls.items()):
                if retry_count >= 3:
                    self.logger.warning(f"  - {url} ({retry_count} attempts)")
            self.logger.warning(f"{'='*80}\n")
        else:
            self.logger.info(f"Spider closed successfully with no failures: {reason}")

    def _determine_page_type(self, url):
        """
        Determine the type of page based on URL.
        """
        if '/diseases/' in url:
            return 'disease'
        elif '/diagnostics/' in url:
            return 'diagnostic'
        elif '/treatments/' in url:
            return 'treatment'
        elif '/symptoms/' in url:
            return 'symptom'
        elif '/body/' in url:
            return 'body-system'
        else:
            return 'general'
