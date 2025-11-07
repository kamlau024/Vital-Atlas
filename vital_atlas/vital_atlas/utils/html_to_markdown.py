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
        markdown = self._remove_page_markers(markdown)
        markdown = self._remove_empty_tab_sections(markdown)
        markdown = self._remove_excessive_newlines(markdown)
        markdown = self._clean_whitespace(markdown)

        return markdown.strip()

    @staticmethod
    def _remove_page_markers(text):
        """
        Remove page structure markers and labels that don't add content value.

        Removes:
        - "ShortPageContent"
        - "Tab Content 1", "Tab Content 2", etc.
        - "Tab Heading" (even if it has content)
        """
        import re

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            # Skip if it matches any of the page markers
            if stripped in ['ShortPageContent', 'Tab Heading']:
                continue

            # Skip if it matches "Tab Content" followed by optional space and number
            if re.match(r'^Tab Content\s*\d+$', stripped):
                continue

            # Keep this line
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @staticmethod
    def _remove_empty_tab_sections(text):
        """
        Remove empty tab headings and tab content sections.

        Removes lines like:
        - "Tab Heading" followed by empty content
        - "Tab Content 1", "Tab Content 2", etc. followed by empty content
        - Lines with just numbers after tab sections
        """
        import re

        lines = text.split('\n')
        cleaned_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a tab heading or tab content line
            is_tab_line = (
                line == "Tab Heading" or
                re.match(r'^Tab Content\s*\d*$', line)
            )

            if is_tab_line:
                # Look ahead to see if the next non-empty lines contain actual content
                has_content = False
                lookahead = i + 1
                skipped_lines = 0

                # Check the next few lines (up to 10) for actual content
                while lookahead < len(lines) and lookahead < i + 10:
                    next_line = lines[lookahead].strip()

                    # Skip empty lines
                    if not next_line:
                        lookahead += 1
                        skipped_lines += 1
                        continue

                    # Check if it's just a single digit or small number (likely pagination/navigation)
                    if re.match(r'^\d{1,2}$', next_line):
                        lookahead += 1
                        skipped_lines += 1
                        continue

                    # Check if it's another tab marker (means this tab is empty)
                    if next_line == "Tab Heading" or re.match(r'^Tab Content\s*\d*$', next_line):
                        break

                    # Check for common non-content patterns
                    if next_line in ['--', '---', '* * *']:
                        lookahead += 1
                        skipped_lines += 1
                        continue

                    # If we find text that's longer than just a few chars, it's real content
                    if len(next_line) > 3 and not re.match(r'^[\d\s\-_]+$', next_line):
                        has_content = True
                        break

                    lookahead += 1
                    skipped_lines += 1

                if not has_content:
                    # Skip this tab line and any immediately following empty lines, numbers, or separators
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if (not next_line or
                            re.match(r'^\d{1,2}$', next_line) or
                            next_line in ['--', '---', '* * *']):
                            i += 1
                        else:
                            # Check if it's another tab marker
                            if next_line == "Tab Heading" or re.match(r'^Tab Content\s*\d*$', next_line):
                                break
                            # If it's actual content, we went too far - step back
                            if len(next_line) > 3:
                                break
                            i += 1
                    continue

            # Keep this line
            cleaned_lines.append(lines[i])
            i += 1

        return '\n'.join(cleaned_lines)

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
