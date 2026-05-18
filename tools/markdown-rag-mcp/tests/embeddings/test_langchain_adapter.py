"""
Unit tests for LangChainEmbeddingAdapter.

Tests the LangChain compatibility adapter including sync/async interfaces,
nested event loop handling, and integration with HuggingFaceEmbedder.
"""

from unittest.mock import MagicMock

import pytest
from markdown_rag_mcp.config import EmbeddingDevice, RAGConfig
from markdown_rag_mcp.embeddings import HuggingFaceEmbedder, LangChainEmbeddingAdapter


class TestLangChainEmbeddingAdapter:
    """Test cases for LangChainEmbeddingAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test configuration - use minimal args to avoid validation issues
        self.config = RAGConfig()
        self.config.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        self.config.embedding_device = EmbeddingDevice.CPU
        self.config.embedding_batch_size = 32

        # Create adapter instance
        self.adapter = LangChainEmbeddingAdapter(self.config)

        # Mock the underlying HuggingFace embedder
        self.mock_embedder = MagicMock()
        self.mock_embedder.embedding_dimension = 384
        self.mock_embedder.model_name = "sentence-transformers/all-MiniLM-L6-v2"

        # Configure async methods as regular mock functions that can be configured per test
        self.mock_embedder.generate_embedding = MagicMock()
        self.mock_embedder.generate_batch_embeddings = MagicMock()

        # Replace the embedder in the adapter
        self.adapter._embedder = self.mock_embedder

    def test_initialization(self):
        """Test adapter initialization."""
        adapter = LangChainEmbeddingAdapter(self.config)

        assert adapter.config == self.config
        assert isinstance(adapter._embedder, HuggingFaceEmbedder)
        assert adapter._initialized is False

    async def test_initialize(self):
        """Test adapter initialization method."""
        self.adapter._initialized = False

        # Mock the model property access
        mock_model = MagicMock()
        self.mock_embedder.model = mock_model

        await self.adapter.initialize()

        assert self.adapter._initialized is True
        # Verify that model was accessed (lazy loading)
        assert self.mock_embedder.model is mock_model

    async def test_initialize_already_initialized(self):
        """Test that initialize is idempotent."""
        self.adapter._initialized = True

        await self.adapter.initialize()

        # Should still be initialized
        assert self.adapter._initialized is True

    def test_embed_documents_not_initialized(self):
        """Test embed_documents raises error when not initialized."""
        self.adapter._initialized = False

        with pytest.raises(RuntimeError) as exc_info:
            self.adapter.embed_documents(["test text"])

        assert "not initialized" in str(exc_info.value)

    def test_embed_query_not_initialized(self):
        """Test embed_query raises error when not initialized."""
        self.adapter._initialized = False

        with pytest.raises(RuntimeError) as exc_info:
            self.adapter.embed_query("test text")

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_aembed_documents_not_initialized(self):
        """Test aembed_documents raises error when not initialized."""
        self.adapter._initialized = False

        with pytest.raises(RuntimeError) as exc_info:
            await self.adapter.aembed_documents(["test text"])

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_aembed_query_not_initialized(self):
        """Test aembed_query raises error when not initialized."""
        self.adapter._initialized = False

        with pytest.raises(RuntimeError) as exc_info:
            await self.adapter.aembed_query("test text")

        assert "not initialized" in str(exc_info.value)

    def test_embed_documents_success(self):
        """Test successful synchronous document embedding."""
        # Setup
        self.adapter._initialized = True
        expected_embeddings = [[0.1, 0.2], [0.3, 0.4]]

        # Mock the async method to return a proper coroutine
        async def mock_batch_embed(texts):
            return expected_embeddings

        self.mock_embedder.generate_batch_embeddings = mock_batch_embed

        # Test
        texts = ["text1", "text2"]
        result = self.adapter.embed_documents(texts)

        # Verify
        assert result == expected_embeddings

    def test_embed_query_success(self):
        """Test successful synchronous query embedding."""
        # Setup
        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2, 0.3, 0.4]

        # Mock the async method to return a proper coroutine
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        # Test
        result = self.adapter.embed_query("test query")

        # Verify
        assert result == expected_embedding

    def test_embed_query_no_event_loop(self):
        """Test embedding when no event loop exists."""
        # Setup
        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2]

        # Mock the async method to return a proper coroutine
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        # Test
        result = self.adapter.embed_query("test")

        # Verify
        assert result == expected_embedding

    def test_embed_query_running_loop_with_nest_asyncio(self):
        """Test embedding with running event loop and nest_asyncio available."""
        # Setup
        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2]

        # Mock the async method to return a proper coroutine
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        # Test
        result = self.adapter.embed_query("test")

        # Verify
        assert result == expected_embedding

    def test_embed_query_running_loop_without_nest_asyncio(self):
        """Test embedding with running event loop when nest_asyncio is not available."""
        # Setup
        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2]

        # Mock the async method to return a proper coroutine
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        # Test - our thread-based implementation doesn't need nest_asyncio
        result = self.adapter.embed_query("test")

        # Should work without issues
        assert result == expected_embedding

    @pytest.mark.asyncio
    async def test_aembed_documents_success(self):
        """Test successful async document embedding."""
        # Setup
        self.adapter._initialized = True
        expected_embeddings = [[0.1, 0.2], [0.3, 0.4]]

        # Configure async mock to return the expected value when awaited
        async def mock_batch_embed(texts):
            return expected_embeddings

        self.mock_embedder.generate_batch_embeddings.side_effect = mock_batch_embed

        # Test
        texts = ["text1", "text2"]
        result = await self.adapter.aembed_documents(texts)

        # Verify
        assert result == expected_embeddings
        self.mock_embedder.generate_batch_embeddings.assert_called_once_with(texts)

    @pytest.mark.asyncio
    async def test_aembed_query_success(self):
        """Test successful async query embedding."""
        # Setup
        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2, 0.3, 0.4]

        # Configure async mock to return the expected value when awaited
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding.side_effect = mock_embed

        # Test
        result = await self.adapter.aembed_query("test query")

        # Verify
        assert result == expected_embedding
        self.mock_embedder.generate_embedding.assert_called_once_with("test query")

    def test_embedding_dimension_property(self):
        """Test embedding dimension property."""
        self.mock_embedder.embedding_dimension = 768

        dimension = self.adapter.embedding_dimension

        assert dimension == 768

    def test_model_name_property(self):
        """Test model name property."""
        result = self.adapter.model_name

        assert result == "sentence-transformers/all-MiniLM-L6-v2"
        assert result == self.config.embedding_model

    def test_embed_documents_preserves_order(self):
        """Test that document embedding preserves order."""
        # Setup
        self.adapter._initialized = True

        # Mock embeddings in specific order
        expected_embeddings = [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]

        # Mock the async method to return a proper coroutine
        async def mock_batch_embed(texts):
            return expected_embeddings

        self.mock_embedder.generate_batch_embeddings = mock_batch_embed

        # Test
        texts = ["first", "second", "third"]
        result = self.adapter.embed_documents(texts)

        # Verify order is preserved
        assert result == expected_embeddings
        assert len(result) == len(texts)

    @pytest.mark.asyncio
    async def test_async_interface_consistency(self):
        """Test that sync and async interfaces produce consistent results."""
        # Setup
        self.adapter._initialized = True
        test_text = "consistency test"
        expected_embedding = [0.1, 0.2, 0.3, 0.4]

        # Configure async mock for embedder
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        # Test both interfaces
        async_result = await self.adapter.aembed_query(test_text)
        sync_result = self.adapter.embed_query(test_text)

        # Results should be identical
        assert async_result == sync_result == expected_embedding

    def test_langchain_embeddings_interface_compliance(self):
        """Test that adapter implements LangChain Embeddings interface correctly."""
        from langchain_core.embeddings import Embeddings

        # Verify adapter is instance of LangChain Embeddings
        assert isinstance(self.adapter, Embeddings)

        # Verify required methods exist
        assert hasattr(self.adapter, 'embed_documents')
        assert hasattr(self.adapter, 'embed_query')
        assert callable(self.adapter.embed_documents)
        assert callable(self.adapter.embed_query)

        # Verify async methods exist (LangChain 0.2+ feature)
        assert hasattr(self.adapter, 'aembed_documents')
        assert hasattr(self.adapter, 'aembed_query')
        assert callable(self.adapter.aembed_documents)
        assert callable(self.adapter.aembed_query)

    def test_empty_documents_list(self):
        """Test embedding empty documents list."""
        # Setup
        self.adapter._initialized = True

        # Mock the async method to return empty list
        async def mock_batch_embed(texts):
            return []

        self.mock_embedder.generate_batch_embeddings = mock_batch_embed

        # Test
        result = self.adapter.embed_documents([])

        # Verify
        assert result == []

    def test_single_document_embedding(self):
        """Test embedding single document."""
        # Setup
        self.adapter._initialized = True
        expected_embeddings = [[0.1, 0.2, 0.3]]

        # Mock the async method to return single document embedding
        async def mock_batch_embed(texts):
            return expected_embeddings

        self.mock_embedder.generate_batch_embeddings = mock_batch_embed

        # Test
        result = self.adapter.embed_documents(["single document"])

        # Verify
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]

    def test_large_batch_embedding(self):
        """Test embedding large batch of documents."""
        # Setup
        self.adapter._initialized = True

        # Create large batch
        batch_size = 100
        texts = [f"document {i}" for i in range(batch_size)]
        expected_embeddings = [[0.1 * i, 0.2 * i] for i in range(batch_size)]

        # Mock the async method to return large batch embeddings
        async def mock_batch_embed(texts):
            return expected_embeddings

        self.mock_embedder.generate_batch_embeddings = mock_batch_embed

        # Test
        result = self.adapter.embed_documents(texts)

        # Verify
        assert len(result) == batch_size
        assert result == expected_embeddings

    def test_unicode_text_handling(self):
        """Test handling of Unicode text in sync interface."""
        # Setup
        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2, 0.3]

        # Mock the async method to return a proper coroutine
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        # Test with Unicode text
        unicode_text = "测试文本 🚀 français español"
        result = self.adapter.embed_query(unicode_text)

        # Should handle Unicode without errors
        assert result == expected_embedding

    @pytest.mark.asyncio
    async def test_unicode_text_handling_async(self):
        """Test handling of Unicode text in async interface."""
        # Setup
        self.adapter._initialized = True
        unicode_text = "测试文本 🚀 français español"
        expected_embedding = [0.1, 0.2, 0.3]

        # Configure async mock for embedder
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding.side_effect = mock_embed

        # Test
        result = await self.adapter.aembed_query(unicode_text)

        # Verify
        assert result == expected_embedding
        self.mock_embedder.generate_embedding.assert_called_once_with(unicode_text)

    def test_error_propagation_sync(self):
        """Test that errors are properly propagated in sync interface."""
        # Setup
        self.adapter._initialized = True
        test_error = RuntimeError("Embedding failed")

        # Mock the async method to raise an error
        async def mock_embed_error(text):
            raise test_error

        self.mock_embedder.generate_embedding = mock_embed_error

        # Test
        with pytest.raises(RuntimeError) as exc_info:
            self.adapter.embed_query("test")

        # The error should be wrapped by our thread executor
        assert "Embedding operation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_propagation_async(self):
        """Test that errors are properly propagated in async interface."""
        # Setup
        self.adapter._initialized = True
        test_error = RuntimeError("Async embedding failed")

        # Configure async mock to raise error
        async def mock_embed_error(text):
            raise test_error

        self.mock_embedder.generate_embedding.side_effect = mock_embed_error

        # Test
        with pytest.raises(RuntimeError) as exc_info:
            await self.adapter.aembed_query("test")

        assert str(exc_info.value) == "Async embedding failed"

    def test_event_loop_creation_thread_safety(self):
        """Test thread safety when creating new event loops."""
        import threading

        self.adapter._initialized = True
        expected_embedding = [0.1, 0.2]
        results = []
        errors = []

        # Mock the async method to return a proper coroutine
        async def mock_embed(text):
            return expected_embedding

        self.mock_embedder.generate_embedding = mock_embed

        def embed_in_thread():
            try:
                result = self.adapter.embed_query("test")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=embed_in_thread)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors and all results are correct
        assert len(errors) == 0
        assert len(results) == 3
        assert all(result == expected_embedding for result in results)

    def test_concurrent_sync_calls(self):
        """Test multiple synchronous calls work correctly."""
        # Setup
        self.adapter._initialized = True

        # Different results for different calls - use a counter to return different embeddings
        call_count = 0
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        # Mock the async method to return different results for each call
        async def mock_embed(text):
            nonlocal call_count
            result = embeddings[call_count]
            call_count += 1
            return result

        self.mock_embedder.generate_embedding = mock_embed

        # Test multiple calls
        results = []
        for i in range(3):
            result = self.adapter.embed_query(f"test {i}")
            results.append(result)

        # Verify all calls succeeded with expected results
        assert results == embeddings
