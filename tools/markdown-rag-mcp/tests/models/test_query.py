"""Unit tests for query models."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from markdown_rag_mcp.models import (
    OutputFormat,
    QueryResult,
    SearchRequest,
    SearchResponse,
    SortOrder,
)
from pydantic import ValidationError


class TestQueryResult:
    """Test cases for QueryResult model."""

    def test_create_valid_query_result(self):
        """Test creating a valid query result."""
        section_id = uuid4()
        doc_id = uuid4()

        result = QueryResult(
            section_text="This is a matching section about authentication",
            file_path="/path/to/document.md",
            confidence_score=0.85,
            section_heading="Authentication Setup",
            heading_level=2,
            chunk_index=3,
            metadata={"title": "API Guide", "tags": ["auth", "api"]},
            section_id=section_id,
            document_id=doc_id,
            start_position=100,
            end_position=200,
        )

        assert result.section_text == "This is a matching section about authentication"
        assert result.file_path == "/path/to/document.md"
        assert result.confidence_score == 0.85
        assert result.section_heading == "Authentication Setup"
        assert result.heading_level == 2
        assert result.chunk_index == 3
        assert result.metadata == {"title": "API Guide", "tags": ["auth", "api"]}
        assert result.section_id == section_id
        assert result.document_id == doc_id
        assert result.start_position == 100
        assert result.end_position == 200

    def test_query_result_computed_properties(self):
        """Test computed properties of QueryResult."""
        result = QueryResult(
            section_text="A" * 250,  # Long text for preview testing
            file_path="/path/to/my-document.md",
            confidence_score=0.75,
            chunk_index=0,
            metadata={"title": "My Document", "tags": ["test"], "summary": "Test doc"},
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=250,
        )

        assert result.filename == "my-document.md"
        assert result.content_preview == "A" * 200 + "..."  # Truncated at 200
        assert result.title == "My Document"
        assert result.tags == ["test"]
        assert result.summary == "Test doc"

        # Test short content (no truncation)
        short_result = QueryResult(
            section_text="Short text",
            file_path="/path/to/doc.md",
            confidence_score=0.8,
            chunk_index=0,
            metadata={},
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=10,
        )

        assert short_result.content_preview == "Short text"

    def test_query_result_computed_properties_defaults(self):
        """Test computed properties with missing metadata."""
        result = QueryResult(
            section_text="Test section",
            file_path="/path/to/doc.md",
            confidence_score=0.8,
            chunk_index=0,
            metadata={},  # Empty metadata
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=12,
        )

        assert result.title is None
        assert result.tags == []
        assert result.summary is None

        # Test with non-list tags
        result_string_tags = QueryResult(
            section_text="Test section",
            file_path="/path/to/doc.md",
            confidence_score=0.8,
            chunk_index=0,
            metadata={"tags": "not-a-list"},  # Non-list tags
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=12,
        )

        assert result_string_tags.tags == []

    def test_query_result_validation_confidence_score(self):
        """Test confidence score validation."""
        # Test valid scores
        valid_result = QueryResult(
            section_text="Test",
            file_path="/path/to/doc.md",
            confidence_score=0.5555,  # Should be rounded to 4 decimal places
            chunk_index=0,
            metadata={},
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=4,
        )
        assert valid_result.confidence_score == 0.5555

        # Test invalid scores
        with pytest.raises(ValidationError) as exc_info:
            QueryResult(
                section_text="Test",
                file_path="/path/to/doc.md",
                confidence_score=1.5,  # Invalid: > 1.0
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=4,
            )
        # Pydantic's built-in validation will trigger first
        assert "Input should be less than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            QueryResult(
                section_text="Test",
                file_path="/path/to/doc.md",
                confidence_score=-0.1,  # Invalid: < 0.0
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=4,
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_query_result_meets_threshold(self):
        """Test meets_threshold method."""
        result = QueryResult(
            section_text="Test",
            file_path="/path/to/doc.md",
            confidence_score=0.75,
            chunk_index=0,
            metadata={},
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=4,
        )

        assert result.meets_threshold(0.7) is True
        assert result.meets_threshold(0.75) is True
        assert result.meets_threshold(0.8) is False

    def test_query_result_str_representation(self):
        """Test string representation."""
        result = QueryResult(
            section_text="This is a test section for string representation",
            file_path="/path/to/doc.md",
            confidence_score=0.85,
            section_heading="Test Section",
            chunk_index=0,
            metadata={},
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=48,
        )

        str_repr = str(result)
        assert "0.850" in str_repr  # Score
        assert "[Test Section]" in str_repr  # Heading
        assert "This is a test section for string representation" in str_repr

        # Test without heading
        result_no_heading = QueryResult(
            section_text="Test without heading",
            file_path="/path/to/doc.md",
            confidence_score=0.75,
            chunk_index=0,
            metadata={},
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=20,
        )

        str_repr = str(result_no_heading)
        assert "0.750" in str_repr
        assert "Test without heading" in str_repr


class TestSearchRequest:
    """Test cases for SearchRequest model."""

    def test_create_valid_search_request(self):
        """Test creating a valid search request."""
        request = SearchRequest(
            query="authentication setup guide",
            limit=20,
            similarity_threshold=0.8,
            include_metadata=True,
            metadata_filters={"tags": "api"},
            sort_order=SortOrder.FILENAME,
            output_format=OutputFormat.JSON,
        )

        assert request.query == "authentication setup guide"
        assert request.limit == 20
        assert request.similarity_threshold == 0.8
        assert request.include_metadata is True
        assert request.metadata_filters == {"tags": "api"}
        assert request.sort_order == SortOrder.FILENAME
        assert request.output_format == OutputFormat.JSON
        assert isinstance(request.request_id, UUID)
        assert isinstance(request.timestamp, datetime)

    def test_search_request_defaults(self):
        """Test default values for SearchRequest."""
        request = SearchRequest(query="test query")

        assert request.query == "test query"
        assert request.limit == 10
        assert request.similarity_threshold == 0.4
        assert request.include_metadata is False
        assert request.metadata_filters == {}
        assert request.sort_order == SortOrder.RELEVANCE
        assert request.output_format == OutputFormat.JSON

    def test_search_request_validation_query(self):
        """Test query validation."""
        # Test empty query
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="")
        assert "String should have at least 1 character" in str(exc_info.value)

        # Test whitespace-only query
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="   \t\n   ")
        assert "Query cannot be empty or whitespace only" in str(exc_info.value)

        # Test query stripping
        request = SearchRequest(query="  test query  ")
        assert request.query == "test query"

    def test_search_request_validation_constraints(self):
        """Test field constraints."""
        # Test invalid limit
        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=0)  # Too low

        with pytest.raises(ValidationError):
            SearchRequest(query="test", limit=101)  # Too high

        # Test invalid similarity threshold
        with pytest.raises(ValidationError):
            SearchRequest(query="test", similarity_threshold=1.5)  # Too high

        with pytest.raises(ValidationError):
            SearchRequest(query="test", similarity_threshold=-0.1)  # Too low

    def test_search_request_validation_metadata_filters(self):
        """Test metadata filters validation."""
        # Valid filters
        request = SearchRequest(query="test", metadata_filters={"tags": ["api"], "author": "john"})
        assert request.metadata_filters == {"tags": ["api"], "author": "john"}

        # Invalid filters (not a dict)
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="test", metadata_filters="not-a-dict")
        assert "Input should be a valid dictionary" in str(exc_info.value)

    def test_search_request_computed_properties(self):
        """Test computed properties."""
        request = SearchRequest(query="python testing framework pytest", metadata_filters={"tags": ["python"]})

        assert request.query_tokens == ["python", "testing", "framework", "pytest"]
        assert request.has_filters is True

        # Test without filters
        request_no_filters = SearchRequest(query="simple query")
        assert request_no_filters.has_filters is False

    def test_search_request_str_representation(self):
        """Test string representation."""
        request = SearchRequest(query="test query", limit=15, similarity_threshold=0.8)

        str_repr = str(request)
        assert "test query" in str_repr
        assert "limit=15" in str_repr
        assert "threshold=0.8" in str_repr


class TestSearchResponse:
    """Test cases for SearchResponse model."""

    def test_create_valid_search_response(self):
        """Test creating a valid search response."""
        request = SearchRequest(query="test query")
        results = [
            QueryResult(
                section_text="Test result 1",
                file_path="/path/to/doc1.md",
                confidence_score=0.9,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=13,
            ),
            QueryResult(
                section_text="Test result 2",
                file_path="/path/to/doc2.md",
                confidence_score=0.8,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=13,
            ),
        ]

        response = SearchResponse(
            request=request,
            results=results,
            total_results=2,
            execution_time_ms=150,
            embedding_time_ms=50,
            search_time_ms=100,
            total_documents_searched=100,
            total_sections_searched=500,
            results_above_threshold=2,
        )

        assert response.request == request
        assert len(response.results) == 2
        assert response.total_results == 2
        assert response.execution_time_ms == 150
        assert response.embedding_time_ms == 50
        assert response.search_time_ms == 100
        assert response.total_documents_searched == 100
        assert response.total_sections_searched == 500
        assert response.results_above_threshold == 2
        assert isinstance(response.response_id, UUID)
        assert isinstance(response.timestamp, datetime)

    def test_search_response_computed_properties(self):
        """Test computed properties."""
        request = SearchRequest(query="test")
        results = [
            QueryResult(
                section_text="Result 1",
                file_path="/path/to/doc1.md",
                confidence_score=0.9,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=8,
            ),
            QueryResult(
                section_text="Result 2",
                file_path="/path/to/doc1.md",  # Same file
                confidence_score=0.7,
                chunk_index=1,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=10,
                end_position=18,
            ),
            QueryResult(
                section_text="Result 3",
                file_path="/path/to/doc2.md",  # Different file
                confidence_score=0.8,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=8,
            ),
        ]

        response = SearchResponse(
            request=request,
            results=results,
            total_results=3,
            execution_time_ms=100,
            embedding_time_ms=30,
            search_time_ms=70,
            total_documents_searched=50,
            total_sections_searched=200,
            results_above_threshold=3,
        )

        assert response.has_results is True
        assert response.average_confidence == pytest.approx(0.8)  # (0.9 + 0.7 + 0.8) / 3
        assert response.top_confidence == 0.9
        assert response.unique_documents == 2  # Two unique file paths

        # Test empty results
        empty_response = SearchResponse(
            request=request,
            results=[],
            total_results=0,
            execution_time_ms=50,
            embedding_time_ms=20,
            search_time_ms=30,
            total_documents_searched=50,
            total_sections_searched=200,
            results_above_threshold=0,
        )

        assert empty_response.has_results is False
        assert empty_response.average_confidence == 0.0
        assert empty_response.top_confidence == 0.0
        assert empty_response.unique_documents == 0

    def test_search_response_validation_results_count(self):
        """Test that results list matches total_results."""
        request = SearchRequest(query="test")
        results = [
            QueryResult(
                section_text="Result 1",
                file_path="/path/to/doc.md",
                confidence_score=0.8,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=8,
            )
        ]

        # Mismatch between results length and total_results
        with pytest.raises(ValidationError) as exc_info:
            SearchResponse(
                request=request,
                results=results,  # 1 result
                total_results=2,  # Says 2 results
                execution_time_ms=100,
                embedding_time_ms=30,
                search_time_ms=70,
                total_documents_searched=50,
                total_sections_searched=200,
                results_above_threshold=1,
            )
        assert "Length of results must match total_results" in str(exc_info.value)

    def test_search_response_filter_by_confidence(self):
        """Test filtering response by confidence threshold."""
        request = SearchRequest(query="test")
        results = [
            QueryResult(
                section_text="High confidence result",
                file_path="/path/to/doc1.md",
                confidence_score=0.9,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=22,
            ),
            QueryResult(
                section_text="Medium confidence result",
                file_path="/path/to/doc2.md",
                confidence_score=0.75,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=24,
            ),
            QueryResult(
                section_text="Low confidence result",
                file_path="/path/to/doc3.md",
                confidence_score=0.6,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=21,
            ),
        ]

        original_response = SearchResponse(
            request=request,
            results=results,
            total_results=3,
            execution_time_ms=100,
            embedding_time_ms=30,
            search_time_ms=70,
            total_documents_searched=50,
            total_sections_searched=200,
            results_above_threshold=3,
        )

        # Filter by confidence >= 0.8
        filtered_response = original_response.filter_by_confidence(0.8)

        assert len(filtered_response.results) == 1  # Only the 0.9 score result
        assert filtered_response.total_results == 1
        assert filtered_response.results_above_threshold == 1
        assert filtered_response.results[0].confidence_score == 0.9

        # Original response should be unchanged
        assert len(original_response.results) == 3

    def test_search_response_str_representation(self):
        """Test string representation."""
        request = SearchRequest(query="test")
        results = [
            QueryResult(
                section_text="Result",
                file_path="/path/to/doc.md",
                confidence_score=0.8,
                chunk_index=0,
                metadata={},
                section_id=uuid4(),
                document_id=uuid4(),
                start_position=0,
                end_position=6,
            )
        ]

        response = SearchResponse(
            request=request,
            results=results,
            total_results=1,
            execution_time_ms=150,
            embedding_time_ms=50,
            search_time_ms=100,
            total_documents_searched=50,
            total_sections_searched=200,
            results_above_threshold=1,
        )

        str_repr = str(response)
        assert "1 results" in str_repr
        assert "150ms" in str_repr
        assert "avg_confidence=0.800" in str_repr


class TestEnums:
    """Test cases for enums."""

    def test_output_format_enum(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.JSON == "json"
        assert OutputFormat.HUMAN == "human"
        assert OutputFormat.CSV == "csv"

    def test_sort_order_enum(self):
        """Test SortOrder enum values."""
        assert SortOrder.RELEVANCE == "relevance"
        assert SortOrder.FILENAME == "filename"
        assert SortOrder.DATE_MODIFIED == "date_modified"
        assert SortOrder.SECTION_ORDER == "section_order"
