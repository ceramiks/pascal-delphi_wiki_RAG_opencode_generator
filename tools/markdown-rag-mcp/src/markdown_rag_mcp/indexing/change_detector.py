"""
Change detector for identifying document modifications using file hashes.

Compares file content hashes to determine if documents have been modified
since their last indexing, enabling efficient incremental updates.
"""

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from markdown_rag_mcp.core import IChangeDetector
from markdown_rag_mcp.models import Document, FileChangeInfo, IndexingError

logger = logging.getLogger(__name__)


class DocumentChangeDetector(IChangeDetector):
    """
    Detects changes in document files using content hashing.

    Maintains an index of file hashes and modification times to efficiently
    identify which documents need reindexing when files are modified.
    """

    def __init__(self, config):
        """
        Initialize the change detector.

        Args:
            config: RAG configuration
        """
        self.config = config

        # In-memory cache of file hashes and metadata
        # In a full implementation, this would be persisted to disk or database
        self._file_index: dict[str, dict[str, any]] = {}

    async def scan_directory_for_changes(
        self,
        directory_path: Path,
        recursive: bool = True,
        known_documents: list[Document] | None = None,
    ) -> list[FileChangeInfo]:
        """
        Scan a directory and detect all file changes since last scan.

        Args:
            directory_path: Directory to scan
            recursive: Whether to scan subdirectories
            known_documents: List of previously indexed documents

        Returns:
            List of detected file changes

        Raises:
            IndexingError: If scanning fails
        """
        try:
            logger.info("Scanning directory for changes: %s", directory_path)

            if not directory_path.exists():
                raise IndexingError(
                    f"Directory does not exist: {directory_path}", file_path=str(directory_path), stage="directory_scan"
                )

            # Build index of known documents
            known_files = {}
            if known_documents:
                for doc in known_documents:
                    file_path = Path(doc.file_path)
                    known_files[str(file_path)] = {
                        'hash': doc.content_hash,
                        'modified_time': doc.modified_at,
                        'document_id': doc.id,
                    }

            changes = []

            # Find current files
            pattern = "**/*.md" if recursive else "*.md"
            current_files = set()

            for file_path in directory_path.glob(pattern):
                if self._should_process_file(file_path):
                    current_files.add(str(file_path))

                    # Check if file has changed
                    change_info = await self._check_file_for_changes(file_path, known_files.get(str(file_path)))

                    if change_info:
                        changes.append(change_info)

            # Check for deleted files
            for known_file_path, known_file_info in known_files.items():
                if known_file_path not in current_files:
                    # File was deleted
                    file_path = Path(known_file_path)
                    change_info = FileChangeInfo(
                        file_path=file_path,
                        change_type='deleted',
                        old_hash=known_file_info['hash'],
                        old_modified_time=known_file_info['modified_time'],
                    )
                    changes.append(change_info)

            logger.info("Detected %d file changes in directory", len(changes))
            return changes

        except Exception as e:
            logger.error("Failed to scan directory for changes: %s", e)
            raise IndexingError(
                f"Directory change scan failed: {e}",
                file_path=str(directory_path),
                stage="change_detection",
                underlying_error=e,
            ) from e

    async def check_file_changed(
        self, file_path: Path, known_document: Document | None = None
    ) -> FileChangeInfo | None:
        """
        Check if a single file has changed.

        Args:
            file_path: Path to file to check
            known_document: Previously indexed document info

        Returns:
            FileChangeInfo if changed, None if unchanged
        """
        try:
            if not file_path.exists():
                if known_document:
                    # File was deleted
                    return FileChangeInfo(
                        file_path=file_path,
                        change_type='deleted',
                        old_hash=known_document.content_hash,
                        old_modified_time=known_document.modified_at,
                    )
                return None

            known_info = None
            if known_document:
                known_info = {
                    'hash': known_document.content_hash,
                    'modified_time': known_document.modified_at,
                    'document_id': known_document.id,
                }

            return await self._check_file_for_changes(file_path, known_info)

        except Exception as e:
            logger.error("Failed to check file changes for %s: %s", file_path, e)
            raise IndexingError(
                f"File change check failed: {e}",
                file_path=str(file_path),
                stage="file_change_check",
                underlying_error=e,
            ) from e

    async def _check_file_for_changes(
        self, file_path: Path, known_info: dict[str, any] | None = None
    ) -> FileChangeInfo | None:
        """
        Check if a file has changed compared to known information.

        Args:
            file_path: Path to file to check
            known_info: Dictionary with known file information

        Returns:
            FileChangeInfo if changed, None if unchanged
        """
        try:
            # Get current file stats
            stat = file_path.stat()
            current_modified_time = datetime.fromtimestamp(stat.st_mtime, UTC)

            # If we don't have known info, this is a new file
            if not known_info:
                current_hash = await self._calculate_file_hash(file_path)
                return FileChangeInfo(
                    file_path=file_path,
                    change_type='created',
                    new_hash=current_hash,
                    new_modified_time=current_modified_time,
                )

            # Quick check: compare modification times
            if current_modified_time <= known_info['modified_time']:
                # File hasn't been modified since last index
                return None

            # File was modified - check if content actually changed
            current_hash = await self._calculate_file_hash(file_path)

            if current_hash == known_info['hash']:
                # Hash is the same - file content unchanged despite mtime difference
                # This can happen with editors that preserve content but update mtime
                logger.debug("File %s has newer mtime but same content hash - no change", file_path)
                return None

            # Content has changed
            return FileChangeInfo(
                file_path=file_path,
                change_type='modified',
                old_hash=known_info['hash'],
                new_hash=current_hash,
                old_modified_time=known_info['modified_time'],
                new_modified_time=current_modified_time,
            )

        except Exception as e:
            logger.error("Error checking file changes for %s: %s", file_path, e)
            return None

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of file content and metadata.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash as hexadecimal string
        """
        try:
            hash_obj = hashlib.sha256()

            # Hash file content
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)

            # Include file size and modification time for additional verification
            stat = file_path.stat()
            hash_obj.update(str(stat.st_size).encode())
            hash_obj.update(str(stat.st_mtime).encode())

            return hash_obj.hexdigest()

        except Exception as e:
            logger.error("Failed to calculate hash for %s: %s", file_path, e)
            # Return a default hash based on file path as fallback
            return hashlib.sha256(str(file_path).encode()).hexdigest()

    def _should_process_file(self, file_path: Path) -> bool:
        """
        Check if a file should be processed for change detection.

        Args:
            file_path: Path to check

        Returns:
            True if file should be processed
        """
        try:
            # Check if file type is supported
            if not self.config.is_file_supported(file_path):
                return False

            # Check if file should be ignored
            if self.config.should_ignore_file(file_path):
                return False

            return True

        except Exception as e:
            logger.debug("Error checking if file should be processed %s: %s", file_path, e)
            return False

    def update_file_index(self, file_path: Path, content_hash: str, modified_time: datetime) -> None:
        """
        Update the internal file index with new file information.

        Args:
            file_path: Path to file
            content_hash: Content hash of file
            modified_time: File modification time
        """
        file_key = str(file_path)
        self._file_index[file_key] = {
            'hash': content_hash,
            'modified_time': modified_time,
            'last_checked': datetime.now(UTC),
        }

    def remove_from_index(self, file_path: Path) -> None:
        """
        Remove a file from the internal index.

        Args:
            file_path: Path to file to remove
        """
        file_key = str(file_path)
        if file_key in self._file_index:
            del self._file_index[file_key]

    def get_index_stats(self) -> dict[str, int]:
        """
        Get statistics about the file index.

        Returns:
            Dictionary with index statistics
        """
        return {
            'indexed_files': len(self._file_index),
            'total_size': sum(
                len(info['hash']) + len(str(info['modified_time'])) for info in self._file_index.values()
            ),
        }
