"""
CCS-specific HTML to Markdown converter.

Canadian Cancer Society pages have simpler structure than BC Cancer,
so we skip most of the BC-specific cleanup methods.
"""

from vital_atlas.utils.html_to_markdown import HTMLToMarkdownConverter


class CCSHTMLToMarkdownConverter(HTMLToMarkdownConverter):
    """
    HTML to Markdown converter for cancer.ca content.

    Simpler than BC Cancer - no tabs, accordions, or complex structure.
    """

    def convert_with_cleanup(self, html_content, base_url=None):
        """
        Convert HTML to Markdown with minimal cleanup.

        Cancer.ca has standard HTML structure, so we only need:
        - Convert relative URLs to absolute
        - Clean up whitespace
        - Remove excessive newlines

        We skip BC Cancer-specific cleanup like:
        - Tab content markers
        - Accordion heading promotion
        - TOC removal (done in spider)

        Args:
            html_content: HTML string to convert
            base_url: Base URL for resolving relative links (optional)

        Returns:
            Cleaned Markdown string
        """
        markdown = self.convert(html_content, base_url)

        # Only basic cleanup
        markdown = self._remove_excessive_newlines(markdown)
        markdown = self._clean_whitespace(markdown)

        return markdown.strip()
