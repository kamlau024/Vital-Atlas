"""
Utility module for converting HTML content to Markdown format.
Preserves hierarchy and structure as much as possible.
"""

import html2text
from markdownify import markdownify as md


class HTMLToMarkdownConverter:
    """
    Converts HTML content to Markdown while preserving structure.
    """

    def __init__(self, use_html2text=True):
        """
        Initialize the converter.

        Args:
            use_html2text: If True, use html2text library. Otherwise use markdownify.
        """
        self.use_html2text = use_html2text

        if use_html2text:
            self.converter = html2text.HTML2Text()
            # Configure html2text settings
            self.converter.ignore_links = False
            self.converter.ignore_images = False
            self.converter.ignore_emphasis = False
            self.converter.body_width = 0  # Don't wrap lines
            self.converter.single_line_break = False
            self.converter.mark_code = True

    def convert(self, html_content):
        """
        Convert HTML to Markdown.

        Args:
            html_content: HTML string to convert

        Returns:
            Markdown string
        """
        if not html_content:
            return ""

        if self.use_html2text:
            return self.converter.handle(html_content)
        else:
            return md(
                html_content,
                heading_style="ATX",  # Use # for headings
                bullets="-",  # Use - for unordered lists
                strong_em_symbol="**",  # Use ** for bold
                strip=['script', 'style'],  # Remove script and style tags
            )

    def convert_with_cleanup(self, html_content):
        """
        Convert HTML to Markdown with additional cleanup.

        Args:
            html_content: HTML string to convert

        Returns:
            Cleaned Markdown string
        """
        markdown = self.convert(html_content)

        # Additional cleanup
        markdown = self._remove_excessive_newlines(markdown)
        markdown = self._clean_whitespace(markdown)

        return markdown.strip()

    @staticmethod
    def _remove_excessive_newlines(text):
        """Remove more than 2 consecutive newlines."""
        import re
        return re.sub(r'\n{3,}', '\n\n', text)

    @staticmethod
    def _clean_whitespace(text):
        """Clean up trailing whitespace on each line."""
        lines = text.split('\n')
        return '\n'.join(line.rstrip() for line in lines)
