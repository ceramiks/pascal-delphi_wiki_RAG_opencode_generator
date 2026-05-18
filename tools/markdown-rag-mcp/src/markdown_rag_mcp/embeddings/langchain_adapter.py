"""
LangChain embedding adapter.

Adapts our HuggingFace embedder to LangChain's Embeddings interface
for seamless integration with langchain-milvus.
"""

import asyncio
import concurrent.futures
import logging
import threading

from langchain_core.embeddings import Embeddings

from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.embeddings.embedder import HuggingFaceEmbedder

logger = logging.getLogger(__name__)


class LangChainEmbeddingAdapter(Embeddings):
    """
    Adapter to make our HuggingFaceEmbedder compatible with LangChain.

    Wraps our async embedding provider to provide LangChain's expected
    synchronous interface.
    """

    def __init__(self, config: RAGConfig):
        """Initialize the adapter with our HuggingFace embedder."""
        self.config = config
        self._embedder = HuggingFaceEmbedder(config)
        self._initialized = False
        self._lock = threading.Lock()
        self._executor = None

    async def initialize(self) -> None:
        """Initialize the underlying embedder."""
        if not self._initialized:
            # HuggingFaceEmbedder uses lazy loading, no explicit initialization needed
            # Just ensure the model loads by accessing it
            _ = self._embedder.model  # This will trigger model loading
            self._initialized = True

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of documents (synchronous interface for LangChain).

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        # Use thread lock to prevent concurrent access issues
        with self._lock:
            return self._run_async_in_thread(self._embedder.generate_batch_embeddings(texts))

    def _run_async_in_thread(self, coro):
        """Run an async coroutine in a separate thread with its own event loop."""

        def run_in_new_thread():
            # Create a completely isolated event loop
            loop = asyncio.new_event_loop()
            try:
                # Set the event loop for this thread only
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(coro)
            except Exception as e:
                logger.error("Error running async operation: %s", e)
                raise RuntimeError(f"Error running async operation: {e}") from e
            finally:
                # Aggressive cleanup to prevent resource leaks
                try:
                    # Cancel ALL tasks, not just pending ones
                    all_tasks = asyncio.all_tasks(loop)
                    if all_tasks:
                        for task in all_tasks:
                            if not task.cancelled() and not task.done():
                                task.cancel()

                        # Wait for cancellations to complete with timeout
                        try:
                            loop.run_until_complete(
                                asyncio.wait_for(
                                    asyncio.gather(*all_tasks, return_exceptions=True),
                                    timeout=1.0,  # Short timeout for cleanup
                                )
                            )
                        except TimeoutError:
                            logger.warning("Task cleanup timed out, forcing shutdown")

                    # Force stop the loop
                    loop.stop()

                    # Wait a bit for loop to stop
                    import time

                    time.sleep(0.01)

                except Exception as e:
                    logger.debug("Loop cleanup error (expected): %s", e)
                finally:
                    # Force close
                    if not loop.is_closed():
                        loop.close()

                    # Clear thread-local event loop
                    try:
                        asyncio.set_event_loop(None)
                    except Exception:
                        pass

        # Get or create thread pool executor
        if self._executor is None or self._executor._shutdown:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="embedding")

        future = self._executor.submit(run_in_new_thread)
        try:
            # Reduced timeout to fail faster if there's an issue
            result = future.result(timeout=60)  # 1 minute timeout instead of 5
            return result
        except concurrent.futures.TimeoutError as e:
            logger.error("Embedding operation timed out after 60s")
            # Cancel the future to clean up
            future.cancel()
            raise RuntimeError("Embedding operation timed out after 60s") from e
        except Exception as e:
            logger.error("Embedding operation failed: %s", e)
            raise RuntimeError(f"Embedding operation failed: {e}") from e

    def cleanup(self):
        """Clean up resources including thread pool."""
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=True, timeout=1.0)
            except Exception as e:
                logger.debug("Executor cleanup error: %s", e)
            finally:
                self._executor = None

    def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query text (synchronous interface for LangChain).

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        # Use thread lock to prevent concurrent access issues
        with self._lock:
            return self._run_async_in_thread(self._embedder.generate_embedding(text))

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Async version of embed_documents (LangChain's async interface).

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        return await self._embedder.generate_batch_embeddings(texts)

    async def aembed_query(self, text: str) -> list[float]:
        """
        Async version of embed_query (LangChain's async interface).

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        return await self._embedder.generate_embedding(text)

    async def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate batch embeddings (direct interface for RAG system).

        This method provides direct access to the underlying embedder's
        batch embedding generation for compatibility with the RAG system.

        Args:
            texts: List of document texts to embed

        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        return await self._embedder.generate_batch_embeddings(texts)

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate single embedding (direct interface for RAG system).

        This method provides direct access to the underlying embedder's
        single embedding generation for compatibility with the RAG system.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call initialize() first.")

        return await self._embedder.generate_embedding(text)

    @property
    def embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings."""
        return self._embedder.embedding_dimension

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.embedding_model
