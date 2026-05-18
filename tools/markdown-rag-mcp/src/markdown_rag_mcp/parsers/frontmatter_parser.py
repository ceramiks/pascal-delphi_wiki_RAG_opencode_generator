"""
Frontmatter parser for extracting YAML metadata from markdown files.

This module handles parsing of frontmatter sections containing structured metadata
like title, tags, topics, keywords, summary, and llm_hints that enhance search
accuracy and content understanding.
"""

import logging
from pathlib import Path
from typing import Any

import frontmatter

from markdown_rag_mcp.models import ParsingError

logger = logging.getLogger(__name__)


class FrontmatterParser:
    """
    Parser for extracting YAML frontmatter from markdown files.

    Handles optional frontmatter sections that provide structured metadata
    to enhance search accuracy and content understanding.
    """

    SUPPORTED_FIELDS = {"title", "tags", "topics", "keywords", "summary", "llm_hints"}

    def __init__(self):
        """Initialize the frontmatter parser."""
        pass

    def parse_file(self, file_path: str | Path) -> tuple[dict[str, Any], str]:
        """
        Parse a markdown file and extract frontmatter and content.

        Args:
            file_path: Path to the markdown file to parse

        Returns:
            Tuple of (frontmatter_dict, markdown_content)

        Raises:
            ParsingError: If file cannot be read or parsed
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise ParsingError(
                    f"Markdown file not found: {file_path}", operation="parse_file", file_path=str(file_path)
                )

            # Read and parse the file with frontmatter
            with open(file_path, encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Extract frontmatter metadata
            metadata = self._extract_metadata(post.metadata, str(file_path))

            # Return cleaned metadata and content
            return metadata, post.content

        except Exception as e:
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(
                f"Failed to parse frontmatter from {file_path}: {e}",
                operation="parse_file",
                file_path=str(file_path),
                underlying_error=e,
            ) from e

    def parse_string(self, content: str) -> tuple[dict[str, Any], str]:
        """
        Parse frontmatter from a markdown string.

        Args:
            content: Markdown content string with optional frontmatter

        Returns:
            Tuple of (frontmatter_dict, markdown_content)

        Raises:
            ParsingError: If content cannot be parsed
        """
        try:
            # Parse the string with frontmatter
            post = frontmatter.loads(content)

            # Extract frontmatter metadata
            metadata = self._extract_metadata(post.metadata)

            # Return cleaned metadata and content
            return metadata, post.content

        except Exception as e:
            raise ParsingError(
                f"Failed to parse frontmatter from string content: {e}", operation="parse_string", underlying_error=e
            ) from e

    def _extract_metadata(self, raw_metadata: dict[str, Any], file_path: str | None = None) -> dict[str, Any]:
        """
        Extract and validate supported frontmatter fields.

        Args:
            raw_metadata: Raw frontmatter metadata dictionary
            file_path: Optional file path for logging context

        Returns:
            Dictionary with cleaned and validated metadata
        """
        metadata = {}

        for field, value in raw_metadata.items():
            if field in self.SUPPORTED_FIELDS:
                cleaned_value = self._clean_field_value(field, value, file_path)
                if cleaned_value is not None:
                    metadata[field] = cleaned_value
            else:
                # Log unsupported fields for awareness but don't include them
                logger.debug("Unsupported frontmatter field '%s' found in %s", field, file_path or "string content")

        return metadata

    def _clean_field_value(self, field: str, value: Any, file_path: str | None = None) -> Any:
        """
        Clean and validate a frontmatter field value.

        Args:
            field: Field name
            value: Raw field value
            file_path: Optional file path for logging context

        Returns:
            Cleaned value or None if invalid
        """
        if value is None:
            return None

        try:
            # Handle string fields (title, summary)
            if field in {"title", "summary"}:
                if isinstance(value, str):
                    return value.strip()
                else:
                    return str(value).strip()

            # Handle list fields (tags, topics, keywords, llm_hints)
            elif field in {"tags", "topics", "keywords", "llm_hints"}:
                if isinstance(value, list):
                    # Clean string items and filter out empty ones
                    cleaned_list = []
                    for item in value:
                        if isinstance(item, str):
                            cleaned_item = item.strip()
                            if cleaned_item:
                                cleaned_list.append(cleaned_item)
                        else:
                            cleaned_item = str(item).strip()
                            if cleaned_item:
                                cleaned_list.append(cleaned_item)
                    return cleaned_list if cleaned_list else None

                elif isinstance(value, str):
                    # Handle comma-separated string
                    items = [item.strip() for item in value.split(",") if item.strip()]
                    return items if items else None

                else:
                    # Try to convert to string and split
                    str_value = str(value).strip()
                    if str_value:
                        items = [item.strip() for item in str_value.split(",") if item.strip()]
                        return items if items else None

            # Field not recognized (shouldn't happen due to SUPPORTED_FIELDS check)
            logger.warning("Unknown field type handling for '%s' in %s", field, file_path or "string content")
            return None

        except Exception as e:
            logger.warning(
                "Failed to clean field '%s' with value '%s' in %s: %s", field, value, file_path or "string content", e
            )
            return None

    def has_frontmatter(self, content: str) -> bool:
        """
        Check if content contains frontmatter without fully parsing.

        Args:
            content: Markdown content string

        Returns:
            True if content appears to have frontmatter
        """
        return content.strip().startswith("---")

    def get_supported_fields(self) -> set[str]:
        """
        Get the set of supported frontmatter fields.

        Returns:
            Set of supported field names
        """
        return self.SUPPORTED_FIELDS.copy()
