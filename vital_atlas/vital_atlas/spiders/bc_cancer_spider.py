"""
Spider for crawling BC Cancer health information articles.
"""

import scrapy
from datetime import datetime
from scrapy_playwright.page import PageMethod

from vital_atlas.items import ArticleItem
from vital_atlas.utils.bc_cancer_metadata_extractor import BCCancerMetadataExtractor


class BCCancerSpider(scrapy.Spider):
    """
    Spider to crawl and scrape health information articles from bccancer.bc.ca
    """

    name = "bc_cancer"
    allowed_domains = ["bccancer.bc.ca"]

    # Start from the health-info section
    start_urls = ["https://www.bccancer.bc.ca/health-info"]

    custom_settings = {
        'SCRAPED_DATA_DIR': '../scraped_data/bc-cancer',
        'PLAYWRIGHT_MAX_PAGES_PER_CONTEXT': 5,
    }

    def __init__(self, *args, **kwargs):
        super(BCCancerSpider, self).__init__(*args, **kwargs)
        self.metadata_extractor = BCCancerMetadataExtractor()
        self.visited_urls = set()

        # If url argument provided via -a url=..., override start_urls
        if hasattr(self, 'url') and self.url:
            self.start_urls = [self.url]
            self.logger.info(f"Overriding start_urls with: {self.url}")

    async def start(self):
        """
        Generate initial requests with Playwright to render JavaScript.
        If the URL looks like an article, go directly to parse_article.
        """
        for url in self.start_urls:
            # If URL looks like an article, go directly to parse_article
            callback = self.parse_article if self._is_article_url(url) else self.parse

            self.logger.info(f"Start request for {url}: is_article={self._is_article_url(url)}, callback={callback.__name__}")

            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                },
                callback=callback,
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
        Removes navigation and TOC elements that shouldn't be part of the content.
        """
        from bs4 import BeautifulSoup

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

        html_content = None
        for selector in content_selectors:
            html_content = response.css(selector).get()
            if html_content:
                self.logger.debug(f"Found content with selector: {selector}")
                break

        if not html_content:
            # Fallback: get body content
            self.logger.warning(f"Using body fallback for content extraction: {response.url}")
            html_content = response.css('body').get()

        # Clean up: remove TOC navigation elements
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove common TOC/navigation elements
        for selector in ['nav', '.ms-qcb-menu', '[class*="quicklaunch"]', '[class*="navigation"]']:
            for element in soup.select(selector):
                element.decompose()

        # Remove any list of links that only contains internal page anchors (#)
        # These are typically table of contents lists
        for ul in soup.find_all(['ul', 'ol']):
            links = ul.find_all('a')
            if links and all(link.get('href', '').startswith('#') or '#' in link.get('href', '') for link in links):
                # This is likely a TOC - remove it
                ul.decompose()

        return str(soup)

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
