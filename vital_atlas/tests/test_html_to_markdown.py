"""
Tests for HTML to Markdown conversion
"""
import pytest
from vital_atlas.utils.html_to_markdown import HTMLToMarkdownConverter


class TestHTMLToMarkdownConverter:
    """Test HTML to Markdown conversion"""

    def setup_method(self):
        """Setup test converter"""
        self.converter = HTMLToMarkdownConverter(use_html2text=True)

    def test_convert_relative_to_absolute_urls(self):
        """Test converting relative URLs to absolute"""
        html = '''
        <div>
            <a href="/relative/link">Link</a>
            <img src="/images/test.jpg" alt="Test">
        </div>
        '''
        base_url = "https://example.com/page"

        result = self.converter._convert_relative_urls(html, base_url)

        assert 'href="https://example.com/relative/link"' in result
        assert 'src="https://example.com/images/test.jpg"' in result

    def test_convert_relative_urls_with_srcset(self):
        """Test srcset attribute conversion"""
        html = '''
        <img src="/img.jpg"
             srcset="/img-sm.jpg 300w, /img-lg.jpg 600w"
             alt="Test">
        '''
        base_url = "https://example.com"

        result = self.converter._convert_relative_urls(html, base_url)

        assert 'srcset="https://example.com/img-sm.jpg 300w, https://example.com/img-lg.jpg 600w"' in result

    def test_remove_page_markers(self):
        """Test removal of ShortPageContent and Tab Heading markers"""
        text = '''
        Some content

        ShortPageContent

        Tab Heading

        More content
        '''

        result = self.converter._remove_page_markers(text)

        assert 'ShortPageContent' not in result
        assert 'Tab Heading' not in result
        assert 'Some content' in result
        assert 'More content' in result

    def test_convert_tab_content_to_heading(self):
        """Test converting tab headings to H2"""
        text = '''
        Expressing anger

        Tab Content 1

        Some content about anger
        '''

        result = self.converter._remove_page_markers(text)

        assert '## Expressing anger' in result
        assert 'Tab Content 1' not in result
        assert 'Some content about anger' in result

    def test_promote_accordion_headings(self):
        """Test promoting accordion headings from #### to ##"""
        text = '''####  [ Types of losses](https://example.com#section1)

Content here

####  [ Moving forward](https://example.com#section2)

More content'''

        result = self.converter._promote_accordion_headings(text)

        assert '##  [ Types of losses]' in result
        assert '##  [ Moving forward]' in result
        # Check that level 4 accordion headings are converted
        assert result.count('####  [') == 0

    def test_remove_trailing_pagination(self):
        """Test removing trailing pagination numbers"""
        text = '''
        This is the main content.

        This is a paragraph.

        2
        '''

        result = self.converter._remove_trailing_pagination(text)

        assert not result.endswith('2')
        assert 'This is a paragraph.' in result

    def test_remove_excessive_newlines(self):
        """Test removing excessive newlines"""
        text = 'Line 1\n\n\n\n\nLine 2'

        result = self.converter._remove_excessive_newlines(text)

        assert result == 'Line 1\n\nLine 2'

    def test_clean_whitespace(self):
        """Test cleaning trailing whitespace"""
        text = 'Line 1    \nLine 2   \n'

        result = self.converter._clean_whitespace(text)

        assert result == 'Line 1\nLine 2\n'

    def test_convert_with_cleanup_full_pipeline(self):
        """Test full conversion pipeline"""
        html = '''
        <div>
            <h1>Test Title</h1>
            <p>Some content</p>
            <a href="/relative">Link</a>
        </div>
        '''
        base_url = "https://example.com"

        result = self.converter.convert_with_cleanup(html, base_url)

        # Should contain converted markdown
        assert 'Test Title' in result
        assert 'Some content' in result
        # Relative URL should be absolute
        assert 'https://example.com/relative' in result
