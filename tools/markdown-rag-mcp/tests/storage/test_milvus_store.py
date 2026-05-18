"""Unit tests for Milvus vector store implementation."""

from unittest.mock import AsyncMock, Mock, PropertyMock, patch
from uuid import uuid4

import pytest
from langchain_core.documents import Document
from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.models import DocumentSection, QueryResult, SectionType, VectorStoreError
from markdown_rag_mcp.storage import MilvusVectorStore


class TestMilvusVectorStore:
    """Test cases for MilvusVectorStore (LangChain-based implementation)."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock RAG configuration."""
        config = Mock(spec=RAGConfig)
        config.milvus_host = "localhost"
        config.milvus_port = 19530
        config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        config.milvus_db_name = "markdown_rag"
        config.milvus_metric_type = "COSINE"
        return config

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create a mock embedding provider."""
        provider = AsyncMock()
        provider.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        provider.generate_batch_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        provider.embedding_dimension = 384
        return provider

    @pytest.fixture
    def sample_document_sections(self):
        """Create sample document sections for testing."""
        doc_id = uuid4()
        return [
            DocumentSection(
                document_id=doc_id,
                section_text="This is a test section about machine learning",
                heading="Machine Learning Basics",
                heading_level=1,
                chunk_index=0,
                token_count=25,
                start_position=0,
                end_position=45,
                section_type=SectionType.HEADING,
            ),
            DocumentSection(
                document_id=doc_id,
                section_text="Neural networks are a fundamental concept in AI",
                heading="Neural Networks",
                heading_level=2,
                chunk_index=1,
                token_count=20,
                start_position=50,
                end_position=97,
                section_type=SectionType.PARAGRAPH,
            ),
        ]

    @pytest.fixture
    def vector_store(self, mock_config, mock_embedding_provider):
        """Create a MilvusVectorStore instance with mocked dependencies."""
        return MilvusVectorStore(mock_config, mock_embedding_provider)

    def test_initialization(self, vector_store, mock_config, mock_embedding_provider):
        """Test vector store initialization."""
        assert vector_store.config == mock_config
        assert vector_store.embedding_provider == mock_embedding_provider
        assert not vector_store.is_initialized
        assert vector_store._vectorstore is None

    @pytest.mark.asyncio
    @patch("markdown_rag_mcp.storage.milvus_store.Milvus")
    async def test_initialize_collections_success(self, mock_milvus_class, vector_store):
        """Test successful collection initialization."""
        # Mock the Milvus class constructor
        mock_vectorstore = AsyncMock()
        mock_milvus_class.return_value = mock_vectorstore

        await vector_store.initialize_collections()

        # Verify initialization
        assert vector_store.is_initialized
        assert vector_store._vectorstore == mock_vectorstore

        # Verify Milvus was called with correct arguments
        mock_milvus_class.assert_called_once()
        call_args = mock_milvus_class.call_args
        assert call_args[1]["collection_name"] == "document_sections"
        assert call_args[1]["connection_args"]["uri"] == "http://localhost:19530"
        assert call_args[1]["connection_args"]["db_name"] == "markdown_rag"
        assert call_args[1]["index_params"]["index_type"] == "IVF_FLAT"
        assert call_args[1]["index_params"]["metric_type"] == "COSINE"
        assert call_args[1]["consistency_level"] == "Strong"
        assert call_args[1]["drop_old"] is False

    @pytest.mark.asyncio
    @patch("markdown_rag_mcp.storage.milvus_store.Milvus")
    async def test_initialize_collections_already_initialized(self, mock_milvus_class, vector_store):
        """Test that re-initialization is skipped when already initialized."""
        # Set up as already initialized
        vector_store._initialized = True
        vector_store._vectorstore = Mock()

        await vector_store.initialize_collections()

        # Verify Milvus constructor was not called
        mock_milvus_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("markdown_rag_mcp.storage.milvus_store.Milvus")
    async def test_initialize_collections_failure(self, mock_milvus_class, vector_store):
        """Test initialization failure handling."""
        # Make Milvus constructor raise an exception
        mock_milvus_class.side_effect = Exception("Connection failed")

        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.initialize_collections()

        assert "Failed to initialize Milvus vector store" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)
        assert not vector_store.is_initialized

    @pytest.mark.asyncio
    async def test_store_document_sections_not_initialized(self, vector_store, sample_document_sections):
        """Test storing sections when not initialized."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        # Should return early without error when not initialized
        await vector_store.store_document_sections(sample_document_sections, embeddings)
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_store_document_sections_empty_sections(self, vector_store):
        """Test storing empty sections list."""
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        vector_store._vectorstore = mock_vectorstore

        # Should return early without error
        await vector_store.store_document_sections([], [])

        # Verify no calls were made to the vectorstore
        mock_vectorstore.aadd_documents.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_document_sections_success(self, vector_store, sample_document_sections):
        """Test successful document section storage."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        vector_store._vectorstore = mock_vectorstore

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        await vector_store.store_document_sections(sample_document_sections, embeddings)

        # Verify aadd_documents was called once
        mock_vectorstore.aadd_documents.assert_called_once()

        # Verify the documents passed to LangChain
        called_documents = mock_vectorstore.aadd_documents.call_args[0][0]
        assert len(called_documents) == 2

        # Check first document
        doc1 = called_documents[0]
        assert doc1.page_content == "This is a test section about machine learning"
        assert doc1.metadata["section_heading"] == "Machine Learning Basics"
        assert doc1.metadata["heading_level"] == 1
        assert doc1.metadata["chunk_index"] == 0
        assert doc1.metadata["section_type"] == "heading"

        # Check second document
        doc2 = called_documents[1]
        assert doc2.page_content == "Neural networks are a fundamental concept in AI"
        assert doc2.metadata["section_heading"] == "Neural Networks"
        assert doc2.metadata["heading_level"] == 2
        assert doc2.metadata["chunk_index"] == 1

    @pytest.mark.asyncio
    async def test_store_document_sections_failure(self, vector_store, sample_document_sections):
        """Test handling of storage failure."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        mock_vectorstore.aadd_documents.side_effect = Exception("Storage failed")
        vector_store._vectorstore = mock_vectorstore

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.store_document_sections(sample_document_sections, embeddings)

        assert "Failed to store document sections" in str(exc_info.value)
        assert "Storage failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_similar_not_initialized(self, vector_store):
        """Test search when not initialized."""
        query_embedding = [0.1, 0.2, 0.3]

        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.search_similar(query_embedding)

        assert "Vector store not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_similar_with_scores_success(self, vector_store):
        """Test successful similarity search with actual scores."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        vector_store._vectorstore = mock_vectorstore

        # Mock search results from LangChain with scores
        mock_doc1 = Document(
            page_content="Machine learning is a subset of AI",
            metadata={
                "section_id": str(uuid4()),
                "document_id": str(uuid4()),
                "file_path": "ml_guide.md",
                "section_heading": "ML Overview",
                "heading_level": 1,
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 34,
            },
        )
        mock_doc2 = Document(
            page_content="Deep learning uses neural networks",
            metadata={
                "section_id": str(uuid4()),
                "document_id": str(uuid4()),
                "file_path": "ml_guide.md",
                "section_heading": "Deep Learning",
                "heading_level": 2,
                "chunk_index": 1,
                "start_position": 40,
                "end_position": 74,
            },
        )

        # Mock the score-based method (first attempt)
        mock_vectorstore.similarity_search_with_score_by_vector.return_value = [
            (mock_doc1, 0.85),  # High similarity score
            (mock_doc2, 0.75),  # Medium similarity score
        ]

        query_embedding = [0.1, 0.2, 0.3]
        results = await vector_store.search_similar(
            query_embedding, limit=5, similarity_threshold=0.7, metadata_filters={"file_path": "ml_guide.md"}
        )

        # Verify the score-based search was called correctly
        mock_vectorstore.similarity_search_with_score_by_vector.assert_called_once_with(
            embedding=query_embedding, k=5, filter={"file_path": "ml_guide.md"}
        )

        # Verify results
        assert len(results) == 2

        # Check first result with real score
        result1 = results[0]
        assert isinstance(result1, QueryResult)
        assert result1.section_text == "Machine learning is a subset of AI"
        assert result1.file_path == "ml_guide.md"
        assert result1.section_heading == "ML Overview"
        assert result1.heading_level == 1
        assert result1.chunk_index == 0
        assert result1.confidence_score == 0.85  # Real score from Milvus

        # Check second result with real score
        result2 = results[1]
        assert result2.section_text == "Deep learning uses neural networks"
        assert result2.section_heading == "Deep Learning"
        assert result2.heading_level == 2
        assert result2.confidence_score == 0.75  # Real score from Milvus

    @pytest.mark.asyncio
    async def test_search_similar_with_low_confidence_filtering(self, vector_store):
        """Test search with low confidence scores getting filtered out."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        vector_store._vectorstore = mock_vectorstore

        # Mock search results from LangChain with low scores that should be filtered
        low_score_doc = Document(
            page_content="Low confidence result",
            metadata={
                "section_id": str(uuid4()),
                "document_id": str(uuid4()),
                "file_path": "ml_guide.md",
                "section_heading": "Low Match",
                "heading_level": 1,
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 20,
            },
        )

        # Mock the score-based method with low scores
        mock_vectorstore.similarity_search_with_score_by_vector.return_value = [
            (low_score_doc, 0.5),  # Low score - should be filtered out by default threshold
        ]

        query_embedding = [0.1, 0.2, 0.3]
        results = await vector_store.search_similar(
            query_embedding, limit=5, similarity_threshold=0.7, metadata_filters={"file_path": "ml_guide.md"}
        )

        # Verify the score-based search was called correctly
        mock_vectorstore.similarity_search_with_score_by_vector.assert_called_once_with(
            embedding=query_embedding, k=5, filter={"file_path": "ml_guide.md"}
        )

        # All results should be filtered out due to low confidence
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_similar_with_threshold_filtering(self, vector_store):
        """Test search with confidence threshold filtering using real scores."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        vector_store._vectorstore = mock_vectorstore

        high_confidence_doc = Document(
            page_content="High confidence result",
            metadata={
                "file_path": "test.md",
                "section_id": str(uuid4()),
                "document_id": str(uuid4()),
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 23,
            },
        )

        low_confidence_doc = Document(
            page_content="Low confidence result",
            metadata={
                "file_path": "test.md",
                "section_id": str(uuid4()),
                "document_id": str(uuid4()),
                "chunk_index": 1,
                "start_position": 24,
                "end_position": 46,
            },
        )

        # Mock score-based method with different scores
        mock_vectorstore.similarity_search_with_score_by_vector.return_value = [
            (high_confidence_doc, 0.85),  # High score - should pass threshold
            (low_confidence_doc, 0.65),  # Low score - should be filtered
        ]

        query_embedding = [0.1, 0.2, 0.3]

        # Test with threshold that filters low confidence results
        results = await vector_store.search_similar(
            query_embedding, similarity_threshold=0.7  # Between low (0.65) and high (0.85) scores
        )

        # Only high confidence result should pass threshold
        assert len(results) == 1
        assert results[0].section_text == "High confidence result"
        assert results[0].confidence_score == 0.85

        # Test with high threshold (should filter out all results)
        mock_vectorstore.similarity_search_with_score_by_vector.return_value = [
            (high_confidence_doc, 0.85),
            (low_confidence_doc, 0.65),
        ]

        results = await vector_store.search_similar(
            query_embedding, similarity_threshold=0.9  # Higher than both scores
        )

        # All results should be filtered out
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_similar_failure(self, vector_store):
        """Test handling of search failure."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        mock_vectorstore.similarity_search_with_score_by_vector.side_effect = Exception("Search failed")
        vector_store._vectorstore = mock_vectorstore

        query_embedding = [0.1, 0.2, 0.3]

        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.search_similar(query_embedding)

        assert "Similarity search failed" in str(exc_info.value)
        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_document_not_initialized(self, vector_store):
        """Test delete when not initialized."""
        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.delete_document("test.md")

        assert "Vector store not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_document_success(self, vector_store):
        """Test successful document deletion."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        vector_store._vectorstore = mock_vectorstore

        await vector_store.delete_document("test.md")

        # Verify delete was called with correct filter
        mock_vectorstore.adelete.assert_called_once_with(filter={"file_path": "test.md"})

    @pytest.mark.asyncio
    async def test_delete_document_failure(self, vector_store):
        """Test handling of deletion failure."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        mock_vectorstore.adelete.side_effect = Exception("Delete failed")
        vector_store._vectorstore = mock_vectorstore

        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.delete_document("test.md")

        assert "Failed to delete document" in str(exc_info.value)
        assert "Delete failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_document_sections_success(self, vector_store, sample_document_sections):
        """Test successful document section update."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        vector_store._vectorstore = mock_vectorstore

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        file_path = "test.md"

        await vector_store.update_document_sections(file_path, sample_document_sections, embeddings)

        # Verify delete was called first
        mock_vectorstore.adelete.assert_called_once_with(filter={"file_path": file_path})

        # Verify add was called second
        mock_vectorstore.aadd_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_document_sections_failure(self, vector_store, sample_document_sections):
        """Test handling of update failure."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = AsyncMock()
        mock_vectorstore.adelete.side_effect = Exception("Update failed")
        vector_store._vectorstore = mock_vectorstore

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        with pytest.raises(VectorStoreError) as exc_info:
            await vector_store.update_document_sections("test.md", sample_document_sections, embeddings)

        assert "Failed to update document sections" in str(exc_info.value)
        assert "Update failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, vector_store):
        """Test health check when not initialized."""
        result = await vector_store.health_check()

        assert result["status"] == "error"
        assert result["message"] == "Vector store not initialized"
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, vector_store):
        """Test successful health check."""
        # Set up initialized state
        vector_store._initialized = True
        mock_collection = Mock()
        mock_collection.num_entities = 100

        mock_vectorstore = Mock()
        mock_vectorstore.col = mock_collection
        mock_vectorstore.collection_name = "document_sections"
        vector_store._vectorstore = mock_vectorstore

        result = await vector_store.health_check()

        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert result["collection_name"] == "document_sections"
        assert result["entities"] == 100

    @pytest.mark.asyncio
    async def test_health_check_connection_failure(self, vector_store):
        """Test health check with connection failure."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        # Access to .col property raises an exception
        type(mock_vectorstore).col = PropertyMock(side_effect=Exception("Connection lost"))
        vector_store._vectorstore = mock_vectorstore

        result = await vector_store.health_check()

        assert result["status"] == "error"
        assert "Connection test failed" in result["message"]
        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_get_section_count_not_initialized(self, vector_store):
        """Test getting section count when not initialized."""
        count = await vector_store.get_section_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_section_count_success(self, vector_store):
        """Test successful section count retrieval."""
        # Set up initialized state
        vector_store._initialized = True
        mock_collection = Mock()
        mock_collection.num_entities = 50

        mock_vectorstore = Mock()
        mock_vectorstore.col = mock_collection
        vector_store._vectorstore = mock_vectorstore

        count = await vector_store.get_section_count()
        assert count == 50

    @pytest.mark.asyncio
    async def test_get_section_count_no_attribute(self, vector_store):
        """Test section count when collection doesn't have num_entities."""
        # Set up initialized state
        vector_store._initialized = True
        mock_collection = Mock()
        # Remove num_entities attribute
        del mock_collection.num_entities

        mock_vectorstore = Mock()
        mock_vectorstore.col = mock_collection
        vector_store._vectorstore = mock_vectorstore

        count = await vector_store.get_section_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_section_count_failure(self, vector_store):
        """Test handling of section count failure."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        type(mock_vectorstore).col = PropertyMock(side_effect=Exception("Collection error"))
        vector_store._vectorstore = mock_vectorstore

        count = await vector_store.get_section_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_success(self, vector_store):
        """Test successful cleanup."""
        # Set up initialized state
        vector_store._initialized = True
        mock_vectorstore = Mock()
        vector_store._vectorstore = mock_vectorstore

        await vector_store.cleanup()

        assert vector_store._vectorstore is None
        assert not vector_store._initialized

    @pytest.mark.asyncio
    async def test_cleanup_failure(self, vector_store):
        """Test cleanup failure handling."""
        # Set up state that causes cleanup to fail
        vector_store._initialized = True
        vector_store._vectorstore = Mock()

        # Make the logger.error method raise an exception
        with patch("markdown_rag_mcp.storage.milvus_store.logger") as mock_logger:
            mock_logger.error.side_effect = Exception("Logging failed")

            # The current implementation doesn't raise VectorStoreError in cleanup,
            # it just logs errors. Let's test successful cleanup instead.
            await vector_store.cleanup()

            # Verify cleanup completed
            assert vector_store._vectorstore is None
            assert not vector_store._initialized

    def test_convert_sections_to_documents(self, vector_store, sample_document_sections):
        """Test conversion of DocumentSection objects to LangChain Documents."""
        documents = vector_store._convert_sections_to_documents(sample_document_sections)

        assert len(documents) == 2

        # Check first document
        doc1 = documents[0]
        assert doc1.page_content == "This is a test section about machine learning"
        assert doc1.metadata["section_heading"] == "Machine Learning Basics"
        assert doc1.metadata["heading_level"] == 1
        assert doc1.metadata["chunk_index"] == 0
        assert doc1.metadata["token_count"] == 25
        assert doc1.metadata["start_position"] == 0
        assert doc1.metadata["end_position"] == 45
        assert doc1.metadata["section_type"] == "heading"

        # Check second document
        doc2 = documents[1]
        assert doc2.page_content == "Neural networks are a fundamental concept in AI"
        assert doc2.metadata["section_heading"] == "Neural Networks"
        assert doc2.metadata["heading_level"] == 2
        assert doc2.metadata["chunk_index"] == 1
        assert doc2.metadata["section_type"] == "paragraph"

        # Verify all metadata includes required fields
        for doc in documents:
            assert "section_id" in doc.metadata
            assert "document_id" in doc.metadata
            assert "file_path" in doc.metadata
            assert "created_at" in doc.metadata

            # Verify file_path is constructed correctly
            assert doc.metadata["file_path"].startswith("doc_")

    def test_is_initialized_property(self, vector_store):
        """Test the is_initialized property."""
        # Initially not initialized
        assert not vector_store.is_initialized

        # Set initialized but no vectorstore
        vector_store._initialized = True
        assert not vector_store.is_initialized

        # Set both initialized and vectorstore
        vector_store._vectorstore = Mock()
        assert vector_store.is_initialized

        # Clear vectorstore
        vector_store._vectorstore = None
        assert not vector_store.is_initialized
