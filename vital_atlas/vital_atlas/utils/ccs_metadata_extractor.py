"""
Utility module for extracting metadata from Canadian Cancer Society web pages.
"""

from datetime import datetime
import re
from typing import Dict, List, Optional


class CCSMetadataExtractor:
    """
    Extracts metadata from cancer.ca HTML responses.
    """

    @staticmethod
    def extract_breadcrumbs(response) -> List[Dict[str, str]]:
        """
        Extract breadcrumb navigation from the page.

        Returns:
            List of dicts with 'text' and 'url' keys
        """
        breadcrumbs = []

        # cancer.ca uses schema.org breadcrumbs
        # <ol class="breadcrumb__list" itemscope itemtype="https://schema.org/BreadcrumbList">
        breadcrumb_items = response.css('ol.breadcrumb__list li.breadcrumb__item')

        for item in breadcrumb_items:
            text = item.css('span.breadcrumb__text::text').get()
            url = item.css('a.breadcrumb__link::attr(href)').get()

            if text:
                breadcrumbs.append({
                    'text': text.strip(),
                    'url': response.urljoin(url) if url else ''
                })

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
        Extract all images from the main content area.

        Returns:
            List of dicts with 'src', 'alt', and 'title' keys
        """
        images = []

        # Only extract from main content, not navigation
        main = response.css('main#main-content')
        if not main:
            return images

        for img in main.css('img'):
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

        Note: cancer.ca does not typically display last updated or review dates.

        Returns:
            Dict with 'last_update' and 'next_review' keys (usually None)
        """
        dates = {
            'last_update': None,
            'next_review': None
        }

        # Look for date patterns in the page (usually not present)
        text = response.text

        # Try to find "Last updated" or "Last modified" dates
        last_update_patterns = [
            r'Last\s+(?:Updated|Modified|Reviewed):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
            r'(?:Updated|Modified|Reviewed):\s*(\d{4}-\d{2}-\d{2})',
        ]

        for pattern in last_update_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates['last_update'] = match.group(1)
                break

        # Try meta tags
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
        # cancer.ca uses h1.title in the hero section
        title = response.css('h1.title::text').get()

        if not title:
            # Fallback to any h1
            title = response.css('h1::text').get()

        if not title:
            # Try page title meta tag
            title = response.css('title::text').get()

        if not title:
            # Try Open Graph title
            title = response.css('meta[property="og:title"]::attr(content)').get()

        return (title or '').strip()

    @staticmethod
    def extract_categories(response) -> List[str]:
        """
        Extract category information from the page.

        Uses URL path to derive categories.

        Returns:
            List of category strings
        """
        categories = []

        # Primary source: Extract from URL path
        # Example: /en/cancer-information/cancer-types/breast
        # Becomes: ["Cancer Information", "Cancer Types", "Breast"]
        url_path = response.url.split('?')[0]  # Remove query string
        url_parts = url_path.split('/')

        for part in url_parts:
            # Skip empty parts, protocol, domain, and language code
            if part and part not in ['http:', 'https:', '', 'cancer.ca', 'www.cancer.ca', 'en', 'fr']:
                # Convert kebab-case to Title Case
                category = part.replace('-', ' ').title()
                categories.append(category)

        # Secondary source: Use breadcrumbs
        breadcrumbs = CCSMetadataExtractor.extract_breadcrumbs(response)
        for bc in breadcrumbs:
            if bc['text'] and bc['text'] != 'Home':
                categories.append(bc['text'])

        # Remove duplicates while preserving order
        seen = set()
        unique_categories = []
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower not in seen:
                seen.add(cat_lower)
                unique_categories.append(cat)

        return unique_categories
