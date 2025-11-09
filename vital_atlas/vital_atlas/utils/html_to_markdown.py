"""
Utility module for converting HTML content to Markdown format.
Preserves hierarchy and structure as much as possible.
"""

import html2text
from markdownify import markdownify as md
from bs4 import BeautifulSoup
from urllib.parse import urljoin


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

    def convert(self, html_content, base_url=None):
        """
        Convert HTML to Markdown.

        Args:
            html_content: HTML string to convert
            base_url: Base URL for resolving relative links (optional)

        Returns:
            Markdown string
        """
        if not html_content:
            return ""

        # Convert relative URLs to absolute if base_url is provided
        if base_url:
            html_content = self._convert_relative_urls(html_content, base_url)

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

    def convert_with_cleanup(self, html_content, base_url=None):
        """
        Convert HTML to Markdown with additional cleanup.

        Args:
            html_content: HTML string to convert
            base_url: Base URL for resolving relative links (optional)

        Returns:
            Cleaned Markdown string
        """
        markdown = self.convert(html_content, base_url)

        # Additional cleanup
        markdown = self._remove_page_markers(markdown)
        # Note: _remove_empty_tab_sections is commented out as it was looking for
        # "## Tab Content N" headings which are now removed in favor of actual tab labels
        # markdown = self._remove_empty_tab_sections(markdown)
        markdown = self._promote_accordion_headings(markdown)
        markdown = self._remove_trailing_pagination(markdown)
        markdown = self._remove_excessive_newlines(markdown)
        markdown = self._clean_whitespace(markdown)

        return markdown.strip()

    @staticmethod
    def _convert_relative_urls(html_content, base_url):
        """
        Convert all relative URLs in the HTML to absolute URLs.

        Args:
            html_content: HTML string with potentially relative URLs
            base_url: Base URL to resolve relative URLs against

        Returns:
            HTML string with absolute URLs
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Convert links (href attributes)
        for tag in soup.find_all(['a', 'link']):
            if tag.has_attr('href'):
                tag['href'] = urljoin(base_url, tag['href'])

        # Convert images and other media (src attributes)
        for tag in soup.find_all(['img', 'script', 'source', 'video', 'audio', 'iframe']):
            if tag.has_attr('src'):
                tag['src'] = urljoin(base_url, tag['src'])

        # Convert srcset attributes (for responsive images)
        for tag in soup.find_all(['img', 'source']):
            if tag.has_attr('srcset'):
                srcset_parts = []
                for part in tag['srcset'].split(','):
                    part = part.strip()
                    if ' ' in part:
                        url, descriptor = part.rsplit(' ', 1)
                        srcset_parts.append(f"{urljoin(base_url, url)} {descriptor}")
                    else:
                        srcset_parts.append(urljoin(base_url, part))
                tag['srcset'] = ', '.join(srcset_parts)

        return str(soup)

    @staticmethod
    def _remove_page_markers(text):
        """
        Process page structure markers:
        - Remove: "ShortPageContent", "Tab Heading", "Tab Content N"
        - Convert tab headings (text before "Tab Content N") to ## headings

        Example:
            Input:  "Diagnosis & staging\n\nTab Content 1\n\nSome content"
            Output: "## Diagnosis & staging\n\nSome content"
        """
        import re

        lines = text.split('\n')
        cleaned_lines = []
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()

            # Skip these markers completely
            if stripped in ['ShortPageContent', 'Tab Heading']:
                i += 1
                continue

            # Check if this is "Tab Content N"
            match = re.match(r'^Tab Content\s*(\d+)$', stripped)
            if match:
                tab_num = match.group(1)
                # Found "Tab Content N" - look back for the tab heading
                # Skip over TOC/list sections to find the actual heading
                if cleaned_lines:
                    # Look backward, skipping over list items and empty lines
                    found_heading = False
                    lookback_count = 0
                    for j in range(len(cleaned_lines) - 1, -1, -1):
                        lookback_count += 1
                        if lookback_count > 20:  # Don't look back too far
                            break

                        prev_line = cleaned_lines[j].strip()

                        # Skip empty lines
                        if not prev_line:
                            continue

                        # Skip list items (likely TOC)
                        if prev_line.startswith(('* ', '- ', '+ ', '1. ', '2. ', '3. ', '4. ', '5. ')):
                            continue

                        # Skip lines that are just links in square brackets
                        if re.match(r'^\[.*\]\(.*\)$', prev_line):
                            continue

                        # Found a non-list, non-empty line - this is likely the heading
                        if not prev_line.startswith('#'):
                            # Only convert if it's reasonably short (not a paragraph)
                            if len(prev_line) < 100:
                                # Convert to level 2 heading
                                cleaned_lines[j] = f"## {prev_line}"
                                found_heading = True
                        break
                # Skip the "Tab Content N" line
                i += 1
                continue

            # Keep this line as-is
            cleaned_lines.append(lines[i])
            i += 1

        return '\n'.join(cleaned_lines)

    @staticmethod
    def _remove_empty_tab_sections(text):
        """
        Remove empty tab headings and tab content sections.

        Removes lines like:
        - "## Tab Content 1", "## Tab Content 2", etc. followed by empty content
        - Lines with just numbers after tab sections

        Note: This runs AFTER _remove_page_markers(), so tab content is already
        formatted as "## Tab Content N" headings.
        """
        import re

        lines = text.split('\n')
        cleaned_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a tab content heading (already formatted as "## Tab Content N")
            is_tab_line = re.match(r'^##\s+Tab Content\s*\d*$', line)

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

                    # Check if it's another tab heading (means this tab is empty)
                    if re.match(r'^##\s+Tab Content\s*\d*$', next_line):
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
    def _promote_accordion_headings(text):
        """
        Convert accordion section headings from level 4 (####) to level 2 (##).

        Accordion headings typically appear as level 4 headings with links containing
        anchor references (#) in the HTML. This promotes them to level 2 for better
        document structure.

        Example:
            Input:  ####  [ Types of losses](https://example.com#7515)
            Output: ##  [ Types of losses](https://example.com#7515)
        """
        import re

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Check if this is a level 4 heading with a link containing an anchor
            # Pattern: #### followed by optional spaces, then a markdown link with # in URL
            if re.match(r'^####\s+\[.*\]\(.*#.*\)', line.strip()):
                # Convert #### to ##
                line = re.sub(r'^####', '##', line)

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @staticmethod
    def _remove_trailing_pagination(text):
        """
        Remove stray pagination numbers, navigation markers, or rating numbers
        that appear at the end of the content.

        Common patterns:
        - Single digit or small number on its own line at the end
        - Numbers followed by navigation arrows or text
        - Rating numbers (e.g., "1", "2", "3", "4", "5")
        """
        import re

        lines = text.split('\n')

        # Work backwards from the end, removing problematic lines
        while lines:
            last_line = lines[-1].strip()

            # Remove if it's just a small number (likely pagination/rating)
            if re.match(r'^\d{1,2}$', last_line):
                lines.pop()
                continue

            # Remove if it's a common navigation pattern
            if re.match(r'^(\d+\s*[|/]\s*\d+|Page\s*\d+|^\d+\s*(of|/)\s*\d+)$', last_line, re.IGNORECASE):
                lines.pop()
                continue

            # Remove common separators at the end
            if last_line in ['--', '---', '* * *', '•', '|']:
                lines.pop()
                continue

            # Remove empty lines at the end
            if not last_line:
                lines.pop()
                continue

            # If we hit real content, stop
            break

        return '\n'.join(lines)

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
