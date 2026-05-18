"""Unit tests for monitoring coordinator implementation."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.core import IIncrementalIndexer
from markdown_rag_mcp.models import MonitoringError
from markdown_rag_mcp.monitoring import MarkdownFileWatcher, MonitoringCoordinator


class TestMonitoringCoordinator:
    """Test cases for MonitoringCoordinator."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock RAG configuration."""
        config = Mock(spec=RAGConfig)
        config.monitoring_enabled = True
        config.monitoring_debounce_seconds = 1.0
        config.max_concurrent_indexing = 3
        return config

    @pytest.fixture
    def mock_incremental_indexer(self):
        """Create a mock incremental indexer."""
        indexer = Mock(spec=IIncrementalIndexer)
        indexer.update_index_for_directory = AsyncMock()
        indexer.update_single_file = AsyncMock()
        return indexer

    @pytest.fixture
    def mock_file_watcher(self):
        """Create a mock file watcher."""
        watcher = Mock(spec=MarkdownFileWatcher)
        watcher.start_watching = Mock()
        watcher.stop_watching = Mock()
        watcher.is_watching = False
        watcher.get_watched_paths = Mock(return_value=[])
        watcher.get_pending_events_count = Mock(return_value=0)
        return watcher

    @pytest.fixture
    def coordinator_with_mock_watcher(self, mock_config, mock_incremental_indexer, mock_file_watcher):
        """Create a MonitoringCoordinator with mock file watcher."""
        return MonitoringCoordinator(
            config=mock_config,
            incremental_indexer=mock_incremental_indexer,
            file_watcher=mock_file_watcher,
        )

    @pytest.fixture
    def coordinator(self, mock_config, mock_incremental_indexer):
        """Create a MonitoringCoordinator instance."""
        with patch('markdown_rag_mcp.monitoring.monitoring_coordinator.MarkdownFileWatcher'):
            return MonitoringCoordinator(
                config=mock_config,
                incremental_indexer=mock_incremental_indexer,
            )

    def test_initialization(self, coordinator, mock_config, mock_incremental_indexer):
        """Test coordinator initialization."""
        assert coordinator.config == mock_config
        assert coordinator.incremental_indexer == mock_incremental_indexer
        assert not coordinator.is_monitoring
        assert coordinator.get_monitored_directories() == []

    def test_initialization_with_existing_watcher(self, coordinator_with_mock_watcher, mock_file_watcher):
        """Test initialization with existing file watcher."""
        assert coordinator_with_mock_watcher.file_watcher == mock_file_watcher

    @pytest.mark.asyncio
    async def test_start_monitoring_success(self, coordinator_with_mock_watcher, tmp_path):
        """Test successful start of monitoring."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Mock successful indexer response
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.return_value = {
            "changes_detected": 5
        }

        await coordinator_with_mock_watcher.start_monitoring(test_dir, recursive=True, initial_scan=True)

        # Verify initial scan was performed
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.assert_called_once_with(
            test_dir, True
        )

        # Verify file watcher was started
        coordinator_with_mock_watcher.file_watcher.start_watching.assert_called_once_with(test_dir, True)

        # Verify state
        assert coordinator_with_mock_watcher.is_monitoring
        assert str(test_dir) in coordinator_with_mock_watcher.get_monitored_directories()

    @pytest.mark.asyncio
    async def test_start_monitoring_no_initial_scan(self, coordinator_with_mock_watcher, tmp_path):
        """Test starting monitoring without initial scan."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        await coordinator_with_mock_watcher.start_monitoring(test_dir, recursive=False, initial_scan=False)

        # Verify no initial scan was performed
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.assert_not_called()

        # Verify file watcher was started
        coordinator_with_mock_watcher.file_watcher.start_watching.assert_called_once_with(test_dir, False)

    @pytest.mark.asyncio
    async def test_start_monitoring_disabled(self, coordinator_with_mock_watcher, tmp_path):
        """Test starting monitoring when disabled in config."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        coordinator_with_mock_watcher.config.monitoring_enabled = False

        with pytest.raises(MonitoringError) as exc_info:
            await coordinator_with_mock_watcher.start_monitoring(test_dir)

        assert "File monitoring is disabled" in str(exc_info.value)
        assert not coordinator_with_mock_watcher.is_monitoring

    @pytest.mark.asyncio
    async def test_start_monitoring_initial_scan_failure(self, coordinator_with_mock_watcher, tmp_path):
        """Test handling of initial scan failure."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Mock indexer failure
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.side_effect = Exception(
            "Indexing failed"
        )

        with pytest.raises(MonitoringError) as exc_info:
            await coordinator_with_mock_watcher.start_monitoring(test_dir, initial_scan=True)

        assert "Failed to start monitoring" in str(exc_info.value)
        assert not coordinator_with_mock_watcher.is_monitoring

    def test_stop_monitoring(self, coordinator_with_mock_watcher, tmp_path):
        """Test stopping monitoring."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Set up monitoring state
        coordinator_with_mock_watcher._monitoring_active = True
        coordinator_with_mock_watcher._monitored_directories.append(test_dir)

        coordinator_with_mock_watcher.stop_monitoring()

        # Verify file watcher was stopped
        coordinator_with_mock_watcher.file_watcher.stop_watching.assert_called_once()

        # Verify state cleanup
        assert not coordinator_with_mock_watcher.is_monitoring
        assert coordinator_with_mock_watcher.get_monitored_directories() == []

    def test_stop_monitoring_not_active(self, coordinator_with_mock_watcher):
        """Test stopping monitoring when not active."""
        coordinator_with_mock_watcher._monitoring_active = False

        coordinator_with_mock_watcher.stop_monitoring()

        # Should not raise exception and watcher should NOT be called (early return)
        coordinator_with_mock_watcher.file_watcher.stop_watching.assert_not_called()

    def test_stop_monitoring_error(self, coordinator_with_mock_watcher):
        """Test error handling in stop monitoring."""
        coordinator_with_mock_watcher._monitoring_active = True
        coordinator_with_mock_watcher.file_watcher.stop_watching.side_effect = Exception("Stop failed")

        with pytest.raises(MonitoringError) as exc_info:
            coordinator_with_mock_watcher.stop_monitoring()

        assert "Failed to stop monitoring" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_file_created(self, coordinator_with_mock_watcher):
        """Test handling of file creation events."""
        test_file = Path("/test/new_file.md")

        # Mock successful indexing result
        coordinator_with_mock_watcher.incremental_indexer.update_single_file.return_value = {
            "status": "success",
            "operation": "created",
        }

        await coordinator_with_mock_watcher._handle_file_created(test_file)

        # Verify indexer was called
        coordinator_with_mock_watcher.incremental_indexer.update_single_file.assert_called_once_with(
            test_file, operation='created'
        )

        # Verify stats were updated
        assert coordinator_with_mock_watcher._stats["operations"]["created"] == 1
        assert coordinator_with_mock_watcher._stats["files_processed"] == 1

    @pytest.mark.asyncio
    async def test_handle_file_created_failure(self, coordinator_with_mock_watcher):
        """Test handling of file creation failure."""
        test_file = Path("/test/new_file.md")

        # Mock failed indexing result
        coordinator_with_mock_watcher.incremental_indexer.update_single_file.return_value = {
            "status": "failed",
            "error": "Indexing error",
            "file_path": str(test_file),
        }

        await coordinator_with_mock_watcher._handle_file_created(test_file)

        # Verify stats were updated for failure
        assert coordinator_with_mock_watcher._stats["operations"]["failed"] == 1
        assert coordinator_with_mock_watcher._stats["files_processed"] == 0
        assert len(coordinator_with_mock_watcher._stats["errors"]) == 1

    @pytest.mark.asyncio
    async def test_handle_file_created_exception(self, coordinator_with_mock_watcher):
        """Test handling of exception during file creation."""
        test_file = Path("/test/new_file.md")

        # Mock indexer exception
        coordinator_with_mock_watcher.incremental_indexer.update_single_file.side_effect = Exception("Unexpected error")

        # Should not raise exception
        await coordinator_with_mock_watcher._handle_file_created(test_file)

        # Verify stats were updated for failure
        assert coordinator_with_mock_watcher._stats["operations"]["failed"] == 1

    @pytest.mark.asyncio
    async def test_handle_file_modified(self, coordinator_with_mock_watcher):
        """Test handling of file modification events."""
        test_file = Path("/test/existing_file.md")

        coordinator_with_mock_watcher.incremental_indexer.update_single_file.return_value = {
            "status": "success",
            "operation": "modified",
        }

        await coordinator_with_mock_watcher._handle_file_modified(test_file)

        coordinator_with_mock_watcher.incremental_indexer.update_single_file.assert_called_once_with(
            test_file, operation='modified'
        )

        assert coordinator_with_mock_watcher._stats["operations"]["modified"] == 1

    @pytest.mark.asyncio
    async def test_handle_file_deleted(self, coordinator_with_mock_watcher):
        """Test handling of file deletion events."""
        test_file = Path("/test/deleted_file.md")

        coordinator_with_mock_watcher.incremental_indexer.update_single_file.return_value = {
            "status": "success",
            "operation": "deleted",
        }

        await coordinator_with_mock_watcher._handle_file_deleted(test_file)

        coordinator_with_mock_watcher.incremental_indexer.update_single_file.assert_called_once_with(
            test_file, operation='deleted'
        )

        assert coordinator_with_mock_watcher._stats["operations"]["deleted"] == 1

    def test_update_stats_success(self, coordinator_with_mock_watcher):
        """Test statistics update for successful operations."""
        result = {"status": "success", "operation": "created"}

        coordinator_with_mock_watcher._update_stats("created", result)

        assert coordinator_with_mock_watcher._stats["files_processed"] == 1
        assert coordinator_with_mock_watcher._stats["operations"]["created"] == 1

    def test_update_stats_failure(self, coordinator_with_mock_watcher):
        """Test statistics update for failed operations."""
        result = {"status": "failed", "error": "Processing error", "file_path": "/test/file.md"}

        coordinator_with_mock_watcher._update_stats("created", result)

        assert coordinator_with_mock_watcher._stats["files_processed"] == 0
        assert coordinator_with_mock_watcher._stats["operations"]["failed"] == 1
        assert len(coordinator_with_mock_watcher._stats["errors"]) == 1
        assert "/test/file.md (created): Processing error" in coordinator_with_mock_watcher._stats["errors"]

    def test_update_stats_error_limit(self, coordinator_with_mock_watcher):
        """Test that error list is limited to 100 entries."""
        # Add 150 errors
        for i in range(150):
            result = {"status": "failed", "error": f"Error {i}", "file_path": f"/test/file{i}.md"}
            coordinator_with_mock_watcher._update_stats("created", result)

        # Should only keep the last 100 errors
        assert len(coordinator_with_mock_watcher._stats["errors"]) == 100
        assert "Error 149" in coordinator_with_mock_watcher._stats["errors"][-1]
        assert "Error 50" in coordinator_with_mock_watcher._stats["errors"][0]

    @pytest.mark.asyncio
    async def test_perform_manual_scan_with_directory(self, coordinator_with_mock_watcher, tmp_path):
        """Test manual scan with specified directory."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Mock indexer response
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.return_value = {
            "changes_detected": 3,
            "files_processed": 5,
        }

        result = await coordinator_with_mock_watcher.perform_manual_scan(test_dir, recursive=True)

        # Verify indexer was called
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.assert_called_once_with(
            test_dir, True
        )

        # Verify result
        assert result["status"] == "success"
        assert result["directories_scanned"] == 1
        assert result["total_changes_detected"] == 3
        assert result["total_files_processed"] == 5

    @pytest.mark.asyncio
    async def test_perform_manual_scan_monitored_directories(self, coordinator_with_mock_watcher, tmp_path):
        """Test manual scan using monitored directories."""
        test_dir1 = tmp_path / "dir1"
        test_dir2 = tmp_path / "dir2"
        test_dir1.mkdir()
        test_dir2.mkdir()

        # Set up monitored directories
        coordinator_with_mock_watcher._monitored_directories = [test_dir1, test_dir2]

        # Mock indexer responses
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.side_effect = [
            {"changes_detected": 2, "files_processed": 3},
            {"changes_detected": 1, "files_processed": 2},
        ]

        result = await coordinator_with_mock_watcher.perform_manual_scan(recursive=False)

        # Verify both directories were scanned
        assert coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.call_count == 2

        # Verify aggregated result
        assert result["directories_scanned"] == 2
        assert result["total_changes_detected"] == 3
        assert result["total_files_processed"] == 5

    @pytest.mark.asyncio
    async def test_perform_manual_scan_no_directories(self, coordinator_with_mock_watcher):
        """Test manual scan with no directories specified or monitored."""
        with pytest.raises(MonitoringError) as exc_info:
            await coordinator_with_mock_watcher.perform_manual_scan()

        assert "No directory specified and no directories being monitored" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_perform_manual_scan_failure(self, coordinator_with_mock_watcher, tmp_path):
        """Test manual scan failure handling."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Mock indexer failure
        coordinator_with_mock_watcher.incremental_indexer.update_index_for_directory.side_effect = Exception(
            "Scan failed"
        )

        with pytest.raises(MonitoringError) as exc_info:
            await coordinator_with_mock_watcher.perform_manual_scan(test_dir)

        assert "Manual scan failed" in str(exc_info.value)

    def test_get_monitoring_stats(self, coordinator_with_mock_watcher):
        """Test getting monitoring statistics."""
        # Set up some state
        coordinator_with_mock_watcher._monitoring_active = True
        coordinator_with_mock_watcher._monitored_directories = [Path("/test/dir1"), Path("/test/dir2")]
        coordinator_with_mock_watcher._stats["files_processed"] = 10
        coordinator_with_mock_watcher._stats["operations"]["created"] = 3

        # Mock file watcher status
        coordinator_with_mock_watcher.file_watcher.is_watching = True
        coordinator_with_mock_watcher.file_watcher.get_watched_paths.return_value = ["/test/dir1", "/test/dir2"]
        coordinator_with_mock_watcher.file_watcher.get_pending_events_count.return_value = 2

        stats = coordinator_with_mock_watcher.get_monitoring_stats()

        # Verify structure and content
        assert stats["monitoring_active"] is True
        assert len(stats["monitored_directories"]) == 2
        assert stats["file_watcher_status"]["is_watching"] is True
        assert stats["file_watcher_status"]["pending_events"] == 2
        assert stats["processing_stats"]["files_processed"] == 10
        assert stats["configuration"]["monitoring_enabled"] is True

    def test_properties_and_getters(self, coordinator_with_mock_watcher):
        """Test property access and getter methods."""
        # Initially not monitoring
        assert not coordinator_with_mock_watcher.is_monitoring
        assert coordinator_with_mock_watcher.get_monitored_directories() == []

        # Add some state
        coordinator_with_mock_watcher._monitoring_active = True
        coordinator_with_mock_watcher._monitored_directories = [Path("/test/path1"), Path("/test/path2")]

        # Test properties
        assert coordinator_with_mock_watcher.is_monitoring
        directories = coordinator_with_mock_watcher.get_monitored_directories()
        assert len(directories) == 2
        assert "/test/path1" in directories
        assert "/test/path2" in directories

    @patch('markdown_rag_mcp.monitoring.monitoring_coordinator.logger')
    def test_logging_behavior(self, mock_logger, coordinator_with_mock_watcher, tmp_path):
        """Test that appropriate logging occurs during operations."""
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        # Test stop monitoring logging
        coordinator_with_mock_watcher._monitoring_active = True
        coordinator_with_mock_watcher.stop_monitoring()

        # Verify logging calls were made
        mock_logger.info.assert_called()
        mock_logger.debug.assert_not_called()  # Since monitoring was active
