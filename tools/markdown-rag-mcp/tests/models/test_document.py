"""Unit tests for document models."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from markdown_rag_mcp.models import (
    Document,
    DocumentSection,
    ProcessingStatus,
    SectionType,
)
from pydantic import ValidationError


class TestDocumentSection:
    """Test cases for DocumentSection model."""

    def test_create_valid_section(self):
        """Test creating a valid document section."""
        doc_id = uuid4()
        section = DocumentSection(
            document_id=doc_id,
            section_text="This is a test section",
            heading="Test Heading",
            heading_level=2,
            chunk_index=0,
            token_count=50,
            start_position=0,
            end_position=23,
            section_type=SectionType.HEADING,
        )

        assert section.document_id == doc_id
        assert section.section_text == "This is a test section"
        assert section.heading == "Test Heading"
        assert section.heading_level == 2
        assert section.chunk_index == 0
        assert section.token_count == 50
        assert section.start_position == 0
        assert section.end_position == 23
        assert section.section_type == SectionType.HEADING
        assert isinstance(section.id, UUID)
        assert isinstance(section.created_at, datetime)

    def test_section_computed_properties(self):
        """Test computed properties of DocumentSection."""
        section = DocumentSection(
            document_id=uuid4(),
            section_text="This is a test section with more content",
            chunk_index=0,
            token_count=50,
            start_position=10,
            end_position=60,
        )

        assert section.content_length == 40
        assert section.position_span == 50

    def test_section_validation_end_position_greater_than_start(self):
        """Test that end_position must be greater than start_position."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentSection(
                document_id=uuid4(),
                section_text="Test",
                chunk_index=0,
                token_count=10,
                start_position=50,
                end_position=30,  # Invalid: less than start_position
            )

        assert "end_position must be greater than start_position" in str(exc_info.value)

    def test_section_validation_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            DocumentSection()  # Missing required fields

    def test_section_validation_constraints(self):
        """Test field constraints."""
        doc_id = uuid4()

        # Test empty section text
        with pytest.raises(ValidationError):
            DocumentSection(
                document_id=doc_id,
                section_text="",  # Invalid: empty string
                chunk_index=0,
                token_count=10,
                start_position=0,
                end_position=10,
            )

        # Test negative chunk_index
        with pytest.raises(ValidationError):
            DocumentSection(
                document_id=doc_id,
                section_text="Test",
                chunk_index=-1,  # Invalid: negative
                token_count=10,
                start_position=0,
                end_position=10,
            )

        # Test invalid heading level
        with pytest.raises(ValidationError):
            DocumentSection(
                document_id=doc_id,
                section_text="Test",
                heading_level=7,  # Invalid: > 6
                chunk_index=0,
                token_count=10,
                start_position=0,
                end_position=10,
            )

        # Test token count too high
        with pytest.raises(ValidationError):
            DocumentSection(
                document_id=doc_id,
                section_text="Test",
                chunk_index=0,
                token_count=1001,  # Invalid: > 1000
                start_position=0,
                end_position=10,
            )

    def test_section_str_representation(self):
        """Test string representation."""
        section = DocumentSection(
            document_id=uuid4(),
            section_text="This is a test section",
            heading="Test Heading",
            chunk_index=0,
            token_count=50,
            start_position=0,
            end_position=22,
        )

        str_repr = str(section)
        assert "[Test Heading]" in str_repr
        assert "This is a test section" in str_repr

        # Test without heading
        section_no_heading = DocumentSection(
            document_id=uuid4(),
            section_text="This is a test section without heading",
            chunk_index=0,
            token_count=50,
            start_position=0,
            end_position=38,
        )

        str_repr = str(section_no_heading)
        assert "This is a test section without heading" in str_repr

    def test_section_defaults(self):
        """Test default values."""
        section = DocumentSection(
            document_id=uuid4(),
            section_text="Test",
            chunk_index=0,
            token_count=10,
            start_position=0,
            end_position=4,
        )

        assert section.section_type == SectionType.PARAGRAPH
        assert section.heading is None
        assert section.heading_level is None


class TestDocument:
    """Test cases for Document model."""

    def test_create_valid_document(self):
        """Test creating a valid document."""
        now = datetime.now(UTC)
        doc = Document(
            file_path="/absolute/path/to/test.md",
            content_hash="a" * 64,  # Valid SHA-256 hash
            file_size=1024,
            created_at=now,
            modified_at=now,
            frontmatter={"title": "Test Document", "tags": ["test", "example"]},
            word_count=100,
            section_count=5,
        )

        assert doc.file_path == "/absolute/path/to/test.md"
        assert doc.content_hash == "a" * 64
        assert doc.file_size == 1024
        assert doc.created_at == now
        assert doc.modified_at == now
        assert doc.processing_status == ProcessingStatus.PENDING
        assert doc.word_count == 100
        assert doc.section_count == 5
        assert isinstance(doc.id, UUID)

    def test_document_computed_properties_from_frontmatter(self):
        """Test computed properties derived from frontmatter."""
        doc = Document(
            file_path="/absolute/path/to/test.md",
            content_hash="a" * 64,
            file_size=1024,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
            frontmatter={
                "title": "Test Document",
                "tags": ["python", "testing"],
                "topics": "api,documentation",  # String format
                "summary": "A test document for unit testing",
                "llm_hints": "Focus on testing patterns",
                "keywords": ["unittest", "pytest"],
                "language": "en",
            },
        )

        assert doc.title == "Test Document"
        assert doc.tags == ["python", "testing"]
        assert doc.topics == ["api", "documentation"]  # Parsed from string
        assert doc.summary == "A test document for unit testing"
        assert doc.llm_hints == "Focus on testing patterns"
        assert doc.keywords == ["unittest", "pytest"]
        assert doc.language == "en"
        assert doc.has_frontmatter is True

    def test_document_computed_properties_defaults(self):
        """Test computed properties with default values."""
        doc = Document(
            file_path="/absolute/path/to/test.md",
            content_hash="b" * 64,
            file_size=1024,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
        )

        assert doc.title == "test"  # From filename
        assert doc.tags == []
        assert doc.topics == []
        assert doc.summary is None
        assert doc.llm_hints is None
        assert doc.keywords == []
        assert doc.language == "en"  # Default
        assert doc.has_frontmatter is False

    def test_document_computed_filename(self):
        """Test filename computed property."""
        doc = Document(
            file_path="/absolute/path/to/my-document.md",
            content_hash="c" * 64,
            file_size=1024,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
        )

        assert doc.filename == "my-document.md"

    def test_document_validation_file_path(self):
        """Test file path validation."""
        now = datetime.now(UTC)

        # Test non-absolute path
        with pytest.raises(ValidationError) as exc_info:
            Document(
                file_path="relative/path.md",  # Invalid: not absolute
                content_hash="d" * 64,
                file_size=1024,
                created_at=now,
                modified_at=now,
            )

        assert "file_path must be an absolute path" in str(exc_info.value)

    def test_document_validation_content_hash(self):
        """Test content hash validation."""
        now = datetime.now(UTC)

        # Test invalid hash length
        with pytest.raises(ValidationError):
            Document(
                file_path="/absolute/path/to/test.md",
                content_hash="short",  # Invalid: wrong length
                file_size=1024,
                created_at=now,
                modified_at=now,
            )

        # Test invalid hash characters
        with pytest.raises(ValidationError) as exc_info:
            Document(
                file_path="/absolute/path/to/test.md",
                content_hash="g" * 64,  # Invalid: 'g' not hex
                file_size=1024,
                created_at=now,
                modified_at=now,
            )

        assert "content_hash must be a valid SHA-256 hex string" in str(exc_info.value)

        # Test valid hash is lowercased
        doc = Document(
            file_path="/absolute/path/to/test.md",
            content_hash="A" * 64,  # Uppercase
            file_size=1024,
            created_at=now,
            modified_at=now,
        )
        assert doc.content_hash == "a" * 64  # Should be lowercased

    def test_document_processing_status_methods(self):
        """Test processing status methods."""
        doc = Document(
            file_path="/absolute/path/to/test.md",
            content_hash="e" * 64,
            file_size=1024,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
        )

        # Initial state
        assert doc.processing_status == ProcessingStatus.PENDING
        assert not doc.is_processing_complete()
        assert not doc.is_indexed()

        # Mark as processing
        doc.mark_as_processing()
        assert doc.processing_status == ProcessingStatus.PROCESSING
        assert not doc.is_processing_complete()
        assert not doc.is_indexed()
        assert doc.error_message is None

        # Mark as indexed
        doc.mark_as_indexed(section_count=5, word_count=100)
        assert doc.processing_status == ProcessingStatus.INDEXED
        assert doc.is_processing_complete()
        assert doc.is_indexed()
        assert doc.section_count == 5
        assert doc.word_count == 100
        assert doc.error_message is None
        assert doc.indexed_at is not None

        # Mark as failed
        doc.mark_as_failed("Test error message")
        assert doc.processing_status == ProcessingStatus.FAILED
        assert doc.is_processing_complete()
        assert not doc.is_indexed()
        assert doc.error_message == "Test error message"
        assert doc.indexed_at is None

    def test_document_str_representation(self):
        """Test string representation."""
        doc = Document(
            file_path="/absolute/path/to/test.md",
            content_hash="f" * 64,
            file_size=1024,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
            frontmatter={"title": "Test Document"},
            section_count=3,
        )

        str_repr = str(doc)
        assert "Test Document" in str_repr
        assert "pending" in str_repr
        assert "3 sections" in str_repr


class TestEnums:
    """Test cases for enums."""

    def test_processing_status_enum(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.INDEXED == "indexed"
        assert ProcessingStatus.FAILED == "failed"

    def test_section_type_enum(self):
        """Test SectionType enum values."""
        assert SectionType.HEADING == "heading"
        assert SectionType.PARAGRAPH == "paragraph"
        assert SectionType.CODE_BLOCK == "code_block"
        assert SectionType.LIST == "list"
        assert SectionType.TABLE == "table"
        assert SectionType.QUOTE == "quote"
