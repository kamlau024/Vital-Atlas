"""
Item pipelines for vital_atlas project.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import hashlib

from vital_atlas.utils.html_to_markdown import HTMLToMarkdownConverter
from vital_atlas.utils.metadata_extractor import MetadataExtractor
from vital_atlas.utils.change_detector import ChangeDetector


class MetadataExtractionPipeline:
    """
    Extract metadata from the scraped pages.
    """

    def __init__(self):
        self.metadata_extractor = MetadataExtractor()

    def process_item(self, item, spider):
        """Process item to extract metadata."""
        # Metadata is already extracted in the spider
        # This pipeline can do additional processing if needed
        return item


class HtmlToMarkdownPipeline:
    """
    Convert HTML content to Markdown format.
    """

    def __init__(self):
        self.converter = HTMLToMarkdownConverter(use_html2text=True)

    def process_item(self, item, spider):
        """Convert HTML content to Markdown."""
        if 'content_html' in item and item['content_html']:
            spider.logger.info(f"Converting HTML to Markdown for: {item.get('url', 'unknown')}")
            item['content_markdown'] = self.converter.convert_with_cleanup(item['content_html'])

        return item


class FileStoragePipeline:
    """
    Save scraped articles as Markdown files with metadata.
    """

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.metadata_dir = self.data_dir / 'metadata'
        self.articles_dir = self.data_dir / 'articles'
        self.change_detector = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            data_dir=crawler.settings.get('SCRAPED_DATA_DIR', '../scraped_data')
        )

    def open_spider(self, spider):
        """Create directories when spider opens."""
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.change_detector = ChangeDetector(str(self.metadata_dir))
        spider.logger.info(f"Saving articles to: {self.articles_dir}")
        spider.logger.info(f"Saving metadata to: {self.metadata_dir}")

        # Log statistics
        stats = self.change_detector.get_statistics()
        spider.logger.info(f"Total articles in index: {stats['total_articles']}")

    def process_item(self, item, spider):
        """Save item to file."""
        url = item['url']

        # Check if this is a new article or has changed
        content_markdown = item.get('content_markdown', '')
        content_hash = self.change_detector.compute_content_hash(content_markdown)

        is_new = self.change_detector.is_new_article(url)
        content_changed = self.change_detector.has_content_changed(url, content_hash)
        metadata_changed = self.change_detector.has_metadata_changed(url, item)

        has_changed = content_changed or metadata_changed

        # Generate file path based on URL structure
        file_path = self._generate_file_path(item['url'])
        item['file_path'] = str(file_path)

        # Save markdown file with frontmatter
        self._save_markdown_with_frontmatter(item, file_path)

        # Save separate metadata JSON file
        self._save_metadata(item, file_path)

        # Record in change detector
        self.change_detector.record_article(
            url=url,
            content_hash=content_hash,
            metadata=item,
            file_path=str(file_path),
            is_new=is_new,
            has_changed=has_changed
        )

        if is_new:
            spider.logger.info(f"[NEW] Saved new article: {file_path}")
        elif has_changed:
            spider.logger.info(f"[UPDATED] Saved updated article: {file_path}")
        else:
            spider.logger.info(f"[NO CHANGE] Article unchanged: {file_path}")

        return item

    def _generate_file_path(self, url):
        """
        Generate a file path based on the URL structure.

        Example:
        https://www.bccancer.bc.ca/health-info/types-of-cancer/breast-cancer
        -> articles/health-info/types-of-cancer/breast-cancer.md
        """
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]

        # Remove domain and create directory structure
        if path_parts:
            # Use the URL path to create nested directories
            *dirs, filename = path_parts
            file_dir = self.articles_dir / '/'.join(dirs)
            file_dir.mkdir(parents=True, exist_ok=True)

            # Create filename
            if not filename:
                filename = 'index'

            return file_dir / f"{filename}.md"
        else:
            # Fallback: use hash of URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            return self.articles_dir / f"article_{url_hash}.md"

    def _save_markdown_with_frontmatter(self, item, file_path):
        """
        Save markdown content with YAML frontmatter containing metadata.
        """
        frontmatter = self._generate_frontmatter(item)
        content = item.get('content_markdown', '')

        full_content = f"{frontmatter}\n\n{content}"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

    def _generate_frontmatter(self, item):
        """
        Generate YAML frontmatter for the markdown file.
        """
        lines = ["---"]

        # Escape quotes in title
        title = item.get('title', '').replace('"', '\\"')
        lines.append(f'title: "{title}"')
        lines.append(f"url: {item.get('url', '')}")
        lines.append(f"date_scraped: {item.get('date_scraped', '')}")

        if item.get('date_last_update'):
            lines.append(f"date_last_update: {item['date_last_update']}")

        if item.get('date_next_review'):
            lines.append(f"date_next_review: {item['date_next_review']}")

        if item.get('breadcrumbs'):
            lines.append("breadcrumbs:")
            for crumb in item['breadcrumbs']:
                lines.append(f"  - {crumb}")

        if item.get('images'):
            lines.append("images:")
            for img in item['images'][:10]:  # Limit to first 10 images
                lines.append(f"  - src: {img.get('src', '')}")
                if img.get('alt'):
                    img_alt = img.get('alt', '').replace('"', '\\"')
                    lines.append(f'    alt: "{img_alt}"')

        lines.append("---")

        return '\n'.join(lines)

    def _save_metadata(self, item, file_path):
        """
        Save complete metadata as a separate JSON file.
        """
        metadata_file = self.metadata_dir / f"{file_path.stem}.json"

        metadata = {
            'url': item.get('url', ''),
            'title': item.get('title', ''),
            'date_scraped': item.get('date_scraped', ''),
            'date_last_update': item.get('date_last_update'),
            'date_next_review': item.get('date_next_review'),
            'breadcrumbs': item.get('breadcrumbs', []),
            'sidebar_links': item.get('sidebar_links', []),
            'related_articles': item.get('related_articles', []),
            'images': item.get('images', []),
            'tags': item.get('tags', []),
            'file_path': str(file_path),
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
