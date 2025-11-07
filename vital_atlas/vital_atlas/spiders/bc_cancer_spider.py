"""
Spider for crawling BC Cancer health information articles.
"""

import scrapy
from datetime import datetime
from scrapy_playwright.page import PageMethod

from vital_atlas.items import ArticleItem
from vital_atlas.utils.metadata_extractor import MetadataExtractor


class BCCancerSpider(scrapy.Spider):
    """
    Spider to crawl and scrape health information articles from bccancer.bc.ca
    """

    name = "bc_cancer"
    allowed_domains = ["bccancer.bc.ca"]

    # Start from the health-info section
    start_urls = ["https://www.bccancer.bc.ca/health-info"]

    custom_settings = {
        'PLAYWRIGHT_MAX_PAGES_PER_CONTEXT': 5,
    }

    def __init__(self, *args, **kwargs):
        super(BCCancerSpider, self).__init__(*args, **kwargs)
        self.metadata_extractor = MetadataExtractor()
        self.visited_urls = set()

    async def start(self):
        """
        Generate initial requests with Playwright to render JavaScript.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                },
                callback=self.parse,
                errback=self.errback_close_page,
            )

    async def parse(self, response):
        """
        Parse the main health-info page and discover article links.
        """
        page = response.meta.get("playwright_page")
        if page:
            await page.close()

        self.logger.info(f"Parsing: {response.url}")

        # Extract all links within the health-info section
        links = response.css('a::attr(href)').getall()

        for link in links:
            full_url = response.urljoin(link)

            # Only follow links within the health-info section
            if '/health-info' in full_url and full_url not in self.visited_urls:
                self.visited_urls.add(full_url)

                # Check if it looks like an article page (not just navigation)
                if self._is_article_url(full_url):
                    yield scrapy.Request(
                        full_url,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_methods": [
                                PageMethod("wait_for_load_state", "networkidle"),
                            ],
                        },
                        callback=self.parse_article,
                        errback=self.errback_close_page,
                    )
                else:
                    # It's a navigation/category page, parse for more links
                    yield scrapy.Request(
                        full_url,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_methods": [
                                PageMethod("wait_for_load_state", "networkidle"),
                            ],
                        },
                        callback=self.parse,
                        errback=self.errback_close_page,
                    )

    async def parse_article(self, response):
        """
        Parse an individual article page and extract content and metadata.
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

        # Use URL-based hierarchy as breadcrumbs (not navigation menu)
        item['breadcrumbs'] = self.metadata_extractor.extract_categories(response)
        item['sidebar_links'] = self.metadata_extractor.extract_sidebar_links(response)
        item['images'] = self.metadata_extractor.extract_images(response)

        # Extract related articles
        item['related_articles'] = self._extract_related_articles(response)

        # Additional metadata
        item['page_type'] = self._determine_page_type(response.url)
        item['tags'] = []  # Can be enhanced based on page content

        yield item

    def _extract_main_content(self, response):
        """
        Extract the main content area of the page.
        Try multiple selectors to find the main content.
        """
        # Try different content selectors
        content_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '#main-content',
            '.content',
            '#content',
        ]

        for selector in content_selectors:
            content = response.css(selector).get()
            if content:
                self.logger.debug(f"Found content with selector: {selector}")
                return content

        # Fallback: get body content
        self.logger.warning(f"Using body fallback for content extraction: {response.url}")
        return response.css('body').get()

    def _extract_related_articles(self, response):
        """
        Extract links to related articles.
        """
        related = []

        # Look for related article sections
        selectors = [
            '.related-articles a',
            '[class*="related"] a',
            'aside a',
        ]

        for selector in selectors:
            items = response.css(selector)
            for item in items:
                text = item.css('::text').get('').strip()
                url = item.css('::attr(href)').get('')
                if text and url and '/health-info' in url:
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

    def _is_article_url(self, url):
        """
        Determine if a URL points to an article page vs a navigation page.
        Simple heuristic: articles typically have more path segments.
        """
        path = url.split('bccancer.bc.ca')[-1]
        segments = [s for s in path.split('/') if s]

        # If URL has 3+ segments under health-info, likely an article
        # e.g., /health-info/types-of-cancer/breast-cancer
        return len(segments) >= 2

    def _determine_page_type(self, url):
        """
        Determine the type of page based on URL.
        """
        if '/types-of-cancer/' in url:
            return 'cancer-type'
        elif '/coping-with-cancer/' in url:
            return 'coping-support'
        elif '/screening/' in url:
            return 'screening'
        elif '/prevention/' in url:
            return 'prevention'
        elif '/adolescent-young-adult/' in url:
            return 'aya-support'
        else:
            return 'general'

    async def errback_close_page(self, failure):
        """
        Handle errors and close Playwright page.
        """
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()

        self.logger.error(f"Error processing {failure.request.url}: {failure.value}")
