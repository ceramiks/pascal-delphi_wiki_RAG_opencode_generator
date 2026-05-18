"""
Vector store implementation.
"""

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_milvus import Milvus
from pymilvus import MilvusClient

from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.core import IEmbeddingProvider, IVectorStore
from markdown_rag_mcp.models import DocumentSection, QueryResult, VectorStoreError

logger = logging.getLogger(__name__)


class MilvusVectorStore(IVectorStore):
    """
    Milvus vector store implementation.

    Leverages Milvus for all vector operations, providing a clean
    interface while eliminating custom Milvus collection management.
    """

    def __init__(self, config: RAGConfig, embedding_provider: IEmbeddingProvider):
        """Initialize vector store with configuration."""
        self.config = config
        self.embedding_provider = embedding_provider
        self._vectorstore: Milvus | None = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the vector store is initialized."""
        return self._initialized and self._vectorstore is not None

    async def initialize_collections(self) -> None:
        """Initialize Milvus vector store."""
        if self._initialized:
            return

        try:
            # First, create database if it doesn't exist
            await self._ensure_database_exists()

            # Build connection arguments for Milvus
            connection_args = {
                "uri": f"http://{self.config.milvus_host}:{self.config.milvus_port}",
                "db_name": "markdown_rag",
            }

            # Initialize Milvus vector store
            self._vectorstore = Milvus(
                embedding_function=self.embedding_provider,
                collection_name="document_sections",
                connection_args=connection_args,
                index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 1024}},
                consistency_level="Strong",
                drop_old=False,  # Don't drop existing collections
            )

            self._initialized = True
            logger.info("Milvus vector store initialized successfully")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize Milvus vector store: {e}",
                operation="initialize_collections",
                underlying_error=e,
            ) from e

    async def _ensure_database_exists(self) -> None:
        """Ensure the markdown_rag database exists, create if it doesn't."""
        try:
            # Create a client connection to check/create database
            client = MilvusClient(uri=f"http://{self.config.milvus_host}:{self.config.milvus_port}")

            # List existing databases
            databases = client.list_databases()

            if self.config.milvus_db_name not in databases:
                logger.info("Creating markdown_rag database...")
                client.create_database(db_name=self.config.milvus_db_name)
                logger.info("Database '%s' created successfully", self.config.milvus_db_name)
            else:
                logger.info("Database '%s' already exists", self.config.milvus_db_name)

            # Close the client connection
            client.close()

        except Exception as e:
            logger.error("Failed to ensure database exists: %s", e)
            raise VectorStoreError(
                f"Failed to create database: {e}",
                operation="ensure_database_exists",
                underlying_error=e,
            ) from e

    async def store_document_sections(self, sections: list[DocumentSection], embeddings: list[list[float]]) -> None:
        """Store document sections using Milvus."""
        if not sections or not self.is_initialized:
            return

        try:
            # Convert sections to Milvus Document format
            documents = self._convert_sections_to_documents(sections)

            # Add documents to vector store
            # Milvus will automatically generate embeddings using our embedding provider
            await self._vectorstore.aadd_documents(documents)

            logger.info("Stored %s document sections using Milvus", len(sections))

        except Exception as e:
            raise VectorStoreError(
                f"Failed to store document sections: {e}",
                operation="store_document_sections",
                record_count=len(sections),
                underlying_error=e,
            ) from e

    async def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[QueryResult]:
        """Search for similar document sections using Milvus."""
        if not self.is_initialized:
            raise VectorStoreError("Vector store not initialized", operation="search_similar")

        try:
            # First attempt: get results with actual similarity scores
            scored_results = self._vectorstore.similarity_search_with_score_by_vector(
                embedding=query_embedding, k=limit, **({'filter': metadata_filters} if metadata_filters else {})
            )

            query_results = []
            for doc, score in scored_results:
                metadata = doc.metadata

                # Convert Milvus distance to confidence score
                # For COSINE metric: higher score = more similar (0 to 1)
                # For L2 metric: lower distance = more similar, need conversion
                if self.config.milvus_metric_type == "COSINE":
                    confidence_score = float(score)  # COSINE already 0-1 similarity
                else:
                    # For L2/IP metrics, convert distance to similarity
                    confidence_score = max(0.0, min(1.0, 1.0 / (1.0 + float(score))))

                # Apply similarity threshold with real scores
                if confidence_score >= similarity_threshold:
                    query_result = QueryResult(
                        section_text=doc.page_content,
                        file_path=metadata.get("file_path", ""),
                        confidence_score=confidence_score,
                        section_heading=metadata.get("section_heading"),
                        heading_level=metadata.get("heading_level"),
                        chunk_index=metadata.get("chunk_index", 0),
                        section_id=metadata.get("section_id", ""),
                        document_id=metadata.get("document_id", ""),
                        start_position=metadata.get("start_position", 0),
                        end_position=metadata.get("end_position", 0),
                        metadata=metadata,
                    )
                    query_results.append(query_result)

            return query_results
        except Exception as e:
            raise VectorStoreError(
                f"Similarity search failed: {e}",
                operation="search_similar",
                underlying_error=e,
            ) from e

    async def delete_document(self, file_path: str) -> None:
        """Delete all sections belonging to a specific document."""
        if not self.is_initialized:
            raise VectorStoreError("Vector store not initialized", operation="delete_document")

        try:
            # LangChain Milvus supports deletion by metadata filter
            await self._vectorstore.adelete(filter={"file_path": file_path})
            logger.info("Deleted document sections for: %s", file_path)

        except Exception as e:
            raise VectorStoreError(
                f"Failed to delete document: {e}",
                operation="delete_document",
                underlying_error=e,
            ) from e

    async def update_document_sections(
        self,
        file_path: str,
        sections: list[DocumentSection],
        embeddings: list[list[float]],
    ) -> None:
        """Update sections for a document (delete old, insert new)."""
        try:
            # Delete existing sections
            await self.delete_document(file_path)

            # Insert new sections
            await self.store_document_sections(sections, embeddings)

            logger.info("Updated %s sections for document: %s", len(sections), file_path)

        except Exception as e:
            raise VectorStoreError(
                f"Failed to update document sections: {e}",
                operation="update_document_sections",
                underlying_error=e,
            ) from e

    async def health_check(self) -> dict[str, Any]:
        """Check the health status of the vector store."""
        try:
            if not self.is_initialized:
                return {
                    "status": "error",
                    "message": "Vector store not initialized",
                    "connected": False,
                }

            # LangChain Milvus doesn't expose detailed health info,
            # but we can try a basic operation to verify it's working
            try:
                # Try to get collection info (this will fail if connection is broken)
                collection_info = self._vectorstore.col
                return {
                    "status": "healthy",
                    "connected": True,
                    "collection_name": self._vectorstore.collection_name,
                    "entities": collection_info.num_entities if hasattr(collection_info, 'num_entities') else -1,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Connection test failed: {e}",
                    "connected": False,
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {e}",
                "connected": False,
            }

    async def get_section_count(self) -> int:
        """Get the total number of indexed sections."""
        if not self.is_initialized:
            return 0

        try:
            # Get total number of documents in the collection
            if hasattr(self._vectorstore.col, 'num_entities'):
                return self._vectorstore.col.num_entities
            return 0

        except Exception as e:
            logger.error("Failed to get section count: %s", e)
            return 0

    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            if self._vectorstore:
                # Milvus handles connection cleanup automatically
                self._vectorstore = None

            self._initialized = False
            logger.info("Milvus vector store cleaned up successfully")

        except Exception as e:
            logger.error("Error during cleanup: %s", e)
            raise VectorStoreError(
                f"Failed to cleanup vector store: {e}",
                operation="cleanup",
                underlying_error=e,
            ) from e

    def _convert_sections_to_documents(self, sections: list[DocumentSection]) -> list[Document]:
        """Convert DocumentSection objects to Milvus Document format."""
        documents = []

        for section in sections:
            # Create Milvus Document with section text and metadata
            doc = Document(
                page_content=section.section_text,
                metadata={
                    "section_id": str(section.id),
                    "document_id": str(section.document_id),
                    "file_path": f"doc_{section.document_id}",  # Mock file path from document_id
                    "section_heading": section.heading,
                    "heading_level": section.heading_level,
                    "chunk_index": section.chunk_index,
                    "token_count": section.token_count,
                    "start_position": section.start_position,
                    "end_position": section.end_position,
                    "section_type": (
                        section.section_type if isinstance(section.section_type, str) else section.section_type.value
                    ),
                    "created_at": section.created_at.isoformat(),
                },
            )
            documents.append(doc)

        return documents
