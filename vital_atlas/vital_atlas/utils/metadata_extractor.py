"""
Utility module for extracting metadata from web pages.
"""

from datetime import datetime
import re
from typing import Dict, List, Optional


class MetadataExtractor:
    """
    Extracts metadata from HTML responses.
    """

    @staticmethod
    def extract_breadcrumbs(response) -> List[Dict[str, str]]:
        """
        Extract breadcrumb navigation from the page.

        Returns:
            List of dicts with 'text' and 'url' keys
        """
        breadcrumbs = []

        # Try common breadcrumb selectors
        selectors = [
            'nav[aria-label="breadcrumb"] a',
            '.breadcrumb a',
            '[class*="breadcrumb"] a',
            'ol.breadcrumb a',
        ]

        for selector in selectors:
            items = response.css(selector)
            if items:
                for item in items:
                    breadcrumbs.append({
                        'text': item.css('::text').get('').strip(),
                        'url': item.css('::attr(href)').get('')
                    })
                break

        return breadcrumbs

    @staticmethod
    def extract_sidebar_links(response) -> List[Dict[str, str]]:
        """
        Extract links from sidebar or related content areas.

        Returns:
            List of dicts with 'text' and 'url' keys
        """
        links = []

        # Try common sidebar selectors
        selectors = [
            'aside a',
            '[class*="sidebar"] a',
            '[class*="related"] a',
            '[id*="sidebar"] a',
            'nav[class*="side"] a',
        ]

        for selector in selectors:
            items = response.css(selector)
            if items:
                for item in items:
                    text = item.css('::text').get('').strip()
                    url = item.css('::attr(href)').get('')
                    if text and url:
                        links.append({
                            'text': text,
                            'url': response.urljoin(url)
                        })

        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            link_tuple = (link['text'], link['url'])
            if link_tuple not in seen:
                seen.add(link_tuple)
                unique_links.append(link)

        return unique_links

    @staticmethod
    def extract_images(response) -> List[Dict[str, str]]:
        """
        Extract all images from the page.

        Returns:
            List of dicts with 'src', 'alt', and 'title' keys
        """
        images = []

        for img in response.css('img'):
            src = img.css('::attr(src)').get('')
            alt = img.css('::attr(alt)').get('')
            title = img.css('::attr(title)').get('')

            if src:
                images.append({
                    'src': response.urljoin(src),
                    'alt': alt,
                    'title': title
                })

        return images

    @staticmethod
    def extract_dates(response) -> Dict[str, Optional[str]]:
        """
        Extract date metadata from the page.

        Returns:
            Dict with 'last_update' and 'next_review' keys
        """
        dates = {
            'last_update': None,
            'next_review': None
        }

        # Look for date patterns in the page
        text = response.text

        # Try to find "Last updated" or "Last modified" dates
        last_update_patterns = [
            r'Last\s+(?:Updated|Modified|Reviewed):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?:Updated|Modified|Reviewed):\s*(\d{4}-\d{2}-\d{2})',
            r'Date\s+(?:Updated|Modified):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        ]

        for pattern in last_update_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates['last_update'] = match.group(1)
                break

        # Try to find "Next review" dates
        next_review_patterns = [
            r'Next\s+Review:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'Next\s+Review:\s*(\d{4}-\d{2}-\d{2})',
            r'Review\s+Date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        ]

        for pattern in next_review_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates['next_review'] = match.group(1)
                break

        # Also try meta tags
        if not dates['last_update']:
            last_modified = response.css('meta[property="article:modified_time"]::attr(content)').get()
            if not last_modified:
                last_modified = response.css('meta[name="last-modified"]::attr(content)').get()
            dates['last_update'] = last_modified

        return dates

    @staticmethod
    def extract_title(response) -> str:
        """
        Extract the page title.

        Returns:
            Page title string
        """
        # Try different title selectors in order of preference
        title = response.css('h1::text').get()

        if not title:
            title = response.css('title::text').get()

        if not title:
            title = response.css('meta[property="og:title"]::attr(content)').get()

        return (title or '').strip()

    @staticmethod
    def extract_categories(response) -> List[str]:
        """
        Extract category information from the page.

        Returns:
            List of category strings
        """
        categories = []

        # Try to extract from breadcrumbs
        breadcrumbs = MetadataExtractor.extract_breadcrumbs(response)
        categories = [bc['text'] for bc in breadcrumbs if bc['text']]

        # Also try meta tags
        meta_categories = response.css('meta[property="article:section"]::attr(content)').getall()
        categories.extend(meta_categories)

        # Try to extract from URL path
        url_parts = response.url.split('/')
        for part in url_parts:
            if part and part not in ['http:', 'https:', '', 'www.bccancer.bc.ca']:
                categories.append(part.replace('-', ' ').title())

        # Remove duplicates
        return list(dict.fromkeys(categories))
