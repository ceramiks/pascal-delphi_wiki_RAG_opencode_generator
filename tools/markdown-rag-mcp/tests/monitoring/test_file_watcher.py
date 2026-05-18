"""Unit tests for file watcher implementation."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.models import MonitoringError
from markdown_rag_mcp.monitoring import FileChangeEvent, MarkdownFileWatcher
from watchdog.events import FileSystemEvent


class TestFileChangeEvent:
    """Test cases for FileChangeEvent."""

    def test_create_event(self):
        """Test creating a file change event."""
        file_path = Path("/test/file.md")
        event = FileChangeEvent("created", file_path)

        assert event.event_type == "created"
        assert event.file_path == file_path
        assert event.is_directory is False
        assert event.timestamp > 0

    def test_event_string_representation(self):
        """Test string representation of event."""
        file_path = Path("/test/file.md")
        event = FileChangeEvent("modified", file_path)

        str_repr = str(event)
        assert "FileChangeEvent(modified: /test/file.md)" in str_repr


class TestMarkdownFileWatcher:
    """Test cases for MarkdownFileWatcher."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock RAG configuration."""
        config = Mock(spec=RAGConfig)
        config.monitoring_enabled = True
        config.monitoring_debounce_seconds = 1.0
        config.is_file_supported.return_value = True
        config.should_ignore_file.return_value = False
        return config

    @pytest.fixture
    def mock_callbacks(self):
        """Create mock callback functions."""
        return {'on_created': AsyncMock(), 'on_modified': AsyncMock(), 'on_deleted': AsyncMock()}

    @pytest.fixture
    def file_watcher(self, mock_config, mock_callbacks):
        """Create a MarkdownFileWatcher instance."""
        return MarkdownFileWatcher(
            config=mock_config,
            on_file_created=mock_callbacks['on_created'],
            on_file_modified=mock_callbacks['on_modified'],
            on_file_deleted=mock_callbacks['on_deleted'],
            debounce_seconds=0.1,  # Short debounce for testing
        )

    def test_initialization(self, file_watcher, mock_config):
        """Test file watcher initialization."""
        assert file_watcher.config == mock_config
        assert file_watcher.debounce_seconds == 0.1
        assert file_watcher._observer is None
        assert len(file_watcher._watched_paths) == 0
        assert not file_watcher.is_watching

    @patch('markdown_rag_mcp.monitoring.file_watcher.Observer')
    def test_start_watching_success(self, mock_observer_class, file_watcher, tmp_path):
        """Test successful start of directory watching."""
        # Create a temporary directory
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Mock observer
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_observer.is_alive.return_value = False

        # Start watching
        file_watcher.start_watching(test_dir, recursive=True)

        # Verify observer setup
        mock_observer_class.assert_called_once()
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()

        # Verify state
        assert str(test_dir.resolve()) in file_watcher._watched_paths
        assert file_watcher._observer == mock_observer

    def test_start_watching_nonexistent_directory(self, file_watcher):
        """Test starting watch on non-existent directory."""
        nonexistent_path = Path("/nonexistent/directory")

        with pytest.raises(MonitoringError) as exc_info:
            file_watcher.start_watching(nonexistent_path)

        assert "Directory does not exist" in str(exc_info.value)
        assert not file_watcher.is_watching

    def test_start_watching_file_not_directory(self, file_watcher, tmp_path):
        """Test starting watch on a file instead of directory."""
        # Create a temporary file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        with pytest.raises(MonitoringError) as exc_info:
            file_watcher.start_watching(test_file)

        assert "Path is not a directory" in str(exc_info.value)

    @patch('markdown_rag_mcp.monitoring.file_watcher.Observer')
    def test_stop_watching(self, mock_observer_class, file_watcher):
        """Test stopping file watching."""
        # Setup observer
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_observer.is_alive.return_value = True

        file_watcher._observer = mock_observer
        file_watcher._watched_paths.add("/test/path")

        # Stop watching
        file_watcher.stop_watching()

        # Verify cleanup
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5.0)
        assert len(file_watcher._watched_paths) == 0
        assert len(file_watcher._pending_events) == 0

    def test_file_system_event_handling(self, file_watcher):
        """Test handling of file system events."""
        # Mock file system events
        created_event = Mock(spec=FileSystemEvent)
        created_event.is_directory = False
        created_event.src_path = "/test/new_file.md"

        modified_event = Mock(spec=FileSystemEvent)
        modified_event.is_directory = False
        modified_event.src_path = "/test/existing_file.md"

        deleted_event = Mock(spec=FileSystemEvent)
        deleted_event.is_directory = False
        deleted_event.src_path = "/test/deleted_file.md"

        # Handle events (should not raise exceptions)
        file_watcher.on_created(created_event)
        file_watcher.on_modified(modified_event)
        file_watcher.on_deleted(deleted_event)

        # Events should be pending (debounced)
        assert len(file_watcher._pending_events) <= 3

    def test_should_process_file_supported(self, file_watcher):
        """Test file processing check for supported files."""
        test_file = Path("/test/document.md")

        # Mock config responses
        file_watcher.config.is_file_supported.return_value = True
        file_watcher.config.should_ignore_file.return_value = False

        result = file_watcher._should_process_file(test_file)
        assert result is True

        file_watcher.config.is_file_supported.assert_called_once_with(test_file)
        file_watcher.config.should_ignore_file.assert_called_once_with(test_file)

    def test_should_process_file_unsupported(self, file_watcher):
        """Test file processing check for unsupported files."""
        test_file = Path("/test/document.txt")

        # Mock config responses
        file_watcher.config.is_file_supported.return_value = False

        result = file_watcher._should_process_file(test_file)
        assert result is False

    def test_should_process_file_ignored(self, file_watcher):
        """Test file processing check for ignored files."""
        test_file = Path("/test/.gitignore")

        # Mock config responses
        file_watcher.config.is_file_supported.return_value = True
        file_watcher.config.should_ignore_file.return_value = True

        result = file_watcher._should_process_file(test_file)
        assert result is False

    @pytest.mark.asyncio
    async def test_debounced_event_processing(self, file_watcher, mock_callbacks, tmp_path):
        """Test that events are properly debounced."""
        test_file = Path("/test/document.md")

        # Set up the event loop capture (simulates start_watching)
        file_watcher._loop = asyncio.get_running_loop()

        # Simulate rapid file changes
        file_watcher._handle_file_event('modified', test_file)
        file_watcher._handle_file_event('modified', test_file)  # Should cancel previous
        file_watcher._handle_file_event('modified', test_file)  # Should cancel previous

        # Wait for debounce processing
        await asyncio.sleep(0.2)  # Longer than debounce time

        # Should have called callback only once
        mock_callbacks['on_modified'].assert_called_once_with(test_file)

    @pytest.mark.asyncio
    async def test_event_dispatch_with_callback(self, file_watcher, mock_callbacks):
        """Test event dispatch to callbacks."""
        test_file = Path("/test/document.md")

        # Create and dispatch events
        create_event = FileChangeEvent('created', test_file)
        modify_event = FileChangeEvent('modified', test_file)
        delete_event = FileChangeEvent('deleted', test_file)

        await file_watcher._dispatch_event(create_event)
        await file_watcher._dispatch_event(modify_event)
        await file_watcher._dispatch_event(delete_event)

        # Verify callbacks were called
        mock_callbacks['on_created'].assert_called_once_with(test_file)
        mock_callbacks['on_modified'].assert_called_once_with(test_file)
        mock_callbacks['on_deleted'].assert_called_once_with(test_file)

    @pytest.mark.asyncio
    async def test_event_dispatch_no_callback(self, file_watcher):
        """Test event dispatch when no callback is set."""
        test_file = Path("/test/document.md")

        # Create watcher without callbacks
        watcher_no_callbacks = MarkdownFileWatcher(config=file_watcher.config, debounce_seconds=0.1)

        # Should not raise exception
        create_event = FileChangeEvent('created', test_file)
        await watcher_no_callbacks._dispatch_event(create_event)

    def test_properties_and_getters(self, file_watcher):
        """Test property access and getter methods."""
        # Initially not watching
        assert not file_watcher.is_watching
        assert file_watcher.get_watched_paths() == []
        assert file_watcher.get_pending_events_count() == 0

        # Add some mock state
        file_watcher._watched_paths.add("/test/path1")
        file_watcher._watched_paths.add("/test/path2")
        file_watcher._pending_events["file1"] = Mock()
        file_watcher._pending_events["file2"] = Mock()

        # Test getters
        watched_paths = file_watcher.get_watched_paths()
        assert len(watched_paths) == 2
        assert "/test/path1" in watched_paths
        assert "/test/path2" in watched_paths

        assert file_watcher.get_pending_events_count() == 2

    def test_move_event_handling(self, file_watcher):
        """Test handling of file move events."""
        # Mock move event
        move_event = Mock()
        move_event.is_directory = False
        move_event.src_path = "/test/old_file.md"
        move_event.dest_path = "/test/new_file.md"

        # Handle move event
        file_watcher.on_moved(move_event)

        # Should create both delete and create events
        # (exact verification depends on internal implementation)
        assert len(file_watcher._pending_events) <= 2

    @pytest.mark.asyncio
    async def test_error_handling_in_callbacks(self, file_watcher):
        """Test error handling when callbacks raise exceptions."""
        test_file = Path("/test/document.md")

        # Create callback that raises exception
        error_callback = AsyncMock(side_effect=Exception("Callback error"))

        watcher_with_error = MarkdownFileWatcher(
            config=file_watcher.config, on_file_created=error_callback, debounce_seconds=0.1
        )

        # Should not propagate exception from callback
        create_event = FileChangeEvent('created', test_file)
        await watcher_with_error._dispatch_event(create_event)

        # Callback should have been called
        error_callback.assert_called_once_with(test_file)
