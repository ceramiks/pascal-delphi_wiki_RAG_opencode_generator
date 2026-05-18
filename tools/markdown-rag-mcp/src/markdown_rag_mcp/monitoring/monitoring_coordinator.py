"""
Monitoring coordinator for automatic index updates.

Coordinates between file watching, change detection, and incremental indexing
to provide automatic document index updates when files are modified.
"""

import logging
from pathlib import Path
from typing import Any

from markdown_rag_mcp.core import IIncrementalIndexer
from markdown_rag_mcp.models import MonitoringError
from markdown_rag_mcp.monitoring.file_watcher import MarkdownFileWatcher

logger = logging.getLogger(__name__)


class MonitoringCoordinator:
    """
    Coordinates automatic monitoring and incremental updates.

    Integrates file watching with incremental indexing to provide
    seamless automatic updates when documents are modified.
    """

    def __init__(
        self,
        config,
        incremental_indexer: IIncrementalIndexer,
        file_watcher: MarkdownFileWatcher | None = None,
    ):
        """
        Initialize the monitoring coordinator.

        Args:
            config: RAG configuration
            incremental_indexer: Incremental indexer for processing changes
            file_watcher: Optional file watcher (will create if not provided)
        """
        self.config = config
        self.incremental_indexer = incremental_indexer

        # Initialize file watcher with callbacks
        self.file_watcher = file_watcher or MarkdownFileWatcher(
            config=config,
            on_file_created=self._handle_file_created,
            on_file_modified=self._handle_file_modified,
            on_file_deleted=self._handle_file_deleted,
            debounce_seconds=config.monitoring_debounce_seconds,
        )

        # Monitoring state
        self._monitoring_active = False
        self._monitored_directories: list[Path] = []

        # Statistics tracking
        self._stats = {
            "files_processed": 0,
            "operations": {"created": 0, "modified": 0, "deleted": 0, "failed": 0},
            "errors": [],
        }

    async def start_monitoring(
        self,
        directory_path: Path,
        recursive: bool = True,
        initial_scan: bool = True,
    ) -> None:
        """
        Start monitoring a directory for changes.

        Args:
            directory_path: Directory to monitor
            recursive: Whether to monitor subdirectories
            initial_scan: Whether to perform initial scan for changes

        Raises:
            MonitoringError: If monitoring cannot be started
        """
        try:
            if not self.config.monitoring_enabled:
                raise MonitoringError(
                    "File monitoring is disabled in configuration",
                    path=str(directory_path),
                    operation="start_monitoring",
                )

            logger.info(
                "Starting monitoring for directory: %s (recursive: %s, initial_scan: %s)",
                directory_path,
                recursive,
                initial_scan,
            )

            # Perform initial scan if requested
            if initial_scan:
                logger.info("Performing initial directory scan...")
                scan_result = await self.incremental_indexer.update_index_for_directory(directory_path, recursive)
                logger.info("Initial scan complete: %d changes processed", scan_result.get("changes_detected", 0))

            # Start file watching
            self.file_watcher.start_watching(directory_path, recursive)

            # Track monitored directory
            if directory_path not in self._monitored_directories:
                self._monitored_directories.append(directory_path)

            self._monitoring_active = True
            logger.info("Monitoring started successfully for: %s", directory_path)

        except Exception as e:
            logger.error("Failed to start monitoring for %s: %s", directory_path, e)
            raise MonitoringError(
                f"Failed to start monitoring: {e}",
                path=str(directory_path),
                operation="start_monitoring",
                underlying_error=e,
            ) from e

    def stop_monitoring(self) -> None:
        """Stop all file monitoring."""
        try:
            if not self._monitoring_active:
                logger.debug("Monitoring not active, nothing to stop")
                return

            logger.info("Stopping file monitoring...")

            # Stop file watcher
            self.file_watcher.stop_watching()

            # Clear monitoring state
            self._monitoring_active = False
            self._monitored_directories.clear()

            logger.info("File monitoring stopped successfully")

        except Exception as e:
            logger.error("Error stopping monitoring: %s", e)
            raise MonitoringError("Failed to stop monitoring", operation="stop_monitoring", underlying_error=e) from e

    async def _handle_file_created(self, file_path: Path) -> None:
        """
        Handle file creation events.

        Args:
            file_path: Path to created file
        """
        try:
            logger.info("Processing file creation: %s", file_path)

            result = await self.incremental_indexer.update_single_file(file_path, operation='created')

            self._update_stats('created', result)

            if result["status"] == "success":
                logger.info("Successfully indexed new file: %s", file_path)
            else:
                logger.error("Failed to index new file %s: %s", file_path, result.get('error'))

        except Exception as e:
            self._update_stats('created', {"status": "failed", "error": str(e)})
            logger.error("Error handling file creation for %s: %s", file_path, e)

    async def _handle_file_modified(self, file_path: Path) -> None:
        """
        Handle file modification events.

        Args:
            file_path: Path to modified file
        """
        try:
            logger.info("Processing file modification: %s", file_path)

            result = await self.incremental_indexer.update_single_file(file_path, operation='modified')

            self._update_stats('modified', result)

            if result["status"] == "success":
                logger.info("Successfully updated modified file: %s", file_path)
            else:
                logger.error("Failed to update modified file %s: %s", file_path, result.get('error'))

        except Exception as e:
            self._update_stats('modified', {"status": "failed", "error": str(e)})
            logger.error("Error handling file modification for %s: %s", file_path, e)

    async def _handle_file_deleted(self, file_path: Path) -> None:
        """
        Handle file deletion events.

        Args:
            file_path: Path to deleted file
        """
        try:
            logger.info("Processing file deletion: %s", file_path)

            result = await self.incremental_indexer.update_single_file(file_path, operation='deleted')

            self._update_stats('deleted', result)

            if result["status"] == "success":
                logger.info("Successfully removed deleted file from index: %s", file_path)
            else:
                logger.error("Failed to remove deleted file %s: %s", file_path, result.get('error'))

        except Exception as e:
            self._update_stats('deleted', {"status": "failed", "error": str(e)})
            logger.error("Error handling file deletion for %s: %s", file_path, e)

    def _update_stats(self, operation: str, result: dict[str, Any]) -> None:
        """
        Update monitoring statistics.

        Args:
            operation: Type of operation performed
            result: Result of the operation
        """
        if result["status"] == "success":
            self._stats["files_processed"] += 1
            self._stats["operations"][operation] += 1
        else:
            self._stats["operations"]["failed"] += 1
            error_msg = f"{result.get('file_path', 'unknown')} ({operation}): {result.get('error', 'Unknown error')}"
            self._stats["errors"].append(error_msg)

            # Keep only the last 100 errors
            if len(self._stats["errors"]) > 100:
                self._stats["errors"] = self._stats["errors"][-100:]

    async def perform_manual_scan(self, directory_path: Path | None = None, recursive: bool = True) -> dict[str, Any]:
        """
        Perform a manual scan for changes.

        Args:
            directory_path: Directory to scan (uses monitored directories if None)
            recursive: Whether to scan recursively

        Returns:
            Dictionary with scan results

        Raises:
            MonitoringError: If scan fails
        """
        try:
            scan_directories = []

            if directory_path:
                scan_directories = [directory_path]
            elif self._monitored_directories:
                scan_directories = self._monitored_directories.copy()
            else:
                raise MonitoringError(
                    "No directory specified and no directories being monitored", operation="manual_scan"
                )

            logger.info("Performing manual scan of %d directories", len(scan_directories))

            results = []
            for dir_path in scan_directories:
                result = await self.incremental_indexer.update_index_for_directory(dir_path, recursive)
                results.append(result)

            # Aggregate results
            total_changes = sum(r.get("changes_detected", 0) for r in results)
            total_processed = sum(r.get("files_processed", 0) for r in results)

            aggregate_result = {
                "status": "success",
                "directories_scanned": len(scan_directories),
                "total_changes_detected": total_changes,
                "total_files_processed": total_processed,
                "directory_results": results,
            }

            logger.info("Manual scan complete: %d changes detected, %d files processed", total_changes, total_processed)

            return aggregate_result

        except Exception as e:
            logger.error("Manual scan failed: %s", e)
            raise MonitoringError(
                f"Manual scan failed: {e}",
                path=str(directory_path) if directory_path else "multiple",
                operation="manual_scan",
                underlying_error=e,
            ) from e

    @property
    def is_monitoring(self) -> bool:
        """Check if currently monitoring for changes."""
        return self._monitoring_active

    def get_monitored_directories(self) -> list[str]:
        """Get list of currently monitored directories."""
        return [str(path) for path in self._monitored_directories]

    def get_monitoring_stats(self) -> dict[str, Any]:
        """
        Get monitoring statistics.

        Returns:
            Dictionary with monitoring statistics
        """
        return {
            "monitoring_active": self._monitoring_active,
            "monitored_directories": self.get_monitored_directories(),
            "file_watcher_status": {
                "is_watching": self.file_watcher.is_watching,
                "watched_paths": self.file_watcher.get_watched_paths(),
                "pending_events": self.file_watcher.get_pending_events_count(),
            },
            "processing_stats": self._stats.copy(),
            "configuration": {
                "monitoring_enabled": self.config.monitoring_enabled,
                "debounce_seconds": self.config.monitoring_debounce_seconds,
                "max_concurrent_indexing": self.config.max_concurrent_indexing,
            },
        }
