"""
HuggingFace embedding provider implementation.

Generates embeddings using local HuggingFace sentence-transformers models.
"""

import asyncio
import logging

from markdown_rag_mcp.core import IEmbeddingProvider
from markdown_rag_mcp.models import EmbeddingModelError

logger = logging.getLogger(__name__)


class HuggingFaceEmbedder(IEmbeddingProvider):
    """
    HuggingFace sentence-transformers embedding provider.

    Uses local models to generate embeddings, supporting CPU, CUDA, and MPS (Apple Silicon) devices.
    """

    def __init__(self, config):
        """Initialize the HuggingFace embedder with configuration."""
        self.config = config
        self._model = None
        self._device = config.resolve_embedding_device()
        self._model_name = config.embedding_model

        logger.info("Initializing HuggingFace embedder: %s on %s", self._model_name, self._device)

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """Load the sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401

            logger.info("Loading embedding model: %s", self._model_name)

            # Load model with cache directory if specified
            cache_folder = str(self.config.embedding_cache_dir) if self.config.embedding_cache_dir else None

            self._model = SentenceTransformer(self._model_name, device=self._device, cache_folder=cache_folder)

            logger.info("Model loaded successfully on device: %s", self._device)

        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)

            raise EmbeddingModelError(
                f"Failed to load model {self._model_name}: {e}",
                model_name=self._model_name,
                operation="load_model",
                underlying_error=e,
            ) from e

    async def initialize(self) -> None:
        """
        Initialize the embedding model.

        This method ensures the model is loaded and ready for use.
        Since HuggingFaceEmbedder uses lazy loading, this method
        simply triggers the model loading process.
        """
        # Trigger model loading by accessing the model property
        _ = self.model
        logger.info("HuggingFace embedder initialized successfully")

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingModelError: If embedding generation fails
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.embedding_dimension

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, self._generate_embedding_sync, text.strip())

            return embedding.tolist()

        except Exception as e:
            logger.error("Embedding generation failed: %s", e)

            raise EmbeddingModelError(
                f"Failed to generate embedding: {e}",
                model_name=self._model_name,
                operation="generate_embedding",
                underlying_error=e,
            ) from e

    async def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingModelError: If batch embedding generation fails
        """
        if not texts:
            return []

        try:
            # Filter out empty texts but remember their positions
            text_mapping = []
            filtered_texts = []

            for i, text in enumerate(texts):
                if text and text.strip():
                    text_mapping.append((i, len(filtered_texts)))
                    filtered_texts.append(text.strip())
                else:
                    text_mapping.append((i, None))

            # Generate embeddings for non-empty texts
            if filtered_texts:
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(None, self._generate_batch_embeddings_sync, filtered_texts)
            else:
                embeddings = []

            # Reconstruct full results with zero vectors for empty texts
            zero_vector = [0.0] * self.embedding_dimension
            results = []

            for _original_idx, filtered_idx in text_mapping:
                if filtered_idx is not None:
                    results.append(embeddings[filtered_idx].tolist())
                else:
                    results.append(zero_vector)

            return results

        except Exception as e:
            logger.error("Batch embedding generation failed: %s", e)

            raise EmbeddingModelError(
                f"Failed to generate batch embeddings: {e}",
                model_name=self._model_name,
                operation="generate_batch_embeddings",
                underlying_error=e,
            ) from e

    def _generate_embedding_sync(self, text: str):
        """Synchronous embedding generation for single text."""
        return self.model.encode(text, convert_to_tensor=False, normalize_embeddings=True)

    def _generate_batch_embeddings_sync(self, texts: list[str]):
        """Synchronous batch embedding generation."""
        return self.model.encode(
            texts,
            batch_size=self.config.embedding_batch_size,
            convert_to_tensor=False,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    @property
    def embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings produced by this provider."""
        # Standard dimension for sentence-transformers/all-MiniLM-L6-v2
        return 384

    @property
    def model_name(self) -> str:
        """Get the name/identifier of the embedding model."""
        return self._model_name
