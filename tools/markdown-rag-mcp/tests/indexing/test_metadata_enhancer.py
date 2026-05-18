"""
Unit tests for the MetadataEnhancer class.

Tests cover metadata enhancement functionality including document and section
enhancement, metadata context creation, and statistics generation.
"""

from datetime import UTC
from uuid import uuid4

import pytest
from markdown_rag_mcp.indexing import MetadataEnhancer
from markdown_rag_mcp.models import Document, DocumentSection, ProcessingStatus, SectionType


@pytest.fixture
def metadata_enhancer():
    """Create a MetadataEnhancer instance with default settings."""
    return MetadataEnhancer()


@pytest.fixture
def custom_metadata_enhancer():
    """Create a MetadataEnhancer instance with custom settings."""
    return MetadataEnhancer(
        include_title_weight=3.0,
        include_summary_weight=2.5,
        include_keywords_weight=2.0,
        include_tags_weight=1.5,
        include_llm_hints=False,
    )


@pytest.fixture
def document_with_frontmatter():
    """Create a Document with rich frontmatter."""
    from datetime import datetime

    return Document(
        file_path="/test/rich_doc.md",
        content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
        file_size=1024,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=datetime(2024, 1, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.PENDING,
        frontmatter={
            "title": "Advanced Machine Learning Techniques",
            "summary": "A comprehensive guide to modern ML algorithms and their applications",
            "keywords": ["machine-learning", "artificial-intelligence", "deep-learning", "neural-networks"],
            "tags": ["tutorial", "advanced", "ai"],
            "topics": ["supervised-learning", "unsupervised-learning", "reinforcement-learning"],
            "llm_hints": "This document focuses on practical implementations of ML algorithms",
        },
    )


@pytest.fixture
def document_without_frontmatter():
    """Create a Document without frontmatter."""
    from datetime import datetime

    return Document(
        file_path="/test/plain_doc.md",
        content_hash="60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752",
        file_size=512,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=datetime(2024, 1, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.PENDING,
    )


@pytest.fixture
def document_with_partial_frontmatter():
    """Create a Document with minimal frontmatter."""
    from datetime import datetime

    return Document(
        file_path="/test/minimal_doc.md",
        content_hash="fd61a03af4f77d870fc21e05e7e80678095c92d808cfb3b5c279ee04c74aca13",
        file_size=256,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=datetime(2024, 1, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.PENDING,
        frontmatter={
            "title": "Simple Guide",
            "tags": ["basic", "guide"],
        },
    )


@pytest.fixture
def sample_section():
    """Create a sample DocumentSection."""
    return DocumentSection(
        document_id=uuid4(),
        section_text="This is the content of a document section with technical details.",
        heading="Technical Implementation",
        heading_level=2,
        chunk_index=1,
        token_count=50,
        start_position=100,
        end_position=200,
        section_type=SectionType.HEADING,
    )


class TestMetadataEnhancer:
    """Test cases for MetadataEnhancer class."""

    def test_init_default_settings(self):
        """Test metadata enhancer initialization with default settings."""
        enhancer = MetadataEnhancer()

        assert enhancer.include_title_weight == 2.0
        assert enhancer.include_summary_weight == 1.5
        assert enhancer.include_keywords_weight == 1.2
        assert enhancer.include_tags_weight == 1.0
        assert enhancer.include_llm_hints is True

    def test_init_custom_settings(self):
        """Test metadata enhancer initialization with custom settings."""
        enhancer = MetadataEnhancer(
            include_title_weight=3.0,
            include_summary_weight=2.5,
            include_keywords_weight=2.0,
            include_tags_weight=1.5,
            include_llm_hints=False,
        )

        assert enhancer.include_title_weight == 3.0
        assert enhancer.include_summary_weight == 2.5
        assert enhancer.include_keywords_weight == 2.0
        assert enhancer.include_tags_weight == 1.5
        assert enhancer.include_llm_hints is False

    def test_init_weight_minimum_enforcement(self):
        """Test that weight values are enforced to be at least 1.0."""
        enhancer = MetadataEnhancer(
            include_title_weight=0.5,
            include_summary_weight=0.8,
            include_keywords_weight=0.3,
            include_tags_weight=0.1,
        )

        assert enhancer.include_title_weight == 1.0
        assert enhancer.include_summary_weight == 1.0
        assert enhancer.include_keywords_weight == 1.0
        assert enhancer.include_tags_weight == 1.0

    def test_enhance_document_for_embedding_no_frontmatter(self, metadata_enhancer, document_without_frontmatter):
        """Test enhancing document without frontmatter returns original content."""
        content = "This is the original document content."

        enhanced_content = metadata_enhancer.enhance_document_for_embedding(document_without_frontmatter, content)

        assert enhanced_content == content

    def test_enhance_document_for_embedding_with_frontmatter(self, metadata_enhancer, document_with_frontmatter):
        """Test enhancing document with rich frontmatter."""
        content = "This is the main document content about machine learning."

        enhanced_content = metadata_enhancer.enhance_document_for_embedding(document_with_frontmatter, content)

        # Should include title (repeated based on weight)
        assert "Title: Advanced Machine Learning Techniques" in enhanced_content

        # Should include summary
        assert "Summary: A comprehensive guide to modern ML algorithms" in enhanced_content

        # Should include keywords
        assert "Keywords: machine-learning, artificial-intelligence, deep-learning, neural-networks" in enhanced_content

        # Should include tags
        assert "Tags: tutorial, advanced, ai" in enhanced_content

        # Should include topics
        assert "Topics: supervised-learning, unsupervised-learning, reinforcement-learning" in enhanced_content

        # Should include LLM hints
        assert "Context: This document focuses on practical implementations" in enhanced_content

        # Should include original content
        assert content in enhanced_content

        # Check that title is repeated based on weight (default 2.0)
        title_count = enhanced_content.count("Title: Advanced Machine Learning Techniques")
        assert title_count == 2

    def test_enhance_document_for_embedding_custom_weights(self, custom_metadata_enhancer, document_with_frontmatter):
        """Test enhancing document with custom weights."""
        content = "Document content."

        enhanced_content = custom_metadata_enhancer.enhance_document_for_embedding(document_with_frontmatter, content)

        # Title should be repeated 3 times (custom weight 3.0)
        title_count = enhanced_content.count("Title: Advanced Machine Learning Techniques")
        assert title_count == 3

        # Summary should be repeated 2 times (custom weight 2.5 -> int(2.5) = 2)
        summary_count = enhanced_content.count("Summary: A comprehensive guide")
        assert summary_count == 2

        # Keywords should be repeated 2 times (custom weight 2.0)
        keywords_count = enhanced_content.count("Keywords:")
        assert keywords_count == 2

        # Tags should be repeated 1 time (custom weight 1.5 -> int(1.5) = 1)
        tags_count = enhanced_content.count("Tags:")
        assert tags_count == 1

        # LLM hints should not be included (custom setting False)
        assert "Context:" not in enhanced_content

    def test_enhance_document_for_embedding_title_same_as_filename(self, metadata_enhancer):
        """Test that title is not included if it's the same as filename."""
        from datetime import datetime

        document = Document(
            file_path="/test/simple_guide.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "simple_guide",  # Same as filename without extension
            },
        )

        content = "Document content."
        enhanced_content = metadata_enhancer.enhance_document_for_embedding(document, content)

        # Title should be added since "simple_guide" != "simple_guide.md" (filename)
        assert "Title:" in enhanced_content

    def test_enhance_document_for_embedding_string_tags_and_keywords(self, metadata_enhancer):
        """Test handling of string-format tags and keywords (comma-separated)."""
        from datetime import datetime

        document = Document(
            file_path="/test/string_format.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "tags": "python, programming, tutorial",
                "keywords": "coding, development",
            },
        )

        content = "Document content."
        enhanced_content = metadata_enhancer.enhance_document_for_embedding(document, content)

        assert "Tags: python, programming, tutorial" in enhanced_content
        assert "Keywords: coding, development" in enhanced_content

    def test_enhance_section_for_embedding(self, metadata_enhancer, document_with_frontmatter, sample_section):
        """Test enhancing a document section."""
        enhanced_content = metadata_enhancer.enhance_section_for_embedding(document_with_frontmatter, sample_section)

        # Should include document title
        assert "Document: Advanced Machine Learning Techniques" in enhanced_content

        # Should include section heading
        assert "Section: Technical Implementation" in enhanced_content

        # Should include limited tags (first 3)
        assert "Tags: tutorial, advanced, ai" in enhanced_content

        # Should include limited keywords (first 5)
        assert "Keywords: machine-learning, artificial-intelligence, deep-learning, neural-networks" in enhanced_content

        # Should include original section content
        assert sample_section.section_text in enhanced_content

    def test_enhance_section_for_embedding_no_heading(self, metadata_enhancer, document_with_frontmatter):
        """Test enhancing a section without heading."""
        section = DocumentSection(
            document_id=document_with_frontmatter.id,
            section_text="Content without heading.",
            heading=None,
            heading_level=None,
            chunk_index=0,
            token_count=20,
            start_position=0,
            end_position=25,
            section_type=SectionType.PARAGRAPH,
        )

        enhanced_content = metadata_enhancer.enhance_section_for_embedding(document_with_frontmatter, section)

        # Should not include section heading line
        assert "Section:" not in enhanced_content
        assert "Document: Advanced Machine Learning Techniques" in enhanced_content

    def test_enhance_section_for_embedding_title_same_as_filename(self, metadata_enhancer, sample_section):
        """Test section enhancement when document title matches filename."""
        from datetime import datetime

        document = Document(
            file_path="/test/guide.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "guide.md",  # Must match full filename including extension
                "tags": ["tutorial"],
            },
        )

        enhanced_content = metadata_enhancer.enhance_section_for_embedding(document, sample_section)

        # Should not include document title since it matches filename
        assert "Document:" not in enhanced_content

    def test_enhance_section_for_embedding_limited_metadata(self, metadata_enhancer, sample_section):
        """Test section enhancement with limited tags and keywords."""
        from datetime import datetime

        document = Document(
            file_path="/test/many_tags.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "Many Tags Document",
                "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
                "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7"],
            },
        )

        enhanced_content = metadata_enhancer.enhance_section_for_embedding(document, sample_section)

        # Should limit to first 3 tags
        assert "Tags: tag1, tag2, tag3" in enhanced_content
        assert "tag4" not in enhanced_content

        # Should limit to first 5 keywords
        assert "Keywords: kw1, kw2, kw3, kw4, kw5" in enhanced_content
        assert "kw6" not in enhanced_content

    def test_create_metadata_context_no_frontmatter(self, metadata_enhancer, document_without_frontmatter):
        """Test creating metadata context for document without frontmatter."""
        context = metadata_enhancer.create_metadata_context(document_without_frontmatter)

        assert context == ""

    def test_create_metadata_context_with_frontmatter(self, metadata_enhancer, document_with_frontmatter):
        """Test creating metadata context for document with frontmatter."""
        context = metadata_enhancer.create_metadata_context(document_with_frontmatter)

        # Should include all metadata fields as space-separated text
        assert "Advanced Machine Learning Techniques" in context
        assert "A comprehensive guide to modern ML algorithms" in context
        assert "tutorial" in context
        assert "advanced" in context
        assert "ai" in context
        assert "supervised-learning" in context
        assert "machine-learning" in context
        assert "This document focuses on practical implementations" in context

    def test_create_metadata_context_no_llm_hints(self, custom_metadata_enhancer, document_with_frontmatter):
        """Test creating metadata context without LLM hints."""
        context = custom_metadata_enhancer.create_metadata_context(document_with_frontmatter)

        # Should not include LLM hints
        assert "This document focuses on practical implementations" not in context

        # Should still include other metadata
        assert "Advanced Machine Learning Techniques" in context

    def test_create_metadata_context_title_same_as_filename(self, metadata_enhancer):
        """Test metadata context when title matches filename."""
        from datetime import datetime

        document = Document(
            file_path="/test/guide.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "guide.md",  # Must match full filename including extension
                "summary": "A helpful guide",
            },
        )

        context = metadata_enhancer.create_metadata_context(document)

        # Should not include title since it matches filename
        assert "guide.md" not in context
        assert "A helpful guide" in context

    def test_get_enhancement_stats_no_frontmatter(self, metadata_enhancer, document_without_frontmatter):
        """Test getting enhancement statistics for document without frontmatter."""
        stats = metadata_enhancer.get_enhancement_stats(document_without_frontmatter)

        expected_stats = {
            "has_frontmatter": False,
            "has_title": True,  # Title comes from filename stem, different from full filename
            "has_summary": False,
            "tag_count": 0,
            "topic_count": 0,
            "keyword_count": 0,
            "has_llm_hints": False,
            "metadata_fields": ["title"],  # Title field exists from filename
        }

        assert stats == expected_stats

    def test_get_enhancement_stats_with_frontmatter(self, metadata_enhancer, document_with_frontmatter):
        """Test getting enhancement statistics for document with frontmatter."""
        stats = metadata_enhancer.get_enhancement_stats(document_with_frontmatter)

        expected_stats = {
            "has_frontmatter": True,
            "has_title": True,
            "has_summary": True,
            "tag_count": 3,
            "topic_count": 3,
            "keyword_count": 4,
            "has_llm_hints": True,
            "metadata_fields": ["title", "summary", "tags", "topics", "keywords", "llm_hints"],
        }

        assert stats == expected_stats

    def test_get_enhancement_stats_partial_frontmatter(self, metadata_enhancer, document_with_partial_frontmatter):
        """Test getting enhancement statistics for document with partial frontmatter."""
        stats = metadata_enhancer.get_enhancement_stats(document_with_partial_frontmatter)

        expected_stats = {
            "has_frontmatter": True,
            "has_title": True,
            "has_summary": False,
            "tag_count": 2,
            "topic_count": 0,
            "keyword_count": 0,
            "has_llm_hints": False,
            "metadata_fields": ["title", "tags"],
        }

        assert stats == expected_stats

    def test_get_enhancement_stats_title_same_as_filename(self, metadata_enhancer):
        """Test enhancement statistics when title matches filename."""
        from datetime import datetime

        document = Document(
            file_path="/test/simple_guide.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "simple_guide.md",  # Must match full filename including extension
            },
        )

        stats = metadata_enhancer.get_enhancement_stats(document)

        # has_title should be False since title matches filename
        assert stats["has_title"] is False
        assert "title" in stats["metadata_fields"]  # But still tracked as having title field

    def test_enhance_document_empty_metadata_fields(self, metadata_enhancer):
        """Test enhancing document with empty metadata fields."""
        from datetime import datetime

        document = Document(
            file_path="/test/empty_fields.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "",
                "summary": "",
                "tags": [],
                "keywords": [],
                "topics": [],
                "llm_hints": "",
            },
        )

        content = "Document content."
        enhanced_content = metadata_enhancer.enhance_document_for_embedding(document, content)

        # When title is empty, it defaults to filename stem ("empty_fields") which != filename ("empty_fields.md")
        # So title will be included even though frontmatter title is empty
        assert "Title: empty_fields" in enhanced_content
        assert content in enhanced_content

    def test_enhance_section_empty_metadata_fields(self, metadata_enhancer, sample_section):
        """Test enhancing section with empty metadata fields."""
        from datetime import datetime

        document = Document(
            file_path="/test/empty_fields.md",
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=100,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
            frontmatter={
                "title": "",
                "tags": [],
                "keywords": [],
            },
        )

        enhanced_content = metadata_enhancer.enhance_section_for_embedding(document, sample_section)

        # Should contain section heading and content
        assert "Section: Technical Implementation" in enhanced_content
        assert sample_section.section_text in enhanced_content
        # When title is empty, it defaults to filename stem ("empty_fields") which != filename ("empty_fields.md")
        assert "Document: empty_fields" in enhanced_content
        # Empty tags and keywords should not appear
        assert "Tags:" not in enhanced_content
        assert "Keywords:" not in enhanced_content
