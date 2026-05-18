"""
Data models for documents and document sections.

These models represent the core data structures used throughout the RAG system
for document processing, storage, and retrieval.
"""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class ProcessingStatus(str, Enum):
    """Document processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class SectionType(str, Enum):
    """Document section type enumeration."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST = "list"
    TABLE = "table"
    QUOTE = "quote"


class DocumentSection(BaseModel):
    """
    Represents a chunk of content from a document.

    Document sections are created by splitting documents at heading boundaries
    with size limits to ensure they fit within embedding model context windows.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique section identifier")
    document_id: UUID = Field(..., description="Parent document identifier")
    section_text: str = Field(..., min_length=1, description="Processed text content")
    heading: str | None = Field(None, description="Section heading if present")
    heading_level: int | None = Field(None, ge=1, le=6, description="Heading level (H1=1, H2=2, etc.)")
    chunk_index: int = Field(..., ge=0, description="Order within document")
    token_count: int = Field(..., ge=0, le=1000, description="Approximate token count")
    start_position: int = Field(..., ge=0, description="Character start in document")
    end_position: int = Field(..., gt=0, description="Character end in document")
    section_type: SectionType = Field(default=SectionType.PARAGRAPH, description="Type of content section")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Section creation timestamp",
    )

    @field_validator('end_position')
    @classmethod
    def validate_positions(cls, v, info):
        """Ensure end_position is greater than start_position."""
        if info.data and 'start_position' in info.data and v <= info.data['start_position']:
            raise ValueError("end_position must be greater than start_position")
        return v

    @computed_field
    @property
    def content_length(self) -> int:
        """Get the character length of the section text."""
        return len(self.section_text)

    @computed_field
    @property
    def position_span(self) -> int:
        """Get the character span covered by this section."""
        return self.end_position - self.start_position

    def __str__(self) -> str:
        """String representation showing heading and content preview."""
        heading_info = f"[{self.heading}] " if self.heading else ""
        preview = self.section_text[:100] + "..." if len(self.section_text) > 100 else self.section_text
        return f"Section({heading_info}{preview})"

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class Document(BaseModel):
    """
    Represents a markdown document with metadata and processing information.

    Documents are the top-level entities that contain multiple DocumentSections
    after processing and chunking.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique document identifier")
    file_path: str = Field(..., min_length=1, description="Absolute path to file")
    content_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 content hash")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    created_at: datetime = Field(..., description="File creation timestamp")
    modified_at: datetime = Field(..., description="File last modification timestamp")
    indexed_at: datetime | None = Field(None, description="When the file was last processed")
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING, description="Current processing state"
    )
    error_message: str | None = Field(None, description="Error details if processing failed")
    frontmatter: dict[str, Any] = Field(default_factory=dict, description="Parsed YAML frontmatter")
    word_count: int = Field(default=0, ge=0, description="Total word count")
    section_count: int = Field(default=0, ge=0, description="Number of sections created")

    # Computed fields from frontmatter
    @computed_field
    @property
    def title(self) -> str | None:
        """Get document title from frontmatter or filename."""
        if title := self.frontmatter.get('title'):
            return str(title)
        return Path(self.file_path).stem

    @computed_field
    @property
    def tags(self) -> list[str]:
        """Get document tags from frontmatter."""
        tags = self.frontmatter.get('tags', [])
        if isinstance(tags, list):
            return [str(tag) for tag in tags]
        elif isinstance(tags, str):
            return [tag.strip() for tag in tags.split(',')]
        return []

    @computed_field
    @property
    def topics(self) -> list[str]:
        """Get document topics from frontmatter."""
        topics = self.frontmatter.get('topics', [])
        if isinstance(topics, list):
            return [str(topic) for topic in topics]
        elif isinstance(topics, str):
            return [topic.strip() for topic in topics.split(',')]
        return []

    @computed_field
    @property
    def summary(self) -> str | None:
        """Get document summary from frontmatter."""
        if summary := self.frontmatter.get('summary'):
            return str(summary)
        return None

    @computed_field
    @property
    def llm_hints(self) -> str | None:
        """Get LLM hints from frontmatter."""
        if hints := self.frontmatter.get('llm_hints'):
            return str(hints)
        return None

    @computed_field
    @property
    def keywords(self) -> list[str]:
        """Get document keywords from frontmatter."""
        keywords = self.frontmatter.get('keywords', [])
        if isinstance(keywords, list):
            return [str(keyword) for keyword in keywords]
        elif isinstance(keywords, str):
            return [kw.strip() for kw in keywords.split(',')]
        return []

    @computed_field
    @property
    def has_frontmatter(self) -> bool:
        """Check if document has any frontmatter data."""
        return bool(self.frontmatter)

    @computed_field
    @property
    def language(self) -> str:
        """Get document language from frontmatter or default to English."""
        return str(self.frontmatter.get('language', 'en'))

    @computed_field
    @property
    def filename(self) -> str:
        """Get the filename without path."""
        return Path(self.file_path).name

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v):
        """Ensure file path is absolute."""
        if not Path(v).is_absolute():
            raise ValueError("file_path must be an absolute path")
        return v

    @field_validator('content_hash')
    @classmethod
    def validate_content_hash(cls, v):
        """Ensure content hash is valid SHA-256."""
        if not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError("content_hash must be a valid SHA-256 hex string")
        return v.lower()

    def is_processing_complete(self) -> bool:
        """Check if document processing is complete (success or failure)."""
        return self.processing_status in (
            ProcessingStatus.INDEXED,
            ProcessingStatus.FAILED,
        )

    def is_indexed(self) -> bool:
        """Check if document is successfully indexed."""
        return self.processing_status == ProcessingStatus.INDEXED

    def mark_as_processing(self) -> None:
        """Mark document as currently being processed."""
        self.processing_status = ProcessingStatus.PROCESSING
        self.error_message = None

    def mark_as_indexed(self, section_count: int, word_count: int) -> None:
        """Mark document as successfully indexed."""
        self.processing_status = ProcessingStatus.INDEXED
        self.indexed_at = datetime.now(UTC)
        self.section_count = section_count
        self.word_count = word_count
        self.error_message = None

    def mark_as_failed(self, error_message: str) -> None:
        """Mark document as failed with error message."""
        self.processing_status = ProcessingStatus.FAILED
        self.error_message = error_message
        self.indexed_at = None

    def __str__(self) -> str:
        """String representation showing title and status."""
        return f"Document({self.title}, {self.processing_status.value}, {self.section_count} sections)"

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
