"""
Markdown document parser implementation.

Parses markdown files with frontmatter support using FrontmatterParser
and creates Document objects with structured content and validated metadata.
"""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from markdown_rag_mcp.core import IDocumentParser
from markdown_rag_mcp.models import Document, DocumentParsingError, ProcessingStatus
from markdown_rag_mcp.parsers.frontmatter_parser import FrontmatterParser

logger = logging.getLogger(__name__)


class MarkdownParser(IDocumentParser):
    """
    Parser for markdown files with frontmatter support.

    Extracts content, frontmatter metadata, and creates Document objects
    ready for further processing and chunking.
    """

    def __init__(self, config):
        """Initialize the markdown parser with configuration."""
        self.config = config
        self.frontmatter_parser = FrontmatterParser()

    async def parse_file(self, file_path: Path) -> Document:
        """
        Parse a markdown file and return a Document object.

        Args:
            file_path: Path to the markdown file to parse

        Returns:
            Document object with parsed content and metadata

        Raises:
            DocumentParsingError: If the file cannot be parsed
        """
        try:
            logger.debug("Parsing markdown file %s", file_path)

            # Validate file
            if not file_path.exists():
                raise DocumentParsingError(
                    f"File does not exist: {file_path}",
                    file_path=str(file_path),
                    parsing_stage="file_validation",
                )

            # Check file size
            file_size = file_path.stat().st_size
            max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                raise DocumentParsingError(
                    f"File too large: {file_size} bytes (max: {max_size_bytes})",
                    file_path=str(file_path),
                    parsing_stage="size_validation",
                )

            # Parse frontmatter and content using FrontmatterParser
            try:
                frontmatter_metadata, markdown_content = self.frontmatter_parser.parse_file(file_path)
            except Exception as e:
                # Convert FrontmatterParser errors to DocumentParsingError
                if "encoding" in str(e).lower() or "unicode" in str(e).lower():
                    raise DocumentParsingError(
                        f"File encoding error: {e}",
                        file_path=str(file_path),
                        parsing_stage="file_reading",
                        underlying_error=e,
                    ) from e
                else:
                    raise DocumentParsingError(
                        f"Frontmatter parsing error: {e}",
                        file_path=str(file_path),
                        parsing_stage="frontmatter_parsing",
                        underlying_error=e,
                    ) from e

            # Calculate content hash
            content_hash = self._calculate_content_hash(markdown_content, frontmatter_metadata)

            # Get file timestamps
            stat = file_path.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime, UTC)
            modified_at = datetime.fromtimestamp(stat.st_mtime, UTC)

            # Calculate word count
            word_count = len(markdown_content.split()) if markdown_content else 0

            # Create Document object
            document = Document(
                file_path=str(file_path.absolute()),
                content_hash=content_hash,
                file_size=file_size,
                created_at=created_at,
                modified_at=modified_at,
                processing_status=ProcessingStatus.PENDING,
                frontmatter=frontmatter_metadata,
                word_count=word_count,
            )

            # Store the raw content for chunking (temporary attribute)
            document._raw_content = markdown_content

            logger.debug("Successfully parsed document %s", document.filename)
            return document

        except DocumentParsingError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error("Unexpected error parsing %s: %s", file_path, e)
            raise DocumentParsingError(
                f"Unexpected parsing error: {e}",
                file_path=str(file_path),
                parsing_stage="general_parsing",
                underlying_error=e,
            ) from e

    def supports_file_type(self, file_path: Path) -> bool:
        """
        Check if this parser supports the given file type.

        Args:
            file_path: Path to check

        Returns:
            True if the parser can handle this file type
        """
        return self.config.is_file_supported(file_path)

    def _calculate_content_hash(self, content: str, metadata: dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash of file content and metadata.

        Args:
            content: File text content
            metadata: Frontmatter metadata dictionary

        Returns:
            SHA-256 hash as hexadecimal string
        """
        # Combine content and metadata for hashing
        combined_content = content or ""

        # Add metadata in a consistent way
        if metadata:
            # Sort metadata keys for consistent hashing
            sorted_metadata = {k: metadata[k] for k in sorted(metadata.keys())}
            metadata_str = str(sorted_metadata)
            combined_content += metadata_str

        # Calculate hash
        hash_obj = hashlib.sha256(combined_content.encode('utf-8'))
        return hash_obj.hexdigest()

    def extract_text_content(self, document: Document) -> str:
        """
        Extract plain text content from a parsed document.

        Args:
            document: Parsed document object

        Returns:
            Plain text content without markdown formatting
        """
        # This is a simplified implementation
        # Full implementation would use markdown-it-py to properly parse
        # markdown structure and extract clean text
        if hasattr(document, '_raw_content'):
            return document._raw_content
        return ""
