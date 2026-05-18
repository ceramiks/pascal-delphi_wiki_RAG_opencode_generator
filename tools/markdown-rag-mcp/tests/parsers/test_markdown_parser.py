"""
Unit tests for MarkdownParser.

Tests the markdown document parsing functionality including frontmatter
integration, document creation, and error handling.
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from markdown_rag_mcp.models import Document, DocumentParsingError, ProcessingStatus
from markdown_rag_mcp.parsers import MarkdownParser


class TestMarkdownParser:
    """Test cases for MarkdownParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.max_file_size_mb = 10
        self.config.is_file_supported.return_value = True

        self.parser = MarkdownParser(self.config)

    def test_init(self):
        """Test parser initialization."""
        assert self.parser.config is self.config
        assert self.parser.frontmatter_parser is not None

    def test_supports_file_type(self):
        """Test file type support checking."""
        test_path = Path("test.md")

        # Configure mock to return True
        self.config.is_file_supported.return_value = True
        assert self.parser.supports_file_type(test_path) is True

        # Configure mock to return False
        self.config.is_file_supported.return_value = False
        assert self.parser.supports_file_type(test_path) is False

        # Verify the config method was called with the path
        self.config.is_file_supported.assert_called_with(test_path)

    @pytest.mark.asyncio
    async def test_parse_file_with_frontmatter(self):
        """Test parsing file with frontmatter."""
        content = """---
title: Test Document
tags: [test, parsing]
summary: A test document
---

# Test Content

This is a test markdown document.

## Section 2

More content here.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            # Verify document properties
            assert isinstance(document, Document)
            assert document.file_path == str(temp_path.absolute())
            assert document.processing_status == ProcessingStatus.PENDING

            # Verify frontmatter
            assert document.frontmatter["title"] == "Test Document"
            assert document.frontmatter["tags"] == ["test", "parsing"]
            assert document.frontmatter["summary"] == "A test document"

            # Verify content
            assert hasattr(document, '_raw_content')
            assert "# Test Content" in document._raw_content
            assert "This is a test markdown document." in document._raw_content

            # Verify metadata
            assert document.word_count > 0
            assert document.file_size > 0
            assert isinstance(document.created_at, datetime)
            assert isinstance(document.modified_at, datetime)
            assert len(document.content_hash) == 64  # SHA-256 hash length

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_file_without_frontmatter(self):
        """Test parsing file without frontmatter."""
        content = """# Simple Document

This is a simple markdown document without frontmatter.

It should still be parsed correctly.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            # Verify document properties
            assert isinstance(document, Document)
            assert document.frontmatter == {}
            assert document.word_count > 0
            assert "Simple Document" in document._raw_content

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_nonexistent_file(self):
        """Test parsing non-existent file raises DocumentParsingError."""
        nonexistent_path = Path("/nonexistent/file.md")

        with pytest.raises(DocumentParsingError) as exc_info:
            await self.parser.parse_file(nonexistent_path)

        assert exc_info.value.context.get("file_path") == str(nonexistent_path)
        assert exc_info.value.context.get("parsing_stage") == "file_validation"

    @pytest.mark.asyncio
    async def test_parse_file_too_large(self):
        """Test parsing file that exceeds size limit."""
        # Set a very small file size limit
        self.config.max_file_size_mb = 0.000001  # ~1 byte

        content = "This content is definitely larger than 1 byte"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(DocumentParsingError) as exc_info:
                await self.parser.parse_file(temp_path)

            assert exc_info.value.context.get("parsing_stage") == "size_validation"
            assert "too large" in str(exc_info.value)

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    @patch('builtins.open')
    async def test_parse_file_encoding_error(self, mock_open):
        """Test handling of file encoding errors."""
        # Create a real file first
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)

        try:
            # Mock open to raise UnicodeDecodeError when frontmatter parser tries to read
            mock_open.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')

            with pytest.raises(DocumentParsingError) as exc_info:
                await self.parser.parse_file(temp_path)

            # FrontmatterParser catches and re-raises encoding errors as frontmatter_parsing
            assert exc_info.value.context.get("parsing_stage") == "frontmatter_parsing"
            assert "codec" in str(exc_info.value).lower()

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_file_frontmatter_error(self):
        """Test handling of frontmatter parsing errors."""
        # Create file with invalid YAML frontmatter
        content = """---
title: Test
invalid_yaml: [unclosed
---

Content here.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(DocumentParsingError) as exc_info:
                await self.parser.parse_file(temp_path)

            # FrontmatterParser converts YAML parsing errors to ParsingError, which becomes file_reading in our handler
            assert exc_info.value.context.get("parsing_stage") == "file_reading"

        finally:
            temp_path.unlink()

    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        content1 = "Test content"
        metadata1 = {"title": "Test"}

        content2 = "Test content"
        metadata2 = {"title": "Test"}

        content3 = "Different content"
        metadata3 = {"title": "Test"}

        # Same content and metadata should produce same hash
        hash1 = self.parser._calculate_content_hash(content1, metadata1)
        hash2 = self.parser._calculate_content_hash(content2, metadata2)
        assert hash1 == hash2

        # Different content should produce different hash
        hash3 = self.parser._calculate_content_hash(content3, metadata3)
        assert hash1 != hash3

        # Hash should be SHA-256 (64 hex characters)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)

    def test_calculate_content_hash_metadata_order(self):
        """Test that metadata order doesn't affect hash."""
        content = "Test content"
        metadata1 = {"title": "Test", "tags": ["a", "b"]}
        metadata2 = {"tags": ["a", "b"], "title": "Test"}

        hash1 = self.parser._calculate_content_hash(content, metadata1)
        hash2 = self.parser._calculate_content_hash(content, metadata2)

        # Should be the same regardless of metadata key order
        assert hash1 == hash2

    def test_calculate_content_hash_empty_inputs(self):
        """Test hash calculation with empty inputs."""
        # Empty content and metadata
        hash1 = self.parser._calculate_content_hash("", {})

        # None content
        hash2 = self.parser._calculate_content_hash(None, {})

        # Both should work and produce valid hashes
        assert len(hash1) == 64
        assert len(hash2) == 64
        assert hash1 == hash2  # None and empty string should produce same hash

    def test_extract_text_content(self):
        """Test text content extraction."""
        # Create a mock document with raw content
        document = Mock()
        document._raw_content = "# Test\n\nThis is content."

        result = self.parser.extract_text_content(document)
        assert result == "# Test\n\nThis is content."

        # Test document without raw content
        document_no_content = Mock()
        delattr(document_no_content, '_raw_content')  # Remove the attribute

        result = self.parser.extract_text_content(document_no_content)
        assert result == ""

    @pytest.mark.asyncio
    async def test_parse_file_word_count(self):
        """Test word count calculation."""
        content = """---
title: Word Count Test
---

# Test Document

This document has exactly ten words in this sentence here.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            # Should count words in content but not frontmatter
            # Content: "# Test Document\n\nThis document has exactly ten words in this sentence here."
            # Words: Test, Document, This, document, has, exactly, ten, words, in, this, sentence, here, =
            # = 13 words (including the # Test Document heading)
            assert document.word_count == 13

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_empty_file(self):
        """Test parsing empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            # Write empty content
            f.write("")
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            assert document.word_count == 0
            assert document.frontmatter == {}
            assert document._raw_content == ""
            assert document.file_size == 0

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_file_timestamps(self):
        """Test that file timestamps are correctly extracted."""
        content = "# Test\nContent"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            # Check timestamps are set and are datetime objects
            assert isinstance(document.created_at, datetime)
            assert isinstance(document.modified_at, datetime)
            assert document.created_at.tzinfo == UTC
            assert document.modified_at.tzinfo == UTC

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_file_with_unicode(self):
        """Test parsing file with Unicode content."""
        content = """---
title: Unicode Test 测试
tags: [unicode, 测试, français]
---

# Unicode Content 测试

This content has Unicode: 你好世界 🌍 français español
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            assert "测试" in document.frontmatter["title"]
            assert "测试" in document.frontmatter["tags"]
            assert "français" in document.frontmatter["tags"]
            assert "你好世界" in document._raw_content
            assert "🌍" in document._raw_content

        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_parse_file_integration_with_frontmatter_parser(self):
        """Test integration with FrontmatterParser functionality."""
        content = """---
title: Integration Test
tags: test, integration, parsing
topics: [testing, validation]
keywords: "parse, validate, test"
summary: |
  Multi-line summary
  with proper formatting
llm_hints: [context, semantic]
unsupported_field: should be ignored
---

# Integration Test

This tests the integration between MarkdownParser and FrontmatterParser.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            document = await self.parser.parse_file(temp_path)

            # Verify FrontmatterParser's field validation worked
            assert "unsupported_field" not in document.frontmatter

            # Verify FrontmatterParser's field cleaning worked
            assert document.frontmatter["tags"] == ["test", "integration", "parsing"]
            assert document.frontmatter["topics"] == ["testing", "validation"]
            assert document.frontmatter["keywords"] == ["parse", "validate", "test"]

            # Verify multi-line summary handling
            assert "Multi-line summary" in document.frontmatter["summary"]
            assert "proper formatting" in document.frontmatter["summary"]

            # Verify list field handling
            assert document.frontmatter["llm_hints"] == ["context", "semantic"]

        finally:
            temp_path.unlink()
