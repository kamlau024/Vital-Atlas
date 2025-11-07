"""
Utility for detecting changes in scraped content.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ChangeDetector:
    """
    Detects changes in scraped articles by comparing content hashes
    and metadata.
    """

    def __init__(self, metadata_dir: str):
        """
        Initialize the change detector.

        Args:
            metadata_dir: Directory where metadata JSON files are stored
        """
        self.metadata_dir = Path(metadata_dir)
        self.change_log_file = self.metadata_dir / 'change_log.json'
        self.url_index_file = self.metadata_dir / 'url_index.json'

        # Load existing indices
        self.url_index = self._load_url_index()
        self.change_log = self._load_change_log()

    def _load_url_index(self) -> Dict:
        """Load the URL to file mapping index."""
        if self.url_index_file.exists():
            with open(self.url_index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_change_log(self) -> List:
        """Load the change log."""
        if self.change_log_file.exists():
            with open(self.change_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_url_index(self):
        """Save the URL index."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        with open(self.url_index_file, 'w', encoding='utf-8') as f:
            json.dump(self.url_index, f, indent=2)

    def _save_change_log(self):
        """Save the change log."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        with open(self.change_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.change_log, f, indent=2)

    def compute_content_hash(self, content: str) -> str:
        """
        Compute MD5 hash of content.

        Args:
            content: Content string to hash

        Returns:
            MD5 hash string
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def is_new_article(self, url: str) -> bool:
        """
        Check if this is a new article.

        Args:
            url: Article URL

        Returns:
            True if article is new (not in index)
        """
        return url not in self.url_index

    def has_content_changed(self, url: str, new_content_hash: str) -> bool:
        """
        Check if article content has changed.

        Args:
            url: Article URL
            new_content_hash: Hash of new content

        Returns:
            True if content has changed
        """
        if url not in self.url_index:
            return True

        old_hash = self.url_index[url].get('content_hash')
        return old_hash != new_content_hash

    def has_metadata_changed(self, url: str, new_metadata: Dict) -> bool:
        """
        Check if article metadata has changed.

        Args:
            url: Article URL
            new_metadata: New metadata dict

        Returns:
            True if metadata has changed
        """
        if url not in self.url_index:
            return True

        old_metadata = self.url_index[url].get('metadata', {})

        # Check specific metadata fields
        fields_to_check = ['title', 'date_last_update', 'date_next_review']

        for field in fields_to_check:
            if old_metadata.get(field) != new_metadata.get(field):
                return True

        return False

    def record_article(self, url: str, content_hash: str, metadata: Dict, file_path: str, is_new: bool = False, has_changed: bool = False):
        """
        Record article in the index.

        Args:
            url: Article URL
            content_hash: Hash of content
            metadata: Article metadata
            file_path: Path where article is saved
            is_new: Whether this is a new article
            has_changed: Whether content/metadata has changed
        """
        self.url_index[url] = {
            'content_hash': content_hash,
            'metadata': {
                'title': metadata.get('title'),
                'date_last_update': metadata.get('date_last_update'),
                'date_next_review': metadata.get('date_next_review'),
            },
            'file_path': file_path,
            'last_scraped': datetime.now().isoformat(),
        }

        # Log the change
        if is_new:
            self._log_change('new', url, metadata.get('title'))
        elif has_changed:
            self._log_change('updated', url, metadata.get('title'))

        self._save_url_index()

    def _log_change(self, change_type: str, url: str, title: str):
        """
        Add entry to change log.

        Args:
            change_type: 'new' or 'updated'
            url: Article URL
            title: Article title
        """
        self.change_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': change_type,
            'url': url,
            'title': title,
        })

        # Keep only last 1000 changes
        if len(self.change_log) > 1000:
            self.change_log = self.change_log[-1000:]

        self._save_change_log()

    def get_recent_changes(self, limit: int = 50) -> List[Dict]:
        """
        Get recent changes.

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of recent changes
        """
        return self.change_log[-limit:]

    def get_statistics(self) -> Dict:
        """
        Get statistics about scraped articles.

        Returns:
            Dict with statistics
        """
        return {
            'total_articles': len(self.url_index),
            'total_changes_logged': len(self.change_log),
            'last_scrape_time': max(
                (item['last_scraped'] for item in self.url_index.values()),
                default=None
            ),
        }
