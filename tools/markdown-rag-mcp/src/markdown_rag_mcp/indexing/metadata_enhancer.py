"""
Metadata enhancer for improving embeddings and search using frontmatter.

This module combines document content with structured frontmatter metadata
to create enhanced text for embedding generation, improving search accuracy
and relevance scoring.
"""

import logging
from typing import Any

from markdown_rag_mcp.core import IMetadataEnhancer
from markdown_rag_mcp.models import Document, DocumentSection

logger = logging.getLogger(__name__)


class MetadataEnhancer(IMetadataEnhancer):
    """
    Enhances document content with frontmatter metadata for improved embeddings.

    This class creates enhanced text representations that combine the original
    content with structured metadata from frontmatter, leading to better
    semantic similarity matching and search relevance.
    """

    def __init__(
        self,
        include_title_weight: float = 2.0,
        include_summary_weight: float = 1.5,
        include_keywords_weight: float = 1.2,
        include_tags_weight: float = 1.0,
        include_llm_hints: bool = True,
    ):
        """
        Initialize the metadata enhancer.

        Args:
            include_title_weight: Multiplier for title repetition in enhanced text
            include_summary_weight: Multiplier for summary repetition
            include_keywords_weight: Multiplier for keywords repetition
            include_tags_weight: Multiplier for tags repetition
            include_llm_hints: Whether to include llm_hints in enhanced text
        """
        self.include_title_weight = max(1.0, include_title_weight)
        self.include_summary_weight = max(1.0, include_summary_weight)
        self.include_keywords_weight = max(1.0, include_keywords_weight)
        self.include_tags_weight = max(1.0, include_tags_weight)
        self.include_llm_hints = include_llm_hints

    def enhance_document_for_embedding(self, document: Document, content: str) -> str:
        """
        Create enhanced text representation of document content for embedding.

        Combines the original content with frontmatter metadata to improve
        semantic matching. The enhancement is done through strategic repetition
        and contextual framing of metadata.

        Args:
            document: Document with frontmatter metadata
            content: Original document content

        Returns:
            Enhanced text suitable for embedding generation
        """
        if not document.has_frontmatter:
            logger.debug("No frontmatter found for document %s, using original content", document.file_path)
            return content

        enhanced_parts = []

        # Start with title if available (high weight for document-level matching)
        if document.title and document.title != document.filename:
            title_text = f"Title: {document.title}"
            # Repeat title based on weight for stronger embedding signal
            for _ in range(int(self.include_title_weight)):
                enhanced_parts.append(title_text)

        # Add summary for context (medium-high weight)
        if document.summary:
            summary_text = f"Summary: {document.summary}"
            for _ in range(int(self.include_summary_weight)):
                enhanced_parts.append(summary_text)

        # Add keywords for semantic signals (medium weight)
        if document.keywords:
            keywords_text = f"Keywords: {', '.join(document.keywords)}"
            for _ in range(int(self.include_keywords_weight)):
                enhanced_parts.append(keywords_text)

        # Add tags for categorization (base weight)
        if document.tags:
            tags_text = f"Tags: {', '.join(document.tags)}"
            for _ in range(int(self.include_tags_weight)):
                enhanced_parts.append(tags_text)

        # Add topics for thematic context
        if document.topics:
            topics_text = f"Topics: {', '.join(document.topics)}"
            enhanced_parts.append(topics_text)

        # Add LLM hints for retrieval guidance
        if self.include_llm_hints and document.llm_hints:
            hints_text = f"Context: {document.llm_hints}"
            enhanced_parts.append(hints_text)

        # Add the original content
        enhanced_parts.append(content)

        enhanced_content = "\n\n".join(enhanced_parts)

        logger.debug(
            "Enhanced document %s: added %d metadata parts, content length %d -> %d",
            document.file_path,
            len(enhanced_parts) - 1,  # -1 for original content
            len(content),
            len(enhanced_content),
        )

        return enhanced_content

    def enhance_section_for_embedding(self, document: Document, section: DocumentSection) -> str:
        """
        Create enhanced text representation of a document section for embedding.

        Combines section content with relevant document-level frontmatter
        to provide better context for semantic matching.

        Args:
            document: Parent document with frontmatter metadata
            section: Document section to enhance

        Returns:
            Enhanced section text suitable for embedding generation
        """
        enhanced_parts = []

        # Add document title for context (if different from filename)
        if document.title and document.title != document.filename:
            enhanced_parts.append(f"Document: {document.title}")

        # Add section heading if present
        if section.heading:
            enhanced_parts.append(f"Section: {section.heading}")

        # Add relevant tags for this section's context
        if document.tags:
            # Limit tags to avoid overwhelming section content
            relevant_tags = document.tags[:3]
            enhanced_parts.append(f"Tags: {', '.join(relevant_tags)}")

        # Add keywords for semantic signals (limited for sections)
        if document.keywords:
            relevant_keywords = document.keywords[:5]
            enhanced_parts.append(f"Keywords: {', '.join(relevant_keywords)}")

        # Add the section content
        enhanced_parts.append(section.section_text)

        enhanced_content = "\n".join(enhanced_parts)

        logger.debug(
            "Enhanced section %s in document %s: content length %d -> %d",
            section.heading or f"section-{section.chunk_index}",
            document.file_path,
            len(section.section_text),
            len(enhanced_content),
        )

        return enhanced_content

    def create_metadata_context(self, document: Document) -> str:
        """
        Create a metadata-only context string for search enhancement.

        This creates a searchable representation of just the metadata,
        useful for boosting relevance when metadata matches query terms.

        Args:
            document: Document with frontmatter metadata

        Returns:
            Metadata context string
        """
        if not document.has_frontmatter:
            return ""

        context_parts = []

        if document.title and document.title != document.filename:
            context_parts.append(document.title)

        if document.summary:
            context_parts.append(document.summary)

        if document.tags:
            context_parts.extend(document.tags)

        if document.topics:
            context_parts.extend(document.topics)

        if document.keywords:
            context_parts.extend(document.keywords)

        if self.include_llm_hints and document.llm_hints:
            context_parts.append(document.llm_hints)

        return " ".join(context_parts)

    def get_enhancement_stats(self, document: Document) -> dict[str, Any]:
        """
        Get statistics about metadata enhancement for a document.

        Args:
            document: Document to analyze

        Returns:
            Dictionary with enhancement statistics
        """
        stats = {
            "has_frontmatter": document.has_frontmatter,
            "has_title": bool(document.title and document.title != document.filename),
            "has_summary": bool(document.summary),
            "tag_count": len(document.tags),
            "topic_count": len(document.topics),
            "keyword_count": len(document.keywords),
            "has_llm_hints": bool(document.llm_hints),
            "metadata_fields": [],
        }

        # Track which metadata fields are available
        if document.title:
            stats["metadata_fields"].append("title")
        if document.summary:
            stats["metadata_fields"].append("summary")
        if document.tags:
            stats["metadata_fields"].append("tags")
        if document.topics:
            stats["metadata_fields"].append("topics")
        if document.keywords:
            stats["metadata_fields"].append("keywords")
        if document.llm_hints:
            stats["metadata_fields"].append("llm_hints")

        return stats
