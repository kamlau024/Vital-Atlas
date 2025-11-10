"""
Tests for pipeline components
"""
import pytest
from vital_atlas.pipelines import FileStoragePipeline


class TestFileStoragePipeline:
    """Test file storage pipeline"""

    def test_remove_duplicate_title_exact_match(self):
        """Test removing duplicate title with exact match"""
        content = '''
# Anger

Some content here

## When to ask for help
'''
        title = "Anger"

        result = FileStoragePipeline._remove_duplicate_title(content, title)

        # Should remove the duplicate H1
        assert result.count('# Anger') == 0
        assert 'Some content here' in result
        assert '## When to ask for help' in result

    def test_remove_duplicate_title_no_false_positive(self):
        """Test that similar titles are not removed"""
        content = '''
Some intro text

## Expressing anger

Content about expressing anger

## When to ask for help
'''
        title = "Anger"

        result = FileStoragePipeline._remove_duplicate_title(content, title)

        # Should NOT remove "Expressing anger" even though it contains "anger"
        assert '## Expressing anger' in result
        assert 'Content about expressing anger' in result

    def test_remove_duplicate_title_various_heading_levels(self):
        """Test removing duplicate titles at different heading levels"""
        content = '''
### Breast Cancer

Some content

## Overview
'''
        title = "Breast Cancer"

        result = FileStoragePipeline._remove_duplicate_title(content, title)

        # Should remove the H3 "Breast Cancer"
        assert '### Breast Cancer' not in result
        assert 'Some content' in result
        assert '## Overview' in result

    def test_remove_duplicate_title_case_insensitive(self):
        """Test case-insensitive title matching"""
        content = '''
# breast cancer

Content here
'''
        title = "Breast Cancer"

        result = FileStoragePipeline._remove_duplicate_title(content, title)

        # Should remove despite case difference
        assert '# breast cancer' not in result
        assert 'Content here' in result

    def test_remove_duplicate_title_empty_content(self):
        """Test with empty content"""
        result = FileStoragePipeline._remove_duplicate_title('', 'Title')
        assert result == ''

    def test_remove_duplicate_title_no_title(self):
        """Test with no title provided"""
        content = '# Some Heading\n\nContent'
        result = FileStoragePipeline._remove_duplicate_title(content, '')
        assert result == content
