"""
Document chunker with frontmatter-enhanced processing.

Creates document sections using heading-based boundaries and size limits,
incorporating frontmatter metadata for improved context and search relevance.
"""

import logging
import re

from markdown_rag_mcp.core import IDocumentChunker, IMetadataEnhancer
from markdown_rag_mcp.models import ChunkingError, Document, DocumentSection, SectionType

logger = logging.getLogger(__name__)


class DocumentChunker(IDocumentChunker):
    """
    Chunks documents into sections with frontmatter metadata integration.

    Uses heading-based boundaries with size limits to create searchable sections
    that fit within embedding model context windows while preserving logical
    document structure and incorporating metadata for enhanced search.
    """

    def __init__(self, config, metadata_enhancer: IMetadataEnhancer = None):
        """
        Initialize the document chunker.

        Args:
            config: RAG configuration with chunking parameters
            metadata_enhancer: Optional metadata enhancer for frontmatter integration
        """
        self.config = config
        self.metadata_enhancer = metadata_enhancer
        self.max_chunk_size = config.chunk_size_limit
        self.chunk_overlap = config.chunk_overlap

    def chunk_document(self, document: Document, content: str) -> list[DocumentSection]:
        """
        Chunk a document into sections with metadata enhancement.

        Args:
            document: Document object with frontmatter metadata
            content: Raw document content to chunk

        Returns:
            List of DocumentSection objects

        Raises:
            ChunkingError: If chunking fails
        """
        try:
            logger.debug(
                "Chunking document %s (content length: %d, has_frontmatter: %s)",
                document.filename,
                len(content),
                document.has_frontmatter,
            )

            if not content or not content.strip():
                logger.warning("Document %s has no content to chunk", document.filename)
                return []

            # Find heading boundaries
            heading_boundaries = self._find_heading_boundaries(content)
            logger.debug("Found %d heading boundaries in document", len(heading_boundaries))

            # Create sections based on headings
            sections = self._create_heading_sections(document, content, heading_boundaries)

            # Split oversized sections
            final_sections = []
            for section in sections:
                if self._estimate_tokens(section.section_text) > self.max_chunk_size:
                    split_sections = self._split_large_section(document, section)
                    final_sections.extend(split_sections)
                else:
                    final_sections.append(section)

            # Re-index sections
            for i, section in enumerate(final_sections):
                section.chunk_index = i

            logger.debug("Created %d sections from document %s", len(final_sections), document.filename)
            return final_sections

        except Exception as e:
            logger.error("Failed to chunk document %s: %s", document.filename, e)
            raise ChunkingError(
                f"Failed to chunk document: {e}",
                file_path=document.file_path,
                operation="chunk_document",
                underlying_error=e,
            ) from e

    def _find_heading_boundaries(self, content: str) -> list[tuple[int, str, int, int]]:
        """
        Find markdown heading boundaries in content.

        Args:
            content: Document content

        Returns:
            List of (position, heading_text, level, end_position) tuples
        """
        boundaries = []

        # Match markdown headings (## Heading or # Heading)
        heading_pattern = r'^(#{1,6})\s+(.+?)$'

        for match in re.finditer(heading_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()

            boundaries.append((start_pos, heading_text, level, end_pos))

        return boundaries

    def _create_heading_sections(
        self, document: Document, content: str, boundaries: list[tuple[int, str, int, int]]
    ) -> list[DocumentSection]:
        """
        Create sections based on heading boundaries.

        Args:
            document: Parent document
            content: Document content
            boundaries: List of heading boundaries

        Returns:
            List of DocumentSection objects
        """
        sections = []

        if not boundaries:
            # No headings found - create single section
            section_text = content.strip()
            if section_text:
                # Apply metadata enhancement
                if document.has_frontmatter:
                    enhanced_text = self.metadata_enhancer.enhance_document_for_embedding(document, section_text)
                else:
                    enhanced_text = section_text

                section = DocumentSection(
                    document_id=document.id,
                    section_text=enhanced_text,
                    heading=None,
                    heading_level=None,
                    chunk_index=0,
                    token_count=self._estimate_tokens(enhanced_text),
                    start_position=0,
                    end_position=len(content),
                    section_type=SectionType.PARAGRAPH,
                )
                sections.append(section)

            return sections

        # Create sections between headings
        for i, (start_pos, heading_text, level, heading_end) in enumerate(boundaries):
            # Determine section end position
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1][0]
            else:
                end_pos = len(content)

            # Extract section content
            section_content = content[heading_end:end_pos].strip()

            # Skip empty sections
            if not section_content:
                continue

            # Include heading in section for context
            full_section_text = f"{heading_text}\n\n{section_content}"

            # Apply metadata enhancement for sections
            if document.has_frontmatter:
                # Create a temporary section for enhancement
                temp_section = DocumentSection(
                    document_id=document.id,
                    section_text=full_section_text,
                    heading=heading_text,
                    heading_level=level,
                    chunk_index=len(sections),
                    token_count=0,
                    start_position=start_pos,
                    end_position=end_pos,
                    section_type=SectionType.HEADING,
                )
                enhanced_text = self.metadata_enhancer.enhance_section_for_embedding(document, temp_section)
            else:
                enhanced_text = full_section_text

            # Create final section
            section = DocumentSection(
                document_id=document.id,
                section_text=enhanced_text,
                heading=heading_text,
                heading_level=level,
                chunk_index=len(sections),
                token_count=self._estimate_tokens(enhanced_text),
                start_position=start_pos,
                end_position=end_pos,
                section_type=SectionType.HEADING,
            )

            sections.append(section)

        return sections

    def _split_large_section(self, document: Document, section: DocumentSection) -> list[DocumentSection]:
        """
        Split a section that exceeds token limits.

        Args:
            document: Parent document
            section: Section to split

        Returns:
            List of smaller sections
        """
        logger.debug(
            "Splitting large section '%s' (tokens: %d, limit: %d)",
            section.heading or f"section-{section.chunk_index}",
            section.token_count,
            self.max_chunk_size,
        )

        # Simple paragraph-based splitting
        paragraphs = section.section_text.split('\n\n')

        sections = []
        current_text = ""
        current_start = section.start_position

        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed limit
            test_text = f"{current_text}\n\n{paragraph}" if current_text else paragraph

            if self._estimate_tokens(test_text) > self.max_chunk_size and current_text:
                # Create section from current text
                subsection = DocumentSection(
                    document_id=document.id,
                    section_text=current_text.strip(),
                    heading=section.heading,
                    heading_level=section.heading_level,
                    chunk_index=section.chunk_index,  # Will be re-indexed later
                    token_count=self._estimate_tokens(current_text),
                    start_position=current_start,
                    end_position=current_start + len(current_text),
                    section_type=section.section_type,
                )
                sections.append(subsection)

                # Start new section with overlap
                if self.chunk_overlap > 0 and current_text:
                    overlap_text = self._get_overlap_text(current_text, self.chunk_overlap)
                    current_text = f"{overlap_text}\n\n{paragraph}"
                else:
                    current_text = paragraph

                current_start += len(current_text) - len(paragraph)
            else:
                # Add paragraph to current section
                current_text = test_text

        # Add final section
        if current_text.strip():
            subsection = DocumentSection(
                document_id=document.id,
                section_text=current_text.strip(),
                heading=section.heading,
                heading_level=section.heading_level,
                chunk_index=section.chunk_index,
                token_count=self._estimate_tokens(current_text),
                start_position=current_start,
                end_position=section.end_position,
                section_type=section.section_type,
            )
            sections.append(subsection)

        logger.debug("Split section into %d subsections", len(sections))
        return sections

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """
        Get overlap text from the end of a section.

        Args:
            text: Source text
            overlap_tokens: Number of tokens for overlap

        Returns:
            Overlap text
        """
        words = text.split()
        if len(words) <= overlap_tokens:
            return text

        return ' '.join(words[-overlap_tokens:])

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return max(1, len(text) // 4)

    def get_chunking_stats(self, sections: list[DocumentSection]) -> dict:
        """
        Get statistics about the chunking process.

        Args:
            sections: List of created sections

        Returns:
            Dictionary with chunking statistics
        """
        if not sections:
            return {"total_sections": 0, "avg_tokens": 0, "max_tokens": 0, "min_tokens": 0, "sections_with_headings": 0}

        token_counts = [section.token_count for section in sections]

        return {
            "total_sections": len(sections),
            "avg_tokens": sum(token_counts) / len(token_counts),
            "max_tokens": max(token_counts),
            "min_tokens": min(token_counts),
            "sections_with_headings": len([s for s in sections if s.heading]),
        }
