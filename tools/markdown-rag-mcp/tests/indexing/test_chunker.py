"""
Unit tests for the DocumentChunker class.

Tests cover document chunking functionality including heading-based boundaries,
size limits, metadata enhancement integration, and section statistics.
"""

from datetime import UTC
from unittest.mock import Mock

import pytest
from markdown_rag_mcp.indexing import DocumentChunker
from markdown_rag_mcp.models import (
    ChunkingError,
    Document,
    DocumentSection,
    ProcessingStatus,
    SectionType,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.chunk_size_limit = 500  # tokens
    config.chunk_overlap = 50  # tokens
    return config


@pytest.fixture
def mock_metadata_enhancer():
    """Create a mock metadata enhancer."""
    enhancer = Mock()
    enhancer.enhance_document_for_embedding.return_value = "enhanced document content"
    enhancer.enhance_section_for_embedding.return_value = "enhanced section content"
    return enhancer


@pytest.fixture
def chunker(mock_config):
    """Create a DocumentChunker instance."""
    return DocumentChunker(mock_config)


@pytest.fixture
def chunker_with_enhancer(mock_config, mock_metadata_enhancer):
    """Create a DocumentChunker instance with metadata enhancer."""
    return DocumentChunker(mock_config, mock_metadata_enhancer)


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    from datetime import datetime

    return Document(
        file_path="/test/sample.md",
        content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
        file_size=1024,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=datetime(2024, 1, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.PENDING,
        frontmatter={"title": "Sample Document", "tags": ["test", "sample"]},
    )


@pytest.fixture
def sample_document_no_frontmatter():
    """Create a sample Document without frontmatter."""
    from datetime import datetime

    return Document(
        file_path="/test/plain.md",
        content_hash="60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752",
        file_size=512,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=datetime(2024, 1, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.PENDING,
    )


class TestDocumentChunker:
    """Test cases for DocumentChunker class."""

    def test_init(self, mock_config):
        """Test chunker initialization."""
        chunker = DocumentChunker(mock_config)

        assert chunker.config == mock_config
        assert chunker.metadata_enhancer is None
        assert chunker.max_chunk_size == 500
        assert chunker.chunk_overlap == 50

    def test_init_with_metadata_enhancer(self, mock_config, mock_metadata_enhancer):
        """Test chunker initialization with metadata enhancer."""
        chunker = DocumentChunker(mock_config, mock_metadata_enhancer)

        assert chunker.metadata_enhancer == mock_metadata_enhancer

    def test_chunk_document_empty_content(self, chunker, sample_document):
        """Test chunking empty content returns empty list."""
        sections = chunker.chunk_document(sample_document, "")

        assert sections == []

    def test_chunk_document_whitespace_content(self, chunker, sample_document):
        """Test chunking whitespace-only content returns empty list."""
        sections = chunker.chunk_document(sample_document, "   \n\t  ")

        assert sections == []

    def test_chunk_document_no_headings(self, chunker, sample_document_no_frontmatter):
        """Test chunking content without headings creates single section."""
        content = "This is a simple paragraph with no headings. It should create a single section."

        sections = chunker.chunk_document(sample_document_no_frontmatter, content)

        assert len(sections) == 1
        section = sections[0]
        assert section.document_id == sample_document_no_frontmatter.id
        assert section.section_text == content
        assert section.heading is None
        assert section.heading_level is None
        assert section.chunk_index == 0
        assert section.section_type == SectionType.PARAGRAPH
        assert section.start_position == 0
        assert section.end_position == len(content)

    def test_chunk_document_with_headings(self, chunker, sample_document_no_frontmatter):
        """Test chunking content with headings creates multiple sections."""
        content = """# Main Title

This is the introduction paragraph.

## Section 1

Content for section 1.

### Subsection 1.1

Content for subsection 1.1.

## Section 2

Content for section 2."""

        sections = chunker.chunk_document(sample_document_no_frontmatter, content)

        assert len(sections) == 4

        # Check first section (Main Title)
        assert sections[0].heading == "Main Title"
        assert sections[0].heading_level == 1
        assert "This is the introduction paragraph." in sections[0].section_text

        # Check second section (Section 1)
        assert sections[1].heading == "Section 1"
        assert sections[1].heading_level == 2
        assert "Content for section 1." in sections[1].section_text

        # Check third section (Subsection 1.1)
        assert sections[2].heading == "Subsection 1.1"
        assert sections[2].heading_level == 3

        # Check fourth section (Section 2)
        assert sections[3].heading == "Section 2"
        assert sections[3].heading_level == 2

    def test_chunk_document_with_frontmatter_and_enhancer(self, chunker_with_enhancer, sample_document):
        """Test chunking with frontmatter and metadata enhancer."""
        content = "# Test Section\n\nSome content here."

        sections = chunker_with_enhancer.chunk_document(sample_document, content)

        assert len(sections) == 1
        # Should call metadata enhancer for section enhancement
        chunker_with_enhancer.metadata_enhancer.enhance_section_for_embedding.assert_called_once()

        # Check that enhanced text is used
        section = sections[0]
        assert section.section_text == "enhanced section content"

    def test_chunk_document_without_frontmatter_no_enhancer(self, chunker, sample_document_no_frontmatter):
        """Test chunking without frontmatter and no enhancer."""
        content = "# Test Section\n\nSome content here."

        sections = chunker.chunk_document(sample_document_no_frontmatter, content)

        assert len(sections) == 1
        section = sections[0]
        # Should use original content since no enhancer and no frontmatter
        assert "Test Section" in section.section_text
        assert "Some content here." in section.section_text

    def test_find_heading_boundaries(self, chunker):
        """Test finding heading boundaries in content."""
        content = """# Level 1 Heading

Some content here.

## Level 2 Heading

More content.

### Level 3 Heading

Even more content.

#### Level 4 Heading

Final content."""

        boundaries = chunker._find_heading_boundaries(content)

        assert len(boundaries) == 4

        # Check first boundary (Level 1)
        pos, text, level, end_pos = boundaries[0]
        assert text == "Level 1 Heading"
        assert level == 1
        assert pos == 0

        # Check second boundary (Level 2)
        pos, text, level, end_pos = boundaries[1]
        assert text == "Level 2 Heading"
        assert level == 2

        # Check third boundary (Level 3)
        pos, text, level, end_pos = boundaries[2]
        assert text == "Level 3 Heading"
        assert level == 3

        # Check fourth boundary (Level 4)
        pos, text, level, end_pos = boundaries[3]
        assert text == "Level 4 Heading"
        assert level == 4

    def test_find_heading_boundaries_no_headings(self, chunker):
        """Test finding heading boundaries in content with no headings."""
        content = "Just plain text with no headings."

        boundaries = chunker._find_heading_boundaries(content)

        assert boundaries == []

    def test_find_heading_boundaries_various_formats(self, chunker):
        """Test finding heading boundaries with various markdown formats."""
        content = """# Heading 1
##Heading 2 Without Space
### Heading 3 With   Multiple   Spaces
####    Heading 4 With Leading Spaces
##### Heading 5
###### Heading 6"""

        boundaries = chunker._find_heading_boundaries(content)

        assert len(boundaries) == 5  # Second one should be ignored (no space after ##)

        # Check that properly formatted headings are found
        texts = [boundary[1] for boundary in boundaries]
        expected_texts = [
            "Heading 1",
            "Heading 3 With   Multiple   Spaces",
            "Heading 4 With Leading Spaces",
            "Heading 5",
            "Heading 6",
        ]
        assert texts == expected_texts

    def test_split_large_section(self, chunker, sample_document):
        """Test splitting a section that exceeds token limits."""
        # Create a large section with paragraph breaks to enable splitting
        paragraphs = ["This is a paragraph with substantial content for testing. " * 10 for i in range(10)]
        large_content = "\n\n".join(paragraphs)

        # Create section with high token count to trigger splitting, but cap at model validation limit
        estimated_tokens = chunker._estimate_tokens(large_content)
        section = DocumentSection(
            document_id=sample_document.id,
            section_text=large_content,
            heading="Large Section",
            heading_level=1,
            chunk_index=0,
            token_count=min(estimated_tokens, 999),  # Cap at model validation limit
            start_position=0,
            end_position=len(large_content),
            section_type=SectionType.HEADING,
        )

        # Verify the content actually exceeds the chunk limit for the test to be meaningful
        assert (
            estimated_tokens > chunker.max_chunk_size
        ), f"Content tokens {estimated_tokens} should exceed limit {chunker.max_chunk_size}"

        subsections = chunker._split_large_section(sample_document, section)

        # Should create multiple subsections
        assert len(subsections) > 1

        # Each subsection should be under the token limit
        for subsection in subsections:
            assert subsection.token_count <= chunker.max_chunk_size

        # All subsections should have the same heading
        for subsection in subsections:
            assert subsection.heading == "Large Section"
            assert subsection.heading_level == 1

    def test_split_large_section_with_paragraphs(self, chunker, sample_document):
        """Test splitting a section with multiple paragraphs."""
        paragraphs = [
            f"Paragraph {i} content goes here with much more text to ensure splitting happens properly."
            for i in range(40)
        ]  # Increase to ensure splitting
        large_content = "\n\n".join(paragraphs)

        section = DocumentSection(
            document_id=sample_document.id,
            section_text=large_content,
            heading="Multi-paragraph Section",
            heading_level=2,
            chunk_index=0,
            token_count=min(chunker._estimate_tokens(large_content), 999),  # Cap at model limit
            start_position=0,
            end_position=len(large_content),
            section_type=SectionType.HEADING,
        )

        subsections = chunker._split_large_section(sample_document, section)

        # Should create multiple subsections based on paragraph boundaries
        assert len(subsections) > 1

    def test_get_overlap_text(self, chunker):
        """Test getting overlap text from section."""
        text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10"

        overlap_text = chunker._get_overlap_text(text, 3)

        assert overlap_text == "Word8 Word9 Word10"

    def test_get_overlap_text_short_content(self, chunker):
        """Test getting overlap text from short content."""
        text = "Short text"

        overlap_text = chunker._get_overlap_text(text, 5)

        assert overlap_text == text

    def test_estimate_tokens(self, chunker):
        """Test token estimation."""
        text = "This is a test string with exactly twenty characters."

        estimated_tokens = chunker._estimate_tokens(text)

        # Should be approximately len(text) // 4
        expected_tokens = max(1, len(text) // 4)
        assert estimated_tokens == expected_tokens

    def test_estimate_tokens_empty(self, chunker):
        """Test token estimation for empty string."""
        estimated_tokens = chunker._estimate_tokens("")

        assert estimated_tokens == 1  # Minimum 1 token

    def test_get_chunking_stats_empty(self, chunker):
        """Test getting chunking statistics for empty section list."""
        stats = chunker.get_chunking_stats([])

        expected_stats = {
            "total_sections": 0,
            "avg_tokens": 0,
            "max_tokens": 0,
            "min_tokens": 0,
            "sections_with_headings": 0,
        }
        assert stats == expected_stats

    def test_get_chunking_stats_with_sections(self, chunker, sample_document):
        """Test getting chunking statistics for sections."""
        sections = [
            DocumentSection(
                document_id=sample_document.id,
                section_text="Short content",
                heading="Section 1",
                heading_level=1,
                chunk_index=0,
                token_count=10,
                start_position=0,
                end_position=13,
                section_type=SectionType.HEADING,
            ),
            DocumentSection(
                document_id=sample_document.id,
                section_text="Medium length content here",
                heading=None,
                heading_level=None,
                chunk_index=1,
                token_count=20,
                start_position=13,
                end_position=39,
                section_type=SectionType.PARAGRAPH,
            ),
            DocumentSection(
                document_id=sample_document.id,
                section_text="This is longer content with more text",
                heading="Section 2",
                heading_level=2,
                chunk_index=2,
                token_count=30,
                start_position=39,
                end_position=76,
                section_type=SectionType.HEADING,
            ),
        ]

        stats = chunker.get_chunking_stats(sections)

        assert stats["total_sections"] == 3
        assert stats["avg_tokens"] == 20.0  # (10 + 20 + 30) / 3
        assert stats["max_tokens"] == 30
        assert stats["min_tokens"] == 10
        assert stats["sections_with_headings"] == 2

    def test_chunk_document_section_reindexing(self, chunker_with_enhancer, sample_document):
        """Test that sections are properly re-indexed after splitting."""
        # Create content that will result in splitting
        content = (
            """# Section 1

"""
            + "Long paragraph content. " * 30
            + """

# Section 2

More content here."""
        )

        # Mock _estimate_tokens to force splitting
        original_estimate = chunker_with_enhancer._estimate_tokens

        def mock_estimate_tokens(text):
            if "Long paragraph content" in text and len(text) > 100:
                return 600  # Force over limit
            return original_estimate(text)

        chunker_with_enhancer._estimate_tokens = mock_estimate_tokens

        sections = chunker_with_enhancer.chunk_document(sample_document, content)

        # Verify sections are properly indexed
        for i, section in enumerate(sections):
            assert section.chunk_index == i

        # Restore original method
        chunker_with_enhancer._estimate_tokens = original_estimate

    def test_chunk_document_exception_handling(self, chunker, sample_document):
        """Test exception handling during chunking."""
        content = "# Test\n\nContent"

        # Mock _find_heading_boundaries to raise exception
        chunker._find_heading_boundaries = Mock(side_effect=Exception("Test error"))

        with pytest.raises(ChunkingError) as exc_info:
            chunker.chunk_document(sample_document, content)

        assert "Failed to chunk document" in str(exc_info.value)
        assert exc_info.value.context.get("file_path") == sample_document.file_path
        assert exc_info.value.context.get("operation") == "chunk_document"

    def test_create_heading_sections_empty_boundaries(self, chunker_with_enhancer, sample_document):
        """Test creating sections with empty heading boundaries."""
        content = "Plain text content without any headings."

        sections = chunker_with_enhancer._create_heading_sections(sample_document, content, [])

        assert len(sections) == 1
        section = sections[0]
        assert "enhanced" in section.section_text  # Should be enhanced by metadata enhancer
        assert section.heading is None
        assert section.section_type == SectionType.PARAGRAPH

    def test_create_heading_sections_skip_empty_sections(self, chunker_with_enhancer, sample_document):
        """Test that empty sections between headings are skipped."""
        content = """# Heading 1

Content for heading 1.

# Heading 2


# Heading 3

Content for heading 3."""

        boundaries = chunker_with_enhancer._find_heading_boundaries(content)
        sections = chunker_with_enhancer._create_heading_sections(sample_document, content, boundaries)

        # Should skip the empty section between Heading 2 and Heading 3
        assert len(sections) == 2
        assert sections[0].heading == "Heading 1"
        assert sections[1].heading == "Heading 3"

    def test_chunk_document_frontmatter_no_enhancer(self, chunker_with_enhancer, sample_document):
        """Test chunking with frontmatter but no metadata enhancer."""
        content = "# Test\n\nContent here."

        sections = chunker_with_enhancer.chunk_document(sample_document, content)

        assert len(sections) == 1
        # Should use enhanced content since we have an enhancer
        section = sections[0]
        assert "enhanced" in section.section_text

    def test_section_includes_heading_in_text(self, chunker, sample_document_no_frontmatter):
        """Test that sections include heading text for context."""
        content = """# Main Heading

This is content under the main heading.

## Sub Heading

This is content under the sub heading."""

        sections = chunker.chunk_document(sample_document_no_frontmatter, content)

        assert len(sections) == 2

        # First section should include "Main Heading" in the text
        assert "Main Heading" in sections[0].section_text
        assert "This is content under the main heading." in sections[0].section_text

        # Second section should include "Sub Heading" in the text
        assert "Sub Heading" in sections[1].section_text
        assert "This is content under the sub heading." in sections[1].section_text
