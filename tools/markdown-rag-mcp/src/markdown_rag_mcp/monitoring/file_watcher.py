"""
File system watcher for detecting changes in markdown document collections.

Monitors directory trees for file additions, modifications, and deletions,
triggering appropriate index update operations automatically.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from markdown_rag_mcp.models import MonitoringError

logger = logging.getLogger(__name__)


class FileChangeEvent:
    """Represents a file system change event."""

    def __init__(self, event_type: str, file_path: Path, is_directory: bool = False):
        self.event_type = event_type  # 'created', 'modified', 'deleted', 'moved'
        self.file_path = file_path
        self.is_directory = is_directory
        self.timestamp = time.time()

    def __str__(self) -> str:
        return f"FileChangeEvent({self.event_type}: {self.file_path})"


class MarkdownFileWatcher(FileSystemEventHandler):
    """
    File system watcher specifically for markdown files.

    Monitors specified directories for changes to supported file types
    and triggers appropriate callback functions for index updates.
    """

    def __init__(
        self,
        config,
        on_file_created: Callable[[Path], asyncio.Task] | None = None,
        on_file_modified: Callable[[Path], asyncio.Task] | None = None,
        on_file_deleted: Callable[[Path], asyncio.Task] | None = None,
        debounce_seconds: float = 2.0,
    ):
        """
        Initialize the file watcher.

        Args:
            config: RAG configuration with file support settings
            on_file_created: Callback for file creation events
            on_file_modified: Callback for file modification events
            on_file_deleted: Callback for file deletion events
            debounce_seconds: Debounce time to prevent duplicate events
        """
        super().__init__()
        self.config = config
        self.on_file_created = on_file_created
        self.on_file_modified = on_file_modified
        self.on_file_deleted = on_file_deleted
        self.debounce_seconds = debounce_seconds

        # Event tracking for debouncing
        self._pending_events: dict[str, FileChangeEvent] = {}
        self._debounce_tasks: dict[str, asyncio.Future] = {}

        # Observer for watchdog
        self._observer: Observer | None = None
        self._watched_paths: set[str] = set()

        # Store reference to the main event loop for cross-thread scheduling
        self._loop: asyncio.AbstractEventLoop | None = None

    def start_watching(self, directory_path: Path, recursive: bool = True) -> None:
        """
        Start watching a directory for file changes.

        Args:
            directory_path: Path to directory to monitor
            recursive: Whether to monitor subdirectories

        Raises:
            MonitoringError: If monitoring cannot be started
        """
        try:
            if not directory_path.exists():
                raise MonitoringError(
                    f"Directory does not exist: {directory_path}", path=str(directory_path), operation="start_watching"
                )

            if not directory_path.is_dir():
                raise MonitoringError(
                    f"Path is not a directory: {directory_path}", path=str(directory_path), operation="start_watching"
                )

            # Capture the current event loop for cross-thread task scheduling
            try:
                self._loop = asyncio.get_running_loop()
                logger.debug("Captured event loop for cross-thread task scheduling")
            except RuntimeError:
                logger.warning("No running event loop found - file events may not be processed")

            # Initialize observer if needed
            if self._observer is None:
                self._observer = Observer()

            # Add path to monitoring
            directory_str = str(directory_path.resolve())
            if directory_str not in self._watched_paths:
                self._observer.schedule(self, directory_str, recursive=recursive)
                self._watched_paths.add(directory_str)
                logger.info("Started monitoring %s (recursive: %s)", directory_path, recursive)

            # Start observer if not already running
            if not self._observer.is_alive():
                self._observer.start()
                logger.info("File monitoring observer started")

        except Exception as e:
            logger.error("Failed to start file monitoring: %s", e)
            raise MonitoringError(
                f"Failed to start monitoring: {e}",
                path=str(directory_path),
                operation="start_watching",
                underlying_error=e,
            ) from e

    def stop_watching(self) -> None:
        """Stop all file monitoring."""
        try:
            if self._observer and self._observer.is_alive():
                self._observer.stop()
                self._observer.join(timeout=5.0)
                logger.info("File monitoring stopped")

            # Cancel pending debounce tasks gracefully
            for future in self._debounce_tasks.values():
                if not future.done():
                    future.cancel()

            self._debounce_tasks.clear()
            self._pending_events.clear()
            self._watched_paths.clear()

        except Exception as e:
            logger.error("Error stopping file monitoring: %s", e)
            raise MonitoringError("Failed to stop monitoring", operation="stop_watching", underlying_error=e) from e

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file/directory creation events."""
        if not event.is_directory:
            self._handle_file_event('created', Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file/directory modification events."""
        if not event.is_directory:
            self._handle_file_event('modified', Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file/directory deletion events."""
        if not event.is_directory:
            self._handle_file_event('deleted', Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file/directory move events."""
        if hasattr(event, 'dest_path') and not event.is_directory:
            # Treat moves as delete + create
            self._handle_file_event('deleted', Path(event.src_path))
            self._handle_file_event('created', Path(event.dest_path))

    def _handle_file_event(self, event_type: str, file_path: Path) -> None:
        """
        Handle a file system event with debouncing.

        Args:
            event_type: Type of event ('created', 'modified', 'deleted')
            file_path: Path to the affected file
        """
        try:
            # Check if file is supported
            if not self._should_process_file(file_path):
                return

            logger.debug("File event: %s %s", event_type, file_path)

            # Create event object
            change_event = FileChangeEvent(event_type, file_path)

            # Use file path as key for debouncing
            file_key = str(file_path)

            # Cancel existing debounce task for this file
            if file_key in self._debounce_tasks:
                existing_task = self._debounce_tasks[file_key]
                if not existing_task.done():
                    existing_task.cancel()
                del self._debounce_tasks[file_key]

            # Store the event, but prioritize 'created' over 'modified' for the same file
            should_update_event = True
            if file_key in self._pending_events:
                existing_event = self._pending_events[file_key]
                # If we have a 'created' event and this is a 'modified' event, keep the 'created'
                if existing_event.event_type == 'created' and event_type == 'modified':
                    should_update_event = False
                    logger.debug("Keeping 'created' event over 'modified' for %s", file_key)

            if should_update_event:
                self._pending_events[file_key] = change_event
                logger.debug("Stored %s event for %s", event_type, file_key)
            else:
                logger.debug("Skipped updating event (keeping higher priority event) for %s", file_key)

            # Schedule debounced processing
            if self._loop and not self._loop.is_closed():
                try:
                    # Use run_coroutine_threadsafe to schedule from watchdog thread to main thread
                    future = asyncio.run_coroutine_threadsafe(self._process_debounced_event(file_key), self._loop)
                    # Convert Future to Task for consistent interface
                    # Note: we store the Future, not a Task, but it has similar interface
                    self._debounce_tasks[file_key] = future
                    logger.debug("Scheduled debounce processing for %s via run_coroutine_threadsafe", file_key)
                except Exception as e:
                    logger.error("Failed to schedule debounce task for %s: %s", file_key, e)
            else:
                logger.error("No event loop available for scheduling debounce task for %s", file_key)

        except Exception as e:
            logger.error("Error handling file event %s for %s: %s", event_type, file_path, e)

    async def _process_debounced_event(self, file_key: str) -> None:
        """
        Process a file event after debounce delay.

        Args:
            file_key: File path key for the pending event
        """
        try:
            logger.debug("Starting debounced processing for %s (waiting %s seconds)", file_key, self.debounce_seconds)
            # Wait for debounce period
            await asyncio.sleep(self.debounce_seconds)

            logger.debug("Debounce completed for %s, processing event", file_key)

            # Get the pending event
            if file_key not in self._pending_events:
                logger.debug("No pending event found for %s", file_key)
                return

            event = self._pending_events.pop(file_key)
            logger.debug("Retrieved event for %s: %s", file_key, event.event_type)

            # Remove task from tracking
            if file_key in self._debounce_tasks:
                del self._debounce_tasks[file_key]

            # Process the event
            logger.debug("Dispatching event for %s", file_key)
            await self._dispatch_event(event)
            logger.debug("Event dispatched successfully for %s", file_key)

        except asyncio.CancelledError:
            # Task was cancelled due to newer event
            logger.debug("Debounced event cancelled for %s", file_key)
            raise  # Re-raise CancelledError
        except Exception as e:
            logger.error("Error processing debounced event for %s: %s", file_key, e)

    async def _dispatch_event(self, event: FileChangeEvent) -> None:
        """
        Dispatch an event to the appropriate callback.

        Args:
            event: File change event to process
        """
        try:
            callback = None

            if event.event_type == 'created' and self.on_file_created:
                callback = self.on_file_created
            elif event.event_type == 'modified' and self.on_file_modified:
                callback = self.on_file_modified
            elif event.event_type == 'deleted' and self.on_file_deleted:
                callback = self.on_file_deleted

            if callback:
                logger.info("Processing %s event for %s", event.event_type, event.file_path)
                # Call the callback (which may be sync or async)
                result = callback(event.file_path)
                if asyncio.iscoroutine(result):
                    await result
                elif hasattr(result, '__await__'):
                    # If callback returns a task or awaitable, await it
                    await result

        except Exception as e:
            logger.error("Error dispatching %s event for %s: %s", event.event_type, event.file_path, e)

    def _should_process_file(self, file_path: Path) -> bool:
        """
        Check if a file should be processed based on configuration.

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

    @property
    def is_watching(self) -> bool:
        """Check if currently watching for file changes."""
        return self._observer is not None and self._observer.is_alive()

    def get_watched_paths(self) -> list[str]:
        """Get list of currently watched directory paths."""
        return list(self._watched_paths)

    def get_pending_events_count(self) -> int:
        """Get count of pending debounced events."""
        return len(self._pending_events)
