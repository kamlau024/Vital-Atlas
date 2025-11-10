"""
Spider for crawling Canadian Cancer Society health information articles.
"""

import scrapy
from datetime import datetime
from bs4 import BeautifulSoup
from scrapy_playwright.page import PageMethod
import asyncio

from vital_atlas.items import ArticleItem
from vital_atlas.utils.ccs_metadata_extractor import CCSMetadataExtractor


class CanadianCancerSocietySpider(scrapy.Spider):
    """
    Spider to crawl and scrape health information articles from cancer.ca
    """

    name = "canadian_cancer_society"
    allowed_domains = ["cancer.ca"]

    # Start from the three main sections
    start_urls = [
        "https://cancer.ca/en/cancer-information",
        "https://cancer.ca/en/treatments",
        "https://cancer.ca/en/living-with-cancer"
    ]

    custom_settings = {
        'SCRAPED_DATA_DIR': '../scraped_data/canadian-cancer-society',
        'DOWNLOAD_DELAY': 1,  # Be polite to cancer.ca
        'PLAYWRIGHT_MAX_PAGES_PER_CONTEXT': 5,
        'HTTPCACHE_ENABLED': False,  # Disable cache to ensure Playwright pages load properly
    }

    def __init__(self, *args, **kwargs):
        super(CanadianCancerSocietySpider, self).__init__(*args, **kwargs)
        self.metadata_extractor = CCSMetadataExtractor()
        self.visited_urls = set()
        self.alphabetical_lists_processed = set()  # Track processed alphabetical lists

        # If url argument provided via -a url=..., override start_urls
        if hasattr(self, 'url') and self.url:
            self.start_urls = [self.url]
            self.logger.info(f"Overriding start_urls with: {self.url}")

    async def start(self):
        """
        Generate initial requests with Playwright.
        If the URL looks like an article, go directly to parse_article.
        """
        for url in self.start_urls:
            # If URL looks like an article, go directly to parse_article
            is_article = self._is_article_url(url)
            callback = self.parse_article if is_article else self.parse

            self.logger.info(f"Start request for {url}: is_article={is_article}, callback={callback.__name__}")

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
        Parse pages and discover article links.
        """
        page = response.meta.get("playwright_page")

        self.logger.info(f"Parsing: {response.url}")

        # Check if this is a page with alphabetical list (dynamic content)
        if self._has_alphabetical_list(response):
            self.logger.info(f"Found alphabetical list page: {response.url}")

            if page:
                # We have Playwright - handle scrolling inline
                self.alphabetical_lists_processed.add(response.url)
                async for item in self._handle_alphabetical_list(page, response):
                    yield item
                await page.close()
                return
            else:
                # No Playwright page (likely cached) - request with Playwright
                if response.url not in self.alphabetical_lists_processed:
                    self.alphabetical_lists_processed.add(response.url)
                    self.logger.info(f"Re-requesting with Playwright for alphabetical list: {response.url}")
                    yield scrapy.Request(
                        response.url,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_methods": [
                                PageMethod("wait_for_load_state", "networkidle"),
                            ],
                        },
                        callback=self.parse,
                        errback=self.errback_close_page,
                        dont_filter=True,
                        priority=10  # Higher priority for alphabetical lists
                    )
                return

        # Check if this is a content page (not just navigation)
        if self._is_article_url(response.url):
            # This is a content page - scrape it via parse_article
            if page:
                await page.close()
            yield scrapy.Request(
                response.url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                },
                callback=self.parse_article,
                errback=self.errback_close_page,
                dont_filter=True
            )
            return

        if page:
            await page.close()

        # Extract all links within the target sections for further crawling
        links = response.css('a::attr(href)').getall()

        for link in links:
            full_url = response.urljoin(link)

            # Only follow links within our target sections
            if self._is_target_section(full_url) and full_url not in self.visited_urls:
                self.visited_urls.add(full_url)

                # All pages go through parse to check for alphabetical lists
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
                    dont_filter=True
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

    def _extract_main_content(self, response):
        """
        Extract the main content area of the page.

        Cancer.ca has clean structure:
        - <main id="main-content"> contains everything
        - Remove breadcrumbs, card navigation, and print buttons
        """
        main = response.css('main#main-content').get()

        if not main:
            self.logger.warning(f"No main content found for: {response.url}")
            return ""

        soup = BeautifulSoup(main, 'html.parser')

        # Remove navigation elements, donation blocks, and newsletter signup
        for selector in [
            '.breadcrumb',  # Breadcrumb navigation
            '.breadcrumb__print',  # Print button
            '.cards-with-cta-list',  # Card-based navigation (index pages)
            '.frup-block',  # Fundraising/donation block
            '.newsletter-signup',  # Newsletter signup section
            '.qualtrics-rating__container',  # Page rating/feedback widget
            'nav',  # Any nav elements
        ]:
            for element in soup.select(selector):
                element.decompose()

        # Process toggle-tip elements - extract and format definitions
        self._process_toggle_tips(soup)

        # Merge fragmented paragraphs caused by toggle-tips
        self._merge_fragmented_paragraphs(soup)

        return str(soup)

    def _merge_fragmented_paragraphs(self, soup):
        """
        Merge fragmented paragraphs caused by toggle-tip divs breaking paragraph flow.

        Pattern:
        <p>text </p><span>more</span> text <span>more</span>.

        Becomes:
        <p>text <span>more</span> text <span>more</span>.</p>
        """
        # Find all p tags (both with and without class="p")
        # Glossary pages use class="p", regular articles use plain <p>
        for p in soup.find_all('p'):
            # Collect inline siblings after this paragraph
            siblings_to_merge = []
            current = p.next_sibling

            while current:
                # Check if it's a text node
                if isinstance(current, str):
                    # Include any text (even whitespace) to preserve formatting
                    siblings_to_merge.append(current)
                    current = current.next_sibling
                # Check if it's an element
                elif hasattr(current, 'name'):
                    # Stop if we hit another block-level element
                    if current.name in ['p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'hr']:
                        break
                    # Collect inline elements (spans, etc.)
                    if current.name == 'span':
                        siblings_to_merge.append(current)
                        current = current.next_sibling
                    else:
                        break
                else:
                    break

            # Move collected siblings into the paragraph
            for sibling in siblings_to_merge:
                # Extract the element from its current position
                extracted = sibling.extract() if hasattr(sibling, 'extract') else sibling
                # Append to the paragraph
                p.append(extracted)

    def _process_toggle_tips(self, soup):
        """
        Process toggle-tip elements by extracting definitions and formatting them.

        After JavaScript renders the page, toggle-tips become:
        <div class="toggle-tip">
            <span class="toggle-tip__open">term</span>
            <div class="toggle-tip__modal">...</div>
        </div>

        Replaces toggle-tip divs with their text content and appends
        formatted definitions at the end of the content.
        """
        # Find all rendered toggle-tip divs
        toggle_tips = soup.find_all('div', class_='toggle-tip')

        if not toggle_tips:
            return

        # Collect definitions
        definitions = []

        for tip_div in toggle_tips:
            # Get the term text from the toggle-tip__open span
            term_span = tip_div.find('span', class_='toggle-tip__open')
            if not term_span:
                term_span = tip_div.find(class_=lambda x: x and 'toggle-tip__open' in x)

            term_text = term_span.get_text(strip=True) if term_span else tip_div.get_text(strip=True)

            # Get the modal/dialog content
            modal = tip_div.find('div', class_='toggle-tip__dialog')
            if not modal:
                modal = tip_div.find('div', class_='toggle-tip__modal')

            if modal:
                # Extract paragraphs from the modal
                paragraphs = []
                for p in modal.find_all('p', class_='p'):
                    # Use separator=' ' to preserve spaces around inline elements like <a> tags
                    p_text = p.get_text(separator=' ', strip=True)
                    if p_text:
                        paragraphs.append(p_text)

                if paragraphs:
                    definitions.append({
                        'title': term_text,
                        'paragraphs': paragraphs
                    })

            # Replace the toggle-tip div with an inline span to preserve text flow
            span = soup.new_tag('span')
            span.string = term_text
            tip_div.replace_with(span)

        # If we have definitions, append them to the content
        if definitions:
            # Find the main content container
            main_content = soup.find('main') or soup.find('div', class_='wysiwyg')

            if main_content:
                # Add a separator
                separator = soup.new_tag('hr')
                main_content.append(separator)

                # Add each definition
                for defn in definitions:
                    # Create definition heading
                    heading = soup.new_tag('p')
                    strong = soup.new_tag('strong')
                    strong.string = f"{defn['title']}:"
                    heading.append(strong)
                    main_content.append(heading)

                    # Add definition paragraphs as regular paragraphs
                    for para_text in defn['paragraphs']:
                        p = soup.new_tag('p')
                        p.string = para_text
                        main_content.append(p)

                    # Add spacing
                    br = soup.new_tag('br')
                    main_content.append(br)

    def _extract_related_articles(self, response):
        """
        Extract links to related articles from the main content.
        """
        related = []

        # Look for related article sections in main content
        main = response.css('main#main-content')
        selectors = [
            '.related-articles a',
            '[class*="related"] a',
        ]

        for selector in selectors:
            items = main.css(selector)
            for item in items:
                text = item.css('::text').get('').strip()
                url = item.css('::attr(href)').get('')
                if text and url and self._is_target_section(url):
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

    def _is_target_section(self, url):
        """
        Check if URL is within our target sections.
        """
        target_sections = [
            '/en/cancer-information',
            '/en/treatments',
            '/en/living-with-cancer'
        ]
        return any(section in url for section in target_sections)

    def _is_article_url(self, url):
        """
        Determine if a URL points to a content page vs a navigation page.

        Strategy: Use URL depth, but exclude special pages like glossary.
        - Navigation pages have 2-3 path segments
        - Content pages have 3-4+ path segments
        - Exception: glossary pages are navigation pages with dynamic lists

        Examples:
        - Navigation: /en/living-with-cancer (2 segments: living-with-cancer)
        - Navigation: /en/living-with-cancer/coping-with-changes (3 segments)
        - Navigation: /en/cancer-information/resources/glossary (special case)
        - Content: /en/living-with-cancer/coping-with-changes/newly-diagnosed (4 segments)
        - Content: /en/cancer-information/resources/glossary/w/wart (glossary entry)

        Returns:
            True if this looks like a content page
        """
        path = url.split('cancer.ca')[-1]
        # Remove /en/ and split by /
        segments = [s for s in path.split('/') if s and s != 'en']

        # Glossary index page is not an article (but glossary entries are)
        if '/resources/glossary' in url and len(segments) == 3:
            # This is the glossary index page
            return False

        # Content pages have 3+ segments
        # e.g., cancer-information/cancer-types/breast
        return len(segments) >= 3

    def _has_alphabetical_list(self, response):
        """
        Check if the page has an alphabetical list with dynamic content.
        Checks for both .alphabetical-list__results and .alphabetical-list classes.
        """
        return bool(response.css('.alphabetical-list__results, .alphabetical-list').get())

    async def _handle_alphabetical_list(self, page, response):
        """
        Handle pages with alphabetical lists (dynamic content that loads on scroll).

        Uses incremental capture strategy because the list uses virtualization:
        - Only a fixed number of items are in the DOM at any time
        - As you scroll, old items are removed and new ones are added
        - We must capture links incrementally during scrolling, not at the end

        Args:
            page: Playwright page object
            response: Scrapy response object

        Yields:
            Scrapy requests for discovered links
        """
        self.logger.info(f"Loading dynamic content for: {response.url}")

        # Track all discovered links across scrolls
        all_links = set()

        # Scroll incrementally and capture links at each position
        scroll_attempts = 0
        max_scrolls = 100  # Increase limit since we're doing incremental scrolls
        no_new_links_count = 0
        max_no_new = 5  # Stop after 5 scrolls with no new links

        scroll_step = 500  # Scroll 500px at a time

        while scroll_attempts < max_scrolls and no_new_links_count < max_no_new:
            # Get current links at this scroll position
            content = await page.content()
            from scrapy import Selector
            current_response = Selector(text=content)

            # Extract links from the alphabetical list at current scroll position
            current_links = current_response.css('.alphabetical-list__results a::attr(href)').getall()
            if not current_links:
                current_links = current_response.css('.alphabetical-list a::attr(href)').getall()

            # Track new links found
            links_before = len(all_links)
            all_links.update(current_links)
            new_links_found = len(all_links) - links_before

            if new_links_found > 0:
                self.logger.info(f"Scroll {scroll_attempts}: Found {new_links_found} new links (total: {len(all_links)})")
                no_new_links_count = 0
            else:
                no_new_links_count += 1
                self.logger.debug(f"Scroll {scroll_attempts}: No new links ({no_new_links_count}/{max_no_new})")

            # Scroll down by scroll_step pixels
            await page.evaluate(f"window.scrollBy(0, {scroll_step})")

            # Wait for content to potentially update
            await asyncio.sleep(0.5)

            scroll_attempts += 1

        self.logger.info(f"Captured {len(all_links)} total links from alphabetical list after {scroll_attempts} scrolls")

        # Follow all the discovered links
        for link in all_links:
            full_url = response.urljoin(link)

            if self._is_target_section(full_url) and full_url not in self.visited_urls:
                self.visited_urls.add(full_url)

                # These are content pages, scrape them
                yield scrapy.Request(
                    full_url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "domcontentloaded"),
                        ],
                    },
                    callback=self.parse_article,
                    errback=self.errback_close_page,
                    dont_filter=True
                )

    async def errback_close_page(self, failure):
        """
        Handle errors and close Playwright page.
        """
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()

        self.logger.error(f"Error processing {failure.request.url}: {failure.value}")

    def _determine_page_type(self, url):
        """
        Determine the type of page based on URL.
        """
        if '/cancer-information/' in url:
            if '/cancer-types/' in url:
                return 'cancer-type'
            return 'cancer-information'
        elif '/treatments/' in url:
            if '/treatment-types/' in url:
                return 'treatment-type'
            return 'treatment-information'
        elif '/living-with-cancer/' in url:
            return 'living-with-cancer'
        else:
            return 'general'
