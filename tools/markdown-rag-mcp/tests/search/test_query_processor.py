"""
Unit tests for QueryProcessor.

Tests the query processing functionality including search coordination,
query preprocessing, result post-processing, and metadata filtering.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.models import QueryResult, SearchError, SearchRequest
from markdown_rag_mcp.search import QueryProcessor


class TestQueryProcessor:
    """Test cases for QueryProcessor."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test configuration
        self.config = RAGConfig()

        # Mock embedding provider
        self.mock_embedding_provider = MagicMock()
        self.mock_embedding_provider.generate_embedding = AsyncMock()

        # Mock vector store
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.search_similar = AsyncMock()

        # Create QueryProcessor instance
        self.processor = QueryProcessor(
            config=self.config, embedding_provider=self.mock_embedding_provider, vector_store=self.mock_vector_store
        )

    def test_initialization(self):
        """Test QueryProcessor initialization."""
        assert self.processor.config == self.config
        assert self.processor.embedding_provider == self.mock_embedding_provider
        assert self.processor.vector_store == self.mock_vector_store

    def create_sample_query_result(self, confidence_score=0.8, metadata=None):
        """Create a sample QueryResult for testing."""
        if metadata is None:
            metadata = {"title": "Test Document", "tags": ["test"]}

        return QueryResult(
            section_text="This is test content for the document section.",
            file_path="/test/path/document.md",
            confidence_score=confidence_score,
            section_heading="Test Heading",
            heading_level=1,
            chunk_index=0,
            metadata=metadata,
            section_id=uuid4(),
            document_id=uuid4(),
            start_position=0,
            end_position=100,
        )

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful search operation."""
        # Setup
        query_text = "test query"
        search_request = SearchRequest(query=query_text, limit=5, similarity_threshold=0.4)

        # Mock embedding generation
        mock_embedding = [0.1, 0.2, 0.3, 0.4]
        self.mock_embedding_provider.generate_embedding.return_value = mock_embedding

        # Mock vector store results
        mock_results = [
            self.create_sample_query_result(confidence_score=0.9),
            self.create_sample_query_result(confidence_score=0.7),
            self.create_sample_query_result(confidence_score=0.5),
        ]
        self.mock_vector_store.search_similar.return_value = mock_results

        # Execute
        results = await self.processor.search(search_request)

        # Verify
        assert len(results) == 3
        assert all(isinstance(r, QueryResult) for r in results)

        # Verify embedding provider was called with preprocessed query
        self.mock_embedding_provider.generate_embedding.assert_called_once_with("test query")

        # Verify vector store was called with correct parameters
        self.mock_vector_store.search_similar.assert_called_once_with(
            query_embedding=mock_embedding, limit=5, similarity_threshold=0.4, metadata_filters={}
        )

        # Verify results are sorted by confidence score (descending)
        assert results[0].confidence_score >= results[1].confidence_score >= results[2].confidence_score

    @pytest.mark.asyncio
    async def test_search_with_metadata_filters(self):
        """Test search with metadata filters."""
        # Setup
        metadata_filters = {"tags": ["python"], "category": "tutorial"}
        search_request = SearchRequest(
            query="test query", limit=3, similarity_threshold=0.4, metadata_filters=metadata_filters
        )

        # Mock embedding generation
        mock_embedding = [0.1, 0.2, 0.3, 0.4]
        self.mock_embedding_provider.generate_embedding.return_value = mock_embedding

        # Mock vector store results - some match filters, some don't
        mock_results = [
            self.create_sample_query_result(
                confidence_score=0.9, metadata={"tags": ["python", "tutorial"], "category": "tutorial"}
            ),
            self.create_sample_query_result(
                confidence_score=0.8, metadata={"tags": ["javascript"], "category": "tutorial"}  # No python tag
            ),
            self.create_sample_query_result(
                confidence_score=0.7, metadata={"tags": ["python"], "category": "reference"}  # Wrong category
            ),
            self.create_sample_query_result(
                confidence_score=0.6, metadata={"tags": ["python"], "category": "tutorial"}
            ),
        ]
        self.mock_vector_store.search_similar.return_value = mock_results

        # Execute
        results = await self.processor.search(search_request)

        # Verify - only results matching all filters should be included
        assert len(results) == 2
        assert results[0].confidence_score == 0.9
        assert results[1].confidence_score == 0.6

        # Verify all results have correct metadata
        for result in results:
            assert "python" in result.metadata["tags"]
            assert result.metadata["category"] == "tutorial"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search returning no results."""
        # Setup
        search_request = SearchRequest(query="nonexistent query")

        # Mock embedding generation
        self.mock_embedding_provider.generate_embedding.return_value = [0.1, 0.2]

        # Mock empty vector store results
        self.mock_vector_store.search_similar.return_value = []

        # Execute
        results = await self.processor.search(search_request)

        # Verify
        assert len(results) == 0
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_embedding_error(self):
        """Test search when embedding generation fails."""
        # Setup
        search_request = SearchRequest(query="test query")

        # Mock embedding provider to raise error
        embedding_error = RuntimeError("Embedding generation failed")
        self.mock_embedding_provider.generate_embedding.side_effect = embedding_error

        # Execute and verify error
        with pytest.raises(SearchError) as exc_info:
            await self.processor.search(search_request)

        assert "Failed to process search query" in str(exc_info.value)
        assert exc_info.value.context["query"] == "test query"
        assert exc_info.value.context["search_stage"] == "query_processing"

    @pytest.mark.asyncio
    async def test_search_vector_store_error(self):
        """Test search when vector store search fails."""
        # Setup
        search_request = SearchRequest(query="test query")

        # Mock successful embedding generation
        self.mock_embedding_provider.generate_embedding.return_value = [0.1, 0.2]

        # Mock vector store to raise error
        vector_error = RuntimeError("Vector search failed")
        self.mock_vector_store.search_similar.side_effect = vector_error

        # Execute and verify error
        with pytest.raises(SearchError) as exc_info:
            await self.processor.search(search_request)

        assert "Failed to process search query" in str(exc_info.value)
        assert exc_info.value.context["query"] == "test query"

    def test_preprocess_query_basic(self):
        """Test basic query preprocessing."""
        # Test whitespace trimming
        assert self.processor._preprocess_query("  test query  ") == "test query"

        # Test multiple whitespace normalization
        assert self.processor._preprocess_query("test    query   with   spaces") == "test query with spaces"

        # Test newlines and tabs
        assert self.processor._preprocess_query("test\nquery\t\twith\nspecial") == "test query with special"

        # Test empty string
        assert self.processor._preprocess_query("") == ""

        # Test only whitespace
        assert self.processor._preprocess_query("   \n\t   ") == ""

    def test_post_process_results_sorting(self):
        """Test post-processing results sorting."""
        # Setup unsorted results
        results = [
            self.create_sample_query_result(confidence_score=0.5),
            self.create_sample_query_result(confidence_score=0.9),
            self.create_sample_query_result(confidence_score=0.7),
        ]

        search_request = SearchRequest(query="test", limit=10)

        # Execute
        processed = self.processor._post_process_results(results, search_request)

        # Verify sorting (descending by confidence)
        assert len(processed) == 3
        assert processed[0].confidence_score == 0.9
        assert processed[1].confidence_score == 0.7
        assert processed[2].confidence_score == 0.5

    def test_post_process_results_limit(self):
        """Test post-processing results limiting."""
        # Setup more results than limit
        results = [
            self.create_sample_query_result(confidence_score=0.9),
            self.create_sample_query_result(confidence_score=0.8),
            self.create_sample_query_result(confidence_score=0.7),
            self.create_sample_query_result(confidence_score=0.6),
            self.create_sample_query_result(confidence_score=0.5),
        ]

        search_request = SearchRequest(query="test", limit=3)

        # Execute
        processed = self.processor._post_process_results(results, search_request)

        # Verify limiting - should get top 3 results
        assert len(processed) == 3
        assert processed[0].confidence_score == 0.9
        assert processed[1].confidence_score == 0.8
        assert processed[2].confidence_score == 0.7

    def test_post_process_results_with_filters(self):
        """Test post-processing with metadata filters."""
        # Setup results with different metadata
        results = [
            self.create_sample_query_result(
                confidence_score=0.9, metadata={"category": "tutorial", "tags": ["python"]}
            ),
            self.create_sample_query_result(
                confidence_score=0.8, metadata={"category": "reference", "tags": ["javascript"]}
            ),
            self.create_sample_query_result(
                confidence_score=0.7, metadata={"category": "tutorial", "tags": ["python", "web"]}
            ),
        ]

        search_request = SearchRequest(query="test", limit=10, metadata_filters={"category": "tutorial"})

        # Execute
        processed = self.processor._post_process_results(results, search_request)

        # Verify filtering - only tutorial category should remain
        assert len(processed) == 2
        assert all(r.metadata["category"] == "tutorial" for r in processed)
        assert processed[0].confidence_score == 0.9
        assert processed[1].confidence_score == 0.7

    def test_apply_metadata_filters_no_filters(self):
        """Test metadata filtering with empty filters."""
        results = [self.create_sample_query_result()]
        filtered = self.processor._apply_metadata_filters(results, {})

        assert filtered == results

    def test_apply_metadata_filters_single_value(self):
        """Test metadata filtering with single value filters."""
        results = [
            self.create_sample_query_result(metadata={"category": "tutorial"}),
            self.create_sample_query_result(metadata={"category": "reference"}),
            self.create_sample_query_result(metadata={"category": "tutorial"}),
        ]

        filters = {"category": "tutorial"}
        filtered = self.processor._apply_metadata_filters(results, filters)

        assert len(filtered) == 2
        assert all(r.metadata["category"] == "tutorial" for r in filtered)

    def test_apply_metadata_filters_list_value(self):
        """Test metadata filtering with list value filters."""
        results = [
            self.create_sample_query_result(metadata={"tags": ["python", "web"]}),
            self.create_sample_query_result(metadata={"tags": ["javascript"]}),
            self.create_sample_query_result(metadata={"tags": ["python", "api"]}),
        ]

        # Filter for documents that have either python or javascript tags
        filters = {"tags": ["python", "javascript"]}
        filtered = self.processor._apply_metadata_filters(results, filters)

        assert len(filtered) == 3  # All should match since they have at least one tag from the filter

    def test_apply_metadata_filters_mixed_types(self):
        """Test metadata filtering with mixed filter types."""
        results = [
            self.create_sample_query_result(metadata={"category": "tutorial", "tags": ["python"]}),
            self.create_sample_query_result(metadata={"category": "reference", "tags": ["python"]}),
            self.create_sample_query_result(metadata={"category": "tutorial", "tags": ["javascript"]}),
        ]

        filters = {"category": "tutorial", "tags": ["python"]}
        filtered = self.processor._apply_metadata_filters(results, filters)

        assert len(filtered) == 1
        assert filtered[0].metadata["category"] == "tutorial"
        assert "python" in filtered[0].metadata["tags"]

    def test_matches_filters_missing_metadata(self):
        """Test filter matching when metadata is missing."""
        metadata = {"category": "tutorial"}
        filters = {"category": "tutorial", "missing_field": "value"}

        # Should return False if any filter key is missing from metadata
        assert not self.processor._matches_filters(metadata, filters)

    def test_matches_filters_single_values(self):
        """Test filter matching with single values."""
        metadata = {"category": "tutorial", "author": "john"}
        filters = {"category": "tutorial"}

        assert self.processor._matches_filters(metadata, filters)

        # Test non-matching
        filters = {"category": "reference"}
        assert not self.processor._matches_filters(metadata, filters)

    def test_matches_filters_list_metadata_single_filter(self):
        """Test filter matching with list metadata and single filter value."""
        metadata = {"tags": ["python", "web", "tutorial"]}
        filters = {"tags": "python"}  # Single value filter

        # Current implementation does exact match, so list != single value
        assert not self.processor._matches_filters(metadata, filters)

        # Test with single value metadata that matches
        metadata = {"category": "python"}
        assert self.processor._matches_filters(metadata, {"category": "python"})

    def test_matches_filters_single_metadata_list_filter(self):
        """Test filter matching with single metadata and list filter value."""
        metadata = {"category": "tutorial"}
        filters = {"category": ["tutorial", "reference"]}  # List filter

        assert self.processor._matches_filters(metadata, filters)

        # Test non-matching
        filters = {"category": ["guide", "reference"]}
        assert not self.processor._matches_filters(metadata, filters)

    def test_matches_filters_both_lists(self):
        """Test filter matching with both metadata and filter as lists."""
        metadata = {"tags": ["python", "web", "tutorial"]}
        filters = {"tags": ["python", "api"]}  # List filter

        # Should match because there's intersection (python)
        assert self.processor._matches_filters(metadata, filters)

        # Test non-matching
        filters = {"tags": ["javascript", "mobile"]}
        assert not self.processor._matches_filters(metadata, filters)

    def test_matches_filters_empty_lists(self):
        """Test filter matching with empty lists."""
        metadata = {"tags": []}
        filters = {"tags": ["python"]}

        # Empty metadata list should not match non-empty filter
        assert not self.processor._matches_filters(metadata, filters)

        # Empty filter list should not match anything
        metadata = {"tags": ["python"]}
        filters = {"tags": []}
        assert not self.processor._matches_filters(metadata, filters)

    def test_matches_filters_complex_scenario(self):
        """Test filter matching with complex metadata scenario."""
        metadata = {
            "category": "tutorial",
            "tags": ["python", "web", "beginner"],
            "author": "john_doe",
            "difficulty": "easy",
        }

        # All filters should match
        filters = {"category": "tutorial", "tags": ["python"], "difficulty": "easy"}
        assert self.processor._matches_filters(metadata, filters)

        # One filter doesn't match
        filters = {"category": "tutorial", "tags": ["python"], "difficulty": "hard"}  # Doesn't match
        assert not self.processor._matches_filters(metadata, filters)

    @pytest.mark.asyncio
    async def test_search_request_validation(self):
        """Test search with various SearchRequest configurations."""
        # Test with custom limit and threshold
        search_request = SearchRequest(query="test query", limit=1, similarity_threshold=0.8)

        # Mock responses
        self.mock_embedding_provider.generate_embedding.return_value = [0.1, 0.2]
        mock_results = [
            self.create_sample_query_result(confidence_score=0.9),
            self.create_sample_query_result(confidence_score=0.7),
        ]
        self.mock_vector_store.search_similar.return_value = mock_results

        # Execute
        results = await self.processor.search(search_request)

        # Verify limit was applied
        assert len(results) == 1

        # Verify vector store was called with correct threshold
        self.mock_vector_store.search_similar.assert_called_once_with(
            query_embedding=[0.1, 0.2], limit=1, similarity_threshold=0.8, metadata_filters={}
        )

    @pytest.mark.asyncio
    async def test_search_unicode_query(self):
        """Test search with Unicode characters in query."""
        # Setup Unicode query
        unicode_query = "测试查询 français español 🚀"
        search_request = SearchRequest(query=unicode_query)

        # Mock responses
        self.mock_embedding_provider.generate_embedding.return_value = [0.1, 0.2]
        self.mock_vector_store.search_similar.return_value = []

        # Execute - should not raise any encoding errors
        results = await self.processor.search(search_request)

        # Verify embedding provider was called with processed Unicode query
        self.mock_embedding_provider.generate_embedding.assert_called_once_with(unicode_query)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_very_long_query(self):
        """Test search with very long query."""
        # Create a very long query
        long_query = "word " * 1000  # 5000 characters
        search_request = SearchRequest(query=long_query.strip())

        # Mock responses
        self.mock_embedding_provider.generate_embedding.return_value = [0.1, 0.2]
        self.mock_vector_store.search_similar.return_value = []

        # Execute - should handle long queries without issues
        results = await self.processor.search(search_request)

        # Verify preprocessing handled the long query
        expected_processed = " ".join(["word"] * 1000)
        self.mock_embedding_provider.generate_embedding.assert_called_once_with(expected_processed)
        assert results == []

    def test_processor_state_consistency(self):
        """Test that processor maintains consistent state across operations."""
        # Verify initial state
        assert self.processor.config == self.config
        assert self.processor.embedding_provider == self.mock_embedding_provider
        assert self.processor.vector_store == self.mock_vector_store

        # Create a second processor instance
        processor2 = QueryProcessor(
            config=self.config, embedding_provider=self.mock_embedding_provider, vector_store=self.mock_vector_store
        )

        # Verify both instances are independent but use same dependencies
        assert processor2.config == self.processor.config
        assert processor2.embedding_provider == self.processor.embedding_provider
        assert processor2.vector_store == self.processor.vector_store
        assert processor2 is not self.processor
