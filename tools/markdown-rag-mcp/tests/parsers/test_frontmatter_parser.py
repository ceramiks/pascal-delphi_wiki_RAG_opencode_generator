"""
Unit tests for FrontmatterParser.

Tests the frontmatter parsing functionality including validation,
cleaning, and error handling.
"""

import tempfile
from pathlib import Path

import pytest
from markdown_rag_mcp.models import ParsingError
from markdown_rag_mcp.parsers import FrontmatterParser


class TestFrontmatterParser:
    """Test cases for FrontmatterParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = FrontmatterParser()

    def test_parse_string_with_valid_frontmatter(self):
        """Test parsing string content with valid frontmatter."""
        content = """---
title: Test Document
tags: [test, example]
topics: [documentation, testing]
summary: A test document for parsing
---

# Test Content

This is the markdown content.
"""
        metadata, markdown_content = self.parser.parse_string(content)

        assert metadata["title"] == "Test Document"
        assert metadata["tags"] == ["test", "example"]
        assert metadata["topics"] == ["documentation", "testing"]
        assert metadata["summary"] == "A test document for parsing"
        assert "# Test Content" in markdown_content
        assert "This is the markdown content." in markdown_content

    def test_parse_string_without_frontmatter(self):
        """Test parsing string content without frontmatter."""
        content = """# Test Content

This is just markdown content without frontmatter.
"""
        metadata, markdown_content = self.parser.parse_string(content)

        assert metadata == {}
        assert "# Test Content" in markdown_content

    def test_parse_string_with_comma_separated_tags(self):
        """Test parsing tags as comma-separated string."""
        content = """---
title: Test Document
tags: test, example, parsing
keywords: "search, find, locate"
---

Content here.
"""
        metadata, markdown_content = self.parser.parse_string(content)

        assert metadata["tags"] == ["test", "example", "parsing"]
        assert metadata["keywords"] == ["search", "find", "locate"]

    def test_parse_string_with_unsupported_fields(self):
        """Test that unsupported fields are filtered out."""
        content = """---
title: Test Document
unsupported_field: should be ignored
another_field: also ignored
tags: [valid]
---

Content here.
"""
        metadata, markdown_content = self.parser.parse_string(content)

        assert "unsupported_field" not in metadata
        assert "another_field" not in metadata
        assert metadata["title"] == "Test Document"
        assert metadata["tags"] == ["valid"]

    def test_parse_file_with_valid_frontmatter(self):
        """Test parsing file with valid frontmatter."""
        content = """---
title: File Test
tags: [file, test]
summary: Testing file parsing
---

# File Content

This content comes from a file.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            metadata, markdown_content = self.parser.parse_file(temp_path)

            assert metadata["title"] == "File Test"
            assert metadata["tags"] == ["file", "test"]
            assert metadata["summary"] == "Testing file parsing"
            assert "# File Content" in markdown_content

        finally:
            temp_path.unlink()

    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file raises ParsingError."""
        nonexistent_path = Path("/nonexistent/file.md")

        with pytest.raises(ParsingError) as exc_info:
            self.parser.parse_file(nonexistent_path)

        assert "not found" in str(exc_info.value)
        assert exc_info.value.context.get("file_path") == str(nonexistent_path)

    def test_clean_field_value_title(self):
        """Test cleaning title field values."""
        # String title
        result = self.parser._clean_field_value("title", "  Test Title  ")
        assert result == "Test Title"

        # Non-string title
        result = self.parser._clean_field_value("title", 123)
        assert result == "123"

        # None title
        result = self.parser._clean_field_value("title", None)
        assert result is None

    def test_clean_field_value_tags_list(self):
        """Test cleaning tags as list."""
        # Valid list
        result = self.parser._clean_field_value("tags", ["  tag1  ", "tag2", "  "])
        assert result == ["tag1", "tag2"]

        # Empty list
        result = self.parser._clean_field_value("tags", [])
        assert result is None

        # List with empty strings
        result = self.parser._clean_field_value("tags", ["", "  ", "valid"])
        assert result == ["valid"]

    def test_clean_field_value_tags_string(self):
        """Test cleaning tags as comma-separated string."""
        # Comma-separated string
        result = self.parser._clean_field_value("tags", "tag1, tag2,  tag3  ")
        assert result == ["tag1", "tag2", "tag3"]

        # Single tag
        result = self.parser._clean_field_value("tags", "single")
        assert result == ["single"]

        # Empty string
        result = self.parser._clean_field_value("tags", "")
        assert result is None

    def test_clean_field_value_invalid_types(self):
        """Test handling of invalid field value types."""
        # Complex object gets converted to string and treated as comma-separated
        result = self.parser._clean_field_value("tags", {"invalid": "object"})
        assert result == ["{'invalid': 'object'}"]  # Gets converted to string and wrapped in list

    def test_extract_metadata_filtering(self):
        """Test metadata extraction with field filtering."""
        raw_metadata = {
            "title": "Valid Title",
            "tags": ["valid", "tags"],
            "invalid_field": "should be ignored",
            "another_invalid": 123,
            "summary": "Valid summary",
        }

        metadata = self.parser._extract_metadata(raw_metadata)

        assert "invalid_field" not in metadata
        assert "another_invalid" not in metadata
        assert metadata["title"] == "Valid Title"
        assert metadata["tags"] == ["valid", "tags"]
        assert metadata["summary"] == "Valid summary"

    def test_has_frontmatter(self):
        """Test frontmatter detection."""
        # With frontmatter
        content_with_fm = """---
title: Test
---
Content"""
        assert self.parser.has_frontmatter(content_with_fm) is True

        # Without frontmatter
        content_without_fm = """# Just Content
No frontmatter here."""
        assert self.parser.has_frontmatter(content_without_fm) is False

        # Empty content
        assert self.parser.has_frontmatter("") is False

        # Only whitespace before frontmatter
        content_with_spaces = """   ---
title: Test
---"""
        assert self.parser.has_frontmatter(content_with_spaces) is True

    def test_get_supported_fields(self):
        """Test getting supported fields."""
        fields = self.parser.get_supported_fields()

        assert isinstance(fields, set)
        assert "title" in fields
        assert "tags" in fields
        assert "topics" in fields
        assert "keywords" in fields
        assert "summary" in fields
        assert "llm_hints" in fields

    def test_parse_complex_frontmatter(self):
        """Test parsing complex frontmatter with all supported fields."""
        content = """---
title: Complex Document
tags:
  - python
  - testing
  - parsing
topics: ["documentation", "code-quality"]
keywords: test, parse, validate
summary: |
  A comprehensive test document that includes
  multiple lines in the summary field.
llm_hints: [context, semantic, search]
---

# Complex Content

This document tests all supported frontmatter fields.
"""
        metadata, markdown_content = self.parser.parse_string(content)

        assert metadata["title"] == "Complex Document"
        assert metadata["tags"] == ["python", "testing", "parsing"]
        assert metadata["topics"] == ["documentation", "code-quality"]
        assert metadata["keywords"] == ["test", "parse", "validate"]
        assert "comprehensive test document" in metadata["summary"]
        assert metadata["llm_hints"] == ["context", "semantic", "search"]

    def test_parse_malformed_frontmatter(self):
        """Test parsing malformed frontmatter."""
        content = """---
title: Test
invalid_yaml: [unclosed list
---

Content here.
"""
        # Should raise ParsingError due to invalid YAML
        with pytest.raises(ParsingError) as exc_info:
            self.parser.parse_string(content)

        assert "parse" in str(exc_info.value).lower()

    def test_field_cleaning_edge_cases(self):
        """Test edge cases in field cleaning."""
        # Mixed types in list - None gets converted to "None" string
        result = self.parser._clean_field_value("tags", ["string", 123, None, ""])
        assert result == ["string", "123", "None"]

        # Numeric values for string fields
        result = self.parser._clean_field_value("title", 0)
        assert result == "0"

        # Boolean values
        result = self.parser._clean_field_value("summary", True)
        assert result == "True"

    @pytest.mark.parametrize("field_name", ["tags", "topics", "keywords", "llm_hints"])
    def test_list_field_variations(self, field_name):
        """Test various input formats for list fields."""
        # List format
        result = self.parser._clean_field_value(field_name, ["item1", "item2"])
        assert result == ["item1", "item2"]

        # String format
        result = self.parser._clean_field_value(field_name, "item1, item2")
        assert result == ["item1", "item2"]

        # Single item
        result = self.parser._clean_field_value(field_name, "single")
        assert result == ["single"]

        # Empty input
        result = self.parser._clean_field_value(field_name, "")
        assert result is None

    def test_unicode_handling(self):
        """Test handling of Unicode characters in frontmatter."""
        content = """---
title: "测试文档 - Test Document"
tags: [测试, test, "français", español]
summary: Unicode characters should be handled properly 🚀
---

# Content with Unicode

This tests Unicode handling in both frontmatter and content.
测试内容 🎉
"""
        metadata, markdown_content = self.parser.parse_string(content)

        assert "测试文档" in metadata["title"]
        assert "测试" in metadata["tags"]
        assert "français" in metadata["tags"]
        assert "🚀" in metadata["summary"]
        assert "测试内容 🎉" in markdown_content
