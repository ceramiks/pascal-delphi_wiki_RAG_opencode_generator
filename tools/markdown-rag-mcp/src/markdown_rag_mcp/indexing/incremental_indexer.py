"""
Incremental indexer for selective document updates.

Handles incremental updates to the document index by processing only
changed files and maintaining consistency between the file system
and vector database.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from markdown_rag_mcp.core import (
    IChangeDetector,
    IDocumentIndexer,
    IIncrementalIndexer,
)
from markdown_rag_mcp.indexing.change_detector import DocumentChangeDetector, FileChangeInfo
from markdown_rag_mcp.indexing.indexer import DocumentIndexer
from markdown_rag_mcp.models import IndexingError

logger = logging.getLogger(__name__)


class IncrementalIndexer(IIncrementalIndexer):
    """
    Manages incremental updates to the document index.

    Coordinates between change detection, document indexing, and vector storage
    to ensure the index stays synchronized with file system changes.
    """

    def __init__(
        self,
        config,
        document_indexer: IDocumentIndexer | None = None,
        change_detector: IChangeDetector | None = None,
    ):
        """
        Initialize the incremental indexer.

        Args:
            config: RAG configuration
            document_indexer: Document indexer for processing files
            change_detector: Change detector for identifying modifications
        """
        self.config = config
        self.document_indexer = document_indexer or DocumentIndexer(config)
        self.change_detector = change_detector or DocumentChangeDetector(config)

    async def update_index_for_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
        force_full_scan: bool = False,
    ) -> dict[str, Any]:
        """
        Update the index for all changes in a directory.

        Args:
            directory_path: Directory to scan and update
            recursive: Whether to scan subdirectories
            force_full_scan: Whether to force full reindexing

        Returns:
            Dictionary with update results and statistics

        Raises:
            IndexingError: If update process fails
        """
        try:
            logger.info(
                "Starting incremental index update for directory: %s (force_full: %s)", directory_path, force_full_scan
            )

            if not directory_path.exists():
                raise IndexingError(
                    f"Directory does not exist: {directory_path}",
                    file_path=str(directory_path),
                    stage="directory_validation",
                )

            # Detect file changes
            changes = await self.change_detector.scan_directory_for_changes(directory_path, recursive)

            if not changes and not force_full_scan:
                logger.info("No changes detected in directory")
                return {
                    "status": "success",
                    "directory": str(directory_path),
                    "changes_detected": 0,
                    "files_processed": 0,
                    "operations": [],
                }

            # Process changes
            results = await self._process_changes(changes, force_full_scan)

            logger.info(
                "Incremental update complete: %d changes processed, %d files updated",
                len(changes),
                results["files_processed"],
            )

            return {"status": "success", "directory": str(directory_path), "changes_detected": len(changes), **results}

        except Exception as e:
            logger.error("Incremental index update failed for %s: %s", directory_path, e)
            raise IndexingError(
                f"Incremental update failed: {e}",
                file_path=str(directory_path),
                stage="incremental_update",
                underlying_error=e,
            ) from e

    async def update_single_file(
        self, file_path: Path, operation: str | None = None  # 'create', 'update', 'delete', or None for auto-detect
    ) -> dict[str, Any]:
        """
        Update the index for a single file.

        Args:
            file_path: Path to file to update
            operation: Specific operation to perform, or None to auto-detect

        Returns:
            Dictionary with update results

        Raises:
            IndexingError: If update fails
        """
        try:
            logger.debug("Updating index for single file: %s (operation: %s)", file_path, operation)

            # Auto-detect operation if not specified
            if operation is None:
                if not file_path.exists():
                    operation = 'delete'
                else:
                    # Check if file has changed
                    change_info = await self.change_detector.check_file_changed(file_path)
                    if change_info:
                        operation = change_info.change_type
                    else:
                        operation = 'none'

            # Process the operation
            result = await self._process_single_file_operation(file_path, operation)

            logger.debug("File update complete: %s -> %s", file_path, result["status"])
            return result

        except Exception as e:
            logger.error("Failed to update file %s: %s", file_path, e)
            raise IndexingError(
                f"File update failed: {e}", file_path=str(file_path), stage="file_update", underlying_error=e
            ) from e

    async def _process_changes(self, changes: list[FileChangeInfo], force_full_scan: bool = False) -> dict[str, Any]:
        """
        Process a list of file changes.

        Args:
            changes: List of detected file changes
            force_full_scan: Whether this is part of a forced full scan

        Returns:
            Dictionary with processing results
        """
        results = {
            "files_processed": 0,
            "operations": {"created": 0, "updated": 0, "deleted": 0, "failed": 0},
            "errors": [],
        }

        # Group changes by operation type for better logging
        changes_by_type = {}
        for change in changes:
            if change.change_type not in changes_by_type:
                changes_by_type[change.change_type] = []
            changes_by_type[change.change_type].append(change)

        # Process each type of change
        for change_type, type_changes in changes_by_type.items():
            logger.info("Processing %d %s operations", len(type_changes), change_type)

            for change in type_changes:
                try:
                    result = await self._process_file_change(change)

                    if result["status"] == "success":
                        results["files_processed"] += 1
                        results["operations"][change_type] += 1
                    else:
                        results["operations"]["failed"] += 1
                        results["errors"].append(f"{change.file_path}: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    results["operations"]["failed"] += 1
                    error_msg = f"{change.file_path}: {e}"
                    results["errors"].append(error_msg)
                    logger.error("Failed to process change for %s: %s", change.file_path, e)

        return results

    async def _process_file_change(self, change: FileChangeInfo) -> dict[str, Any]:
        """
        Process a single file change.

        Args:
            change: File change information

        Returns:
            Dictionary with processing result
        """
        return await self._process_single_file_operation(change.file_path, change.change_type)

    async def _process_single_file_operation(self, file_path: Path, operation: str) -> dict[str, Any]:
        """
        Process a single file operation.

        Args:
            file_path: Path to file
            operation: Operation type ('created', 'modified', 'deleted', 'none')

        Returns:
            Dictionary with operation result
        """
        try:
            if operation == 'none':
                return {
                    "status": "success",
                    "operation": "none",
                    "file_path": str(file_path),
                    "message": "No changes detected",
                }

            elif operation in ('created', 'modified'):
                # Index or reindex the file
                if operation == 'modified':
                    logger.debug("Updating existing document: %s", file_path)
                    result = await self.document_indexer.update_document(file_path)
                else:
                    logger.debug("Indexing new document: %s", file_path)
                    result = await self.document_indexer.index_document(file_path)

                # Update change detector with the actual hash and modification time from indexing
                if result["status"] in ("success", "skipped"):
                    # Get the actual hash and modification time from the indexer result
                    content_hash = result.get("content_hash")
                    modified_at = result.get("modified_at")

                    if content_hash and modified_at:
                        # Update the change detector's file index with the processed document info
                        self.change_detector.update_file_index(file_path, content_hash, modified_at)
                        logger.debug(
                            "Updated change detector state for %s: hash=%s, modified=%s",
                            file_path,
                            content_hash[:16] + "...",
                            modified_at,
                        )
                    else:
                        logger.warning("Indexer result missing hash or modification time for %s", file_path)

                return result

            elif operation == 'deleted':
                # Remove from index
                logger.debug("Removing deleted document: %s", file_path)
                result = await self.document_indexer.remove_document(file_path)

                # Update change detector index
                if result["status"] == "success":
                    self.change_detector.remove_from_index(file_path)

                return result

            else:
                raise ValueError(f"Unknown operation type: {operation}")

        except Exception as e:
            logger.error("Failed to process %s operation for %s: %s", operation, file_path, e)
            return {"status": "failed", "operation": operation, "file_path": str(file_path), "error": str(e)}

    async def batch_update_files(
        self,
        file_operations: list[tuple[Path, str]],  # List of (file_path, operation) tuples
        max_concurrent: int | None = None,
    ) -> dict[str, Any]:
        """
        Process multiple file operations concurrently.

        Args:
            file_operations: List of (file_path, operation) tuples
            max_concurrent: Maximum concurrent operations

        Returns:
            Dictionary with batch processing results
        """
        try:
            logger.info("Starting batch update of %d files", len(file_operations))

            max_concurrent = max_concurrent or self.config.max_concurrent_indexing

            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_semaphore(file_path, operation):
                async with semaphore:
                    return await self._process_single_file_operation(file_path, operation)

            # Process all operations
            results = await asyncio.gather(
                *[process_with_semaphore(file_path, op) for file_path, op in file_operations], return_exceptions=True
            )

            # Aggregate results
            success_count = 0
            failed_count = 0
            errors = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    file_path, operation = file_operations[i]
                    errors.append(f"{file_path} ({operation}): {result}")
                elif result.get("status") == "success":
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{result.get('file_path', 'unknown')}: {result.get('error', 'Unknown error')}")

            batch_result = {
                "status": "completed",
                "total_files": len(file_operations),
                "successful": success_count,
                "failed": failed_count,
                "errors": errors,
            }

            logger.info("Batch update complete: %d/%d successful", success_count, len(file_operations))

            return batch_result

        except Exception as e:
            logger.error("Batch update failed: %s", e)
            raise IndexingError(f"Batch update failed: {e}", stage="batch_update", underlying_error=e) from e

    def get_status(self) -> dict[str, Any]:
        """
        Get status information about the incremental indexer.

        Returns:
            Dictionary with status information
        """
        return {
            "change_detector_stats": self.change_detector.get_index_stats(),
            "config": {
                "max_concurrent_indexing": self.config.max_concurrent_indexing,
                "monitoring_enabled": self.config.monitoring_enabled,
                "debounce_seconds": self.config.monitoring_debounce_seconds,
            },
        }
