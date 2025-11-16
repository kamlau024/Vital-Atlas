"""
Metadata extractor for Cleveland Clinic health articles.
"""

from datetime import datetime
import re


class ClevelandClinicMetadataExtractor:
    """
    Extracts metadata from Cleveland Clinic health article pages.
    """

    def extract_title(self, response):
        """
        Extract the article title.

        Args:
            response: Scrapy response object

        Returns:
            str: Article title
        """
        # Try h1 first
        title = response.css('h1::text').get()

        if not title:
            # Fallback to title tag
            title = response.css('title::text').get()
            if title:
                # Remove "| Cleveland Clinic" suffix
                title = title.split('|')[0].strip()

        return title.strip() if title else "Untitled"

    def extract_dates(self, response):
        """
        Extract last update and next review dates.

        Args:
            response: Scrapy response object

        Returns:
            dict: Dictionary with 'last_update' and 'next_review' keys
        """
        dates = {
            'last_update': None,
            'next_review': None
        }

        # Look for date metadata
        # Cleveland Clinic often uses meta tags or specific date elements

        # Try to find "Last reviewed" or "Updated" text
        date_text = response.css('[class*="date"]::text, [class*="updated"]::text, [class*="reviewed"]::text').getall()

        for text in date_text:
            text = text.strip()
            # Look for patterns like "Last reviewed: MM/DD/YYYY" or "Updated: Month DD, YYYY"
            if 'last reviewed' in text.lower() or 'reviewed' in text.lower():
                date_match = self._extract_date_from_text(text)
                if date_match:
                    dates['last_update'] = date_match
            elif 'updated' in text.lower():
                date_match = self._extract_date_from_text(text)
                if date_match:
                    dates['last_update'] = date_match

        # Try meta tags
        if not dates['last_update']:
            meta_date = response.css('meta[property="article:modified_time"]::attr(content)').get()
            if meta_date:
                dates['last_update'] = meta_date

        return dates

    def _extract_date_from_text(self, text):
        """
        Extract date from text string.

        Args:
            text: String containing a date

        Returns:
            str: Extracted date or None
        """
        # Common date patterns
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'[A-Za-z]+\s+\d{1,2},\s+\d{4}',  # Month DD, YYYY
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def extract_categories(self, response):
        """
        Extract breadcrumbs/categories from the page.

        Args:
            response: Scrapy response object

        Returns:
            list: List of category strings
        """
        categories = []

        # Try breadcrumb navigation
        breadcrumbs = response.css('nav[aria-label="breadcrumb"] a::text, .breadcrumb a::text').getall()

        if breadcrumbs:
            categories = [bc.strip() for bc in breadcrumbs if bc.strip()]

        # If no breadcrumbs, try to extract from URL
        if not categories:
            url_parts = response.url.split('/')
            if 'health' in url_parts:
                idx = url_parts.index('health')
                if len(url_parts) > idx + 1:
                    # Get the category from URL (diseases, diagnostics, etc.)
                    category = url_parts[idx + 1].replace('-', ' ').title()
                    categories = ['Health', category]

        return categories

    def extract_sidebar_links(self, response):
        """
        Extract links from sidebar or related content sections.

        Args:
            response: Scrapy response object

        Returns:
            list: List of dictionaries with 'text' and 'url' keys
        """
        sidebar_links = []

        # Common sidebar selectors
        selectors = [
            'aside a',
            '.sidebar a',
            '[class*="sidebar"] a',
            '[class*="related"] a'
        ]

        for selector in selectors:
            links = response.css(selector)
            for link in links:
                text = link.css('::text').get('')
                url = link.css('::attr(href)').get('')

                if text and url:
                    text = text.strip()
                    if text and 'my.clevelandclinic.org' in url:
                        sidebar_links.append({
                            'text': text,
                            'url': response.urljoin(url)
                        })

        # Remove duplicates
        seen = set()
        unique_links = []
        for link in sidebar_links:
            link_tuple = (link['text'], link['url'])
            if link_tuple not in seen:
                seen.add(link_tuple)
                unique_links.append(link)

        return unique_links

    def extract_images(self, response):
        """
        Extract all images from the article.

        Args:
            response: Scrapy response object

        Returns:
            list: List of dictionaries with image metadata
        """
        images = []

        # Extract all images from main content
        img_elements = response.css('main img, article img')

        for img in img_elements:
            src = img.css('::attr(src)').get()
            alt = img.css('::attr(alt)').get('')

            if src:
                images.append({
                    'src': response.urljoin(src),
                    'alt': alt.strip() if alt else ''
                })

        return images
