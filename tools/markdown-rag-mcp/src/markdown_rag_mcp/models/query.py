"""
Data models for search queries and results.

These models handle query processing, result formatting, and search request
management for the RAG system.
"""

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class OutputFormat(str, Enum):
    """Output format enumeration for search results."""

    JSON = "json"
    HUMAN = "human"
    CSV = "csv"


class SortOrder(str, Enum):
    """Sort order enumeration for search results."""

    RELEVANCE = "relevance"  # Default: by confidence score descending
    FILENAME = "filename"
    DATE_MODIFIED = "date_modified"
    SECTION_ORDER = "section_order"


class QueryResult(BaseModel):
    """
    Represents a single search result matching a query.

    Contains the matched section content, metadata, and relevance scoring
    information for display to users or further processing.
    """

    section_text: str = Field(..., min_length=1, description="Matching section content")
    file_path: str = Field(..., min_length=1, description="Absolute path to source file")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    section_heading: str | None = Field(None, description="Heading context")
    heading_level: int | None = Field(None, ge=1, le=6, description="Heading level (H1-H6)")
    chunk_index: int = Field(..., ge=0, description="Position within document")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata from frontmatter")

    # Additional context fields
    section_id: UUID = Field(..., description="Unique section identifier")
    document_id: UUID = Field(..., description="Parent document identifier")
    start_position: int = Field(..., ge=0, description="Character start in document")
    end_position: int = Field(..., gt=0, description="Character end in document")

    @computed_field
    @property
    def filename(self) -> str:
        """Get the filename without path."""

        return Path(self.file_path).name

    @computed_field
    @property
    def content_preview(self) -> str:
        """Get a truncated preview of the section content."""
        max_length = 200
        if len(self.section_text) <= max_length:
            return self.section_text
        return self.section_text[:max_length] + "..."

    @computed_field
    @property
    def title(self) -> str | None:
        """Get document title from metadata."""
        return self.metadata.get('title')

    @computed_field
    @property
    def tags(self) -> list[str]:
        """Get document tags from metadata."""
        tags = self.metadata.get('tags', [])
        return tags if isinstance(tags, list) else []

    @computed_field
    @property
    def summary(self) -> str | None:
        """Get document summary from metadata."""
        return self.metadata.get('summary')

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        """Ensure confidence score is valid."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return round(v, 4)  # Round to 4 decimal places for consistency

    def meets_threshold(self, threshold: float) -> bool:
        """Check if result meets minimum confidence threshold."""
        return self.confidence_score >= threshold

    def __str__(self) -> str:
        """String representation showing score and content preview."""
        heading_info = f"[{self.section_heading}] " if self.section_heading else ""
        return f"Result({self.confidence_score:.3f}: {heading_info}{self.content_preview})"

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class SearchRequest(BaseModel):
    """
    Represents a search request with query parameters and options.

    Encapsulates all search parameters for consistent handling across
    the system and easier extension with additional search options.
    """

    query: str = Field(..., min_length=1, description="Natural language search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    similarity_threshold: float = Field(default=0.4, ge=0.0, le=1.0, description="Minimum similarity score")
    include_metadata: bool = Field(default=False, description="Include document metadata in results")
    metadata_filters: dict[str, Any] = Field(default_factory=dict, description="Metadata filtering criteria")
    sort_order: SortOrder = Field(default=SortOrder.RELEVANCE, description="Result sorting preference")
    output_format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format preference")

    # Request metadata
    request_id: UUID = Field(default_factory=uuid4, description="Unique request identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Request timestamp",
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate and clean the query string."""
        query = v.strip()
        if not query:
            raise ValueError("Query cannot be empty or whitespace only")
        return query

    @field_validator('metadata_filters')
    @classmethod
    def validate_metadata_filters(cls, v):
        """Validate metadata filter format."""
        if not isinstance(v, dict):
            raise ValueError("metadata_filters must be a dictionary")
        return v

    @computed_field
    @property
    def query_tokens(self) -> list[str]:
        """Get query split into tokens for analysis."""
        # Simple whitespace tokenization for now
        return [token.strip() for token in self.query.split() if token.strip()]

    @computed_field
    @property
    def has_filters(self) -> bool:
        """Check if request has metadata filters."""
        return bool(self.metadata_filters)

    def __str__(self) -> str:
        """String representation showing query and key parameters."""
        return f"SearchRequest('{self.query}', limit={self.limit}, threshold={self.similarity_threshold})"

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class SearchResponse(BaseModel):
    """
    Complete response to a search request including results and metadata.

    Provides structured response format with search statistics and
    execution information for debugging and analytics.
    """

    request: SearchRequest = Field(..., description="Original search request")
    results: list[QueryResult] = Field(..., description="Matching search results")

    # Response metadata
    total_results: int = Field(..., ge=0, description="Total results found")
    execution_time_ms: int = Field(..., ge=0, description="Query execution time in milliseconds")
    embedding_time_ms: int = Field(..., ge=0, description="Embedding generation time in milliseconds")
    search_time_ms: int = Field(..., ge=0, description="Vector search time in milliseconds")

    # Search statistics
    total_documents_searched: int = Field(..., ge=0, description="Documents in search scope")
    total_sections_searched: int = Field(..., ge=0, description="Sections in search scope")
    results_above_threshold: int = Field(..., ge=0, description="Results meeting threshold")

    response_id: UUID = Field(default_factory=uuid4, description="Unique response identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp",
    )

    @computed_field
    @property
    def has_results(self) -> bool:
        """Check if response contains any results."""
        return len(self.results) > 0

    @computed_field
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score of results."""
        if not self.results:
            return 0.0
        return sum(r.confidence_score for r in self.results) / len(self.results)

    @computed_field
    @property
    def top_confidence(self) -> float:
        """Get highest confidence score in results."""
        if not self.results:
            return 0.0
        return max(r.confidence_score for r in self.results)

    @computed_field
    @property
    def unique_documents(self) -> int:
        """Count unique documents in results."""
        return len({r.file_path for r in self.results})

    @model_validator(mode='after')
    def validate_results_count(self):
        """Ensure results list matches total_results count."""
        if len(self.results) != self.total_results:
            raise ValueError("Length of results must match total_results")
        return self

    def filter_by_confidence(self, min_confidence: float) -> 'SearchResponse':
        """Return new response with results filtered by confidence threshold."""
        filtered_results = [r for r in self.results if r.confidence_score >= min_confidence]

        # Create new response with filtered results
        return SearchResponse(
            request=self.request,
            results=filtered_results,
            total_results=len(filtered_results),
            execution_time_ms=self.execution_time_ms,
            embedding_time_ms=self.embedding_time_ms,
            search_time_ms=self.search_time_ms,
            total_documents_searched=self.total_documents_searched,
            total_sections_searched=self.total_sections_searched,
            results_above_threshold=len(filtered_results),
        )

    def __str__(self) -> str:
        """String representation showing key response statistics."""
        return (
            f"SearchResponse({self.total_results} results, "
            f"{self.execution_time_ms}ms, "
            f"avg_confidence={self.average_confidence:.3f})"
        )

    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
