"""
Query processing implementation for search operations.

Handles natural language queries, embedding generation, and coordination
with vector store for similarity search.
"""

import logging
from typing import Any

from markdown_rag_mcp.core import IEmbeddingProvider, IVectorStore
from markdown_rag_mcp.models import QueryResult, SearchError, SearchRequest

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Processes search queries and coordinates with embedding and storage components.

    Handles query preprocessing, embedding generation, and result ranking
    for natural language search operations.
    """

    def __init__(self, config, embedding_provider: IEmbeddingProvider, vector_store: IVectorStore):
        """
        Initialize the query processor.

        Args:
            config: System configuration
            embedding_provider: Provider for generating query embeddings
            vector_store: Vector database for similarity search
        """
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def search(self, request: SearchRequest) -> list[QueryResult]:
        """
        Process a search request and return ranked results.

        Args:
            request: Search request with query and parameters

        Returns:
            List of query results ordered by relevance

        Raises:
            SearchError: If search processing fails
        """
        try:
            logger.debug("Processing search request: %s", request.query)

            # Preprocess query
            processed_query = self._preprocess_query(request.query)

            # Generate query embedding
            query_embedding = await self.embedding_provider.generate_embedding(processed_query)
            logger.debug("Generated query embedding")

            # Search vector store
            results = await self.vector_store.search_similar(
                query_embedding=query_embedding,
                limit=request.limit,
                similarity_threshold=request.similarity_threshold,
                metadata_filters=request.metadata_filters,
            )

            # Post-process results
            processed_results = self._post_process_results(results, request)

            logger.debug("Search completed: %d results", len(processed_results))
            return processed_results

        except Exception as e:
            logger.error("Query processing failed: %s", {e})
            raise SearchError(
                f"Failed to process search query: {e}",
                query=request.query,
                search_stage="query_processing",
                underlying_error=e,
            ) from e

    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess the query string for better matching.

        Args:
            query: Raw query string

        Returns:
            Preprocessed query string
        """
        # Basic preprocessing - in full implementation would include:
        # - Tokenization
        # - Stop word removal (optional)
        # - Query expansion
        # - Spell correction
        processed = query.strip()

        # Remove extra whitespace
        processed = ' '.join(processed.split())

        return processed

    def _post_process_results(self, results: list[QueryResult], request: SearchRequest) -> list[QueryResult]:
        """
        Post-process search results for final ranking and filtering.

        Args:
            results: Raw search results from vector store
            request: Original search request

        Returns:
            Processed and ranked results
        """
        # Results are already filtered by threshold in vector store
        processed_results = results

        # Apply additional filtering if needed
        if request.metadata_filters:
            processed_results = self._apply_metadata_filters(processed_results, request.metadata_filters)

        # Sort by confidence score (descending) if not already sorted
        processed_results.sort(key=lambda r: r.confidence_score, reverse=True)

        # Limit results
        processed_results = processed_results[: request.limit]

        return processed_results

    def _apply_metadata_filters(self, results: list[QueryResult], filters: dict[str, Any]) -> list[QueryResult]:
        """
        Apply metadata filters to search results.

        Args:
            results: Results to filter
            filters: Metadata filter criteria

        Returns:
            Filtered results
        """
        if not filters:
            return results

        filtered_results = []
        for result in results:
            if self._matches_filters(result.metadata, filters):
                filtered_results.append(result)

        return filtered_results

    def _matches_filters(self, metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        """
        Check if metadata matches the given filters.

        Args:
            metadata: Document metadata
            filters: Filter criteria

        Returns:
            True if metadata matches all filters
        """
        for filter_key, filter_value in filters.items():
            metadata_value = metadata.get(filter_key)

            if metadata_value is None:
                return False

            # Handle different filter types
            if isinstance(filter_value, list):
                # Filter value is a list - check if any item matches
                if isinstance(metadata_value, list):
                    # Both are lists - check for intersection
                    if not set(filter_value) & set(metadata_value):
                        return False
                else:
                    # Metadata is single value - check if it's in filter list
                    if metadata_value not in filter_value:
                        return False
            else:
                # Filter value is single value - exact match
                if metadata_value != filter_value:
                    return False

        return True
