"""
Document indexer orchestrating parsing, chunking, embedding, and storage.

Coordinates the complete document processing pipeline from raw markdown files
to indexed vector embeddings with frontmatter metadata enhancement.
"""

import logging
import time
from pathlib import Path
from typing import Any

from markdown_rag_mcp.core import (
    IDocumentChunker,
    IDocumentIndexer,
    IDocumentParser,
    IEmbeddingProvider,
    IMetadataEnhancer,
    IVectorStore,
)
from markdown_rag_mcp.embeddings import HuggingFaceEmbedder
from markdown_rag_mcp.indexing.chunker import DocumentChunker
from markdown_rag_mcp.indexing.metadata_enhancer import MetadataEnhancer
from markdown_rag_mcp.models import IndexingError
from markdown_rag_mcp.parsers import MarkdownParser
from markdown_rag_mcp.storage import MilvusVectorStore

logger = logging.getLogger(__name__)


class DocumentIndexer(IDocumentIndexer):
    """
    Orchestrates the complete document indexing pipeline.

    Manages the flow from document parsing through chunking, embedding generation,
    and vector storage, with full frontmatter metadata integration.
    """

    def __init__(
        self,
        config,
        document_parser: IDocumentParser | None = None,
        embedding_provider: IEmbeddingProvider | None = None,
        vector_store: IVectorStore | None = None,
        metadata_enhancer: IMetadataEnhancer | None = None,
        chunker: IDocumentChunker | None = None,
    ):
        """
        Initialize the document indexer.

        Args:
            config: RAG configuration
            document_parser: Document parser instance
            embedding_provider: Embedding provider instance
            vector_store: Vector storage instance
        """
        self.config = config
        self.document_parser = document_parser or MarkdownParser(config)
        self.embedding_provider = embedding_provider or HuggingFaceEmbedder(config)
        self.vector_store = vector_store or MilvusVectorStore(config, self.embedding_provider)
        self.metadata_enhancer = metadata_enhancer or MetadataEnhancer()
        self.chunker = chunker or DocumentChunker(config, self.metadata_enhancer)

    async def index_document(self, file_path: Path, force_reindex: bool = False) -> dict[str, Any]:
        """
        Index a single document through the complete pipeline.

        Args:
            file_path: Path to the document to index
            force_reindex: Whether to reindex even if already processed

        Returns:
            Dictionary with indexing results and statistics

        Raises:
            IndexingError: If indexing fails at any stage
        """
        start_time = time.time()

        try:
            logger.info("Starting indexing for document: %s", file_path)

            # Stage 1: Parse document
            logger.debug("Stage 1: Parsing document")
            document = await self.document_parser.parse_file(file_path)
            document.mark_as_processing()

            # Extract raw content for chunking
            if not hasattr(document, '_raw_content'):
                raise IndexingError(
                    "Document parser did not provide raw content", file_path=str(file_path), stage="content_extraction"
                )

            raw_content = document._raw_content
            logger.debug("Parsed document: %d chars, frontmatter: %s", len(raw_content), document.has_frontmatter)

            # Stage 2: Check if already indexed (unless force reindex)
            if not force_reindex:
                # Check if document with same content hash already exists in vector store
                # This is a future optimization - for now we skip this check
                try:
                    if hasattr(self.vector_store, 'get_document_by_hash'):
                        existing_doc = await self.vector_store.get_document_by_hash(document.content_hash)
                        if existing_doc and existing_doc.get('file_path') == str(file_path):
                            logger.info("Document %s already indexed with same content hash, skipping", file_path)
                            return {
                                "status": "skipped",
                                "file_path": str(file_path),
                                "document_id": str(document.id),
                                "content_hash": document.content_hash,
                                "modified_at": document.modified_at,
                                "sections_created": 0,
                                "processing_time": f"{time.time() - start_time:.2f}s",
                                "message": "Document already indexed with same content",
                            }
                except Exception as e:
                    logger.debug("Could not check for duplicate hash: %s", e)
                    # Continue with indexing if hash check fails

            # Stage 3: Chunk document with metadata enhancement
            logger.debug("Stage 3: Chunking document with metadata enhancement")
            sections = self.chunker.chunk_document(document, raw_content)

            if not sections:
                logger.warning("No sections created from document %s", file_path)
                document.mark_as_indexed(0, 0)
                return {
                    "status": "success",
                    "file_path": str(file_path),
                    "document_id": str(document.id),
                    "content_hash": document.content_hash,
                    "modified_at": document.modified_at,
                    "sections_created": 0,
                    "processing_time": f"{time.time() - start_time:.2f}s",
                    "message": "No content to index",
                }

            logger.debug("Created %d sections from document", len(sections))

            # Stage 4: Generate embeddings for all sections
            logger.debug("Stage 4: Generating embeddings for sections")
            section_texts = [section.section_text for section in sections]

            embeddings = await self.embedding_provider.generate_batch_embeddings(section_texts)

            if len(embeddings) != len(sections):
                raise IndexingError(
                    f"Embedding count mismatch: {len(embeddings)} != {len(sections)}",
                    file_path=str(file_path),
                    stage="embedding_generation",
                )

            logger.debug("Generated %d embeddings", len(embeddings))

            # Stage 5: Store in vector database
            logger.debug("Stage 5: Storing sections in vector database")
            await self.vector_store.store_document_sections(sections, embeddings)

            # Stage 6: Update document status
            word_count = len(raw_content.split()) if raw_content else 0
            document.mark_as_indexed(len(sections), word_count)

            processing_time = time.time() - start_time

            # Collect statistics
            chunking_stats = self.chunker.get_chunking_stats(sections)
            enhancement_stats = self.metadata_enhancer.get_enhancement_stats(document)

            result = {
                "status": "success",
                "file_path": str(file_path),
                "document_id": str(document.id),
                "content_hash": document.content_hash,
                "modified_at": document.modified_at,
                "sections_created": len(sections),
                "word_count": word_count,
                "processing_time": f"{processing_time:.2f}s",
                "has_frontmatter": document.has_frontmatter,
                "chunking_stats": chunking_stats,
                "enhancement_stats": enhancement_stats,
            }

            logger.info(
                "Successfully indexed document %s: %d sections in %.2fs", file_path, len(sections), processing_time
            )

            return result

        except Exception as e:
            # Mark document as failed if we have it
            if 'document' in locals():
                document.mark_as_failed(str(e))

            logger.error("Failed to index document %s: %s", file_path, e)
            raise IndexingError(
                f"Document indexing failed: {e}",
                file_path=str(file_path),
                stage="indexing_pipeline",
                underlying_error=e,
            ) from e

    async def update_document(self, file_path: Path) -> dict[str, Any]:
        """
        Update an existing document in the index.

        Args:
            file_path: Path to the document to update

        Returns:
            Dictionary with update results
        """
        try:
            logger.info("Updating document: %s", file_path)

            # Remove existing document from vector store
            await self.vector_store.delete_document(str(file_path))

            # Re-index the document
            result = await self.index_document(file_path, force_reindex=True)
            result["operation"] = "update"

            logger.info("Successfully updated document: %s", file_path)
            return result

        except Exception as e:
            logger.error("Failed to update document %s: %s", file_path, e)
            raise IndexingError(
                f"Document update failed: {e}", file_path=str(file_path), stage="document_update", underlying_error=e
            ) from e

    async def remove_document(self, file_path: Path) -> dict[str, Any]:
        """
        Remove a document from the index.

        Args:
            file_path: Path to the document to remove

        Returns:
            Dictionary with removal results
        """
        try:
            logger.info("Removing document: %s", file_path)

            # Remove from vector store
            await self.vector_store.delete_document(str(file_path))

            result = {
                "status": "success",
                "file_path": str(file_path),
                "operation": "remove",
                "message": "Document removed from index",
            }

            logger.info("Successfully removed document: %s", file_path)
            return result

        except Exception as e:
            logger.error("Failed to remove document %s: %s", file_path, e)
            raise IndexingError(
                f"Document removal failed: {e}", file_path=str(file_path), stage="document_removal", underlying_error=e
            ) from e

    async def batch_index_documents(
        self, file_paths: list[Path], force_reindex: bool = False, max_concurrent: int = None
    ) -> dict[str, Any]:
        """
        Index multiple documents concurrently.

        Args:
            file_paths: List of document paths to index
            force_reindex: Whether to reindex existing documents
            max_concurrent: Maximum concurrent indexing operations

        Returns:
            Dictionary with batch indexing results
        """
        import asyncio

        start_time = time.time()
        max_concurrent = max_concurrent or self.config.max_concurrent_indexing

        try:
            logger.info("Starting batch indexing of %d documents", len(file_paths))

            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def index_with_semaphore(file_path):
                async with semaphore:
                    try:
                        return await self.index_document(file_path, force_reindex)
                    except Exception as e:
                        return {"status": "failed", "file_path": str(file_path), "error": str(e)}

            # Process all documents
            results = await asyncio.gather(
                *[index_with_semaphore(path) for path in file_paths], return_exceptions=False
            )

            # Aggregate results
            successful = [r for r in results if r["status"] == "success"]
            failed = [r for r in results if r["status"] == "failed"]

            processing_time = time.time() - start_time

            batch_result = {
                "status": "completed",
                "total_files": len(file_paths),
                "successful": len(successful),
                "failed": len(failed),
                "processing_time": f"{processing_time:.2f}s",
                "results": results,
            }

            logger.info(
                "Batch indexing complete: %d/%d successful in %.2fs", len(successful), len(file_paths), processing_time
            )

            return batch_result

        except Exception as e:
            logger.error("Batch indexing failed: %s", e)
            raise IndexingError(f"Batch indexing failed: {e}", stage="batch_processing", underlying_error=e) from e
