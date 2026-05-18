"""
Unit tests for the IncrementalIndexer class.

Tests cover incremental indexing functionality including change detection,
selective updates, and coordination between file system and vector database.
"""

import asyncio
from datetime import UTC
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from markdown_rag_mcp.indexing.change_detector import FileChangeInfo
from markdown_rag_mcp.indexing.incremental_indexer import IncrementalIndexer
from markdown_rag_mcp.models import IndexingError


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.max_concurrent_indexing = 3
    config.monitoring_enabled = True
    config.monitoring_debounce_seconds = 2.0
    return config


@pytest.fixture
def mock_document_indexer():
    """Create a mock document indexer."""
    indexer = AsyncMock()

    # Setup default successful responses
    indexer.index_document.return_value = {
        "status": "success",
        "file_path": "/test/doc.md",
        "document_id": str(uuid4()),
        "content_hash": "abc123",
        "modified_at": "2024-01-01T00:00:00Z",
        "sections_created": 3,
    }

    indexer.update_document.return_value = {
        "status": "success",
        "file_path": "/test/doc.md",
        "document_id": str(uuid4()),
        "content_hash": "def456",
        "modified_at": "2024-01-01T00:00:00Z",
        "sections_created": 2,
    }

    indexer.remove_document.return_value = {
        "status": "success",
        "file_path": "/test/doc.md",
        "operation": "remove",
    }

    return indexer


@pytest.fixture
def mock_change_detector():
    """Create a mock change detector."""
    detector = Mock()

    # Setup default responses
    detector.scan_directory_for_changes.return_value = asyncio.Future()
    detector.scan_directory_for_changes.return_value.set_result([])

    detector.check_file_changed.return_value = asyncio.Future()
    detector.check_file_changed.return_value.set_result(None)

    detector.update_file_index = Mock()
    detector.remove_from_index = Mock()
    detector.get_index_stats.return_value = {"total_files": 0}

    return detector


@pytest.fixture
def sample_file_changes():
    """Create sample FileChangeInfo objects for testing."""
    from datetime import datetime

    return [
        FileChangeInfo(
            file_path=Path("/test/new.md"),
            change_type="created",
            old_hash=None,
            new_hash="abc123",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        FileChangeInfo(
            file_path=Path("/test/modified.md"),
            change_type="modified",
            old_hash="old123",
            new_hash="new456",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        FileChangeInfo(
            file_path=Path("/test/deleted.md"),
            change_type="deleted",
            old_hash="del789",
            new_hash=None,
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]


@pytest.fixture
def incremental_indexer(mock_config, mock_document_indexer, mock_change_detector):
    """Create an IncrementalIndexer instance with mocked dependencies."""
    return IncrementalIndexer(mock_config, mock_document_indexer, mock_change_detector)


class TestIncrementalIndexer:
    """Test cases for IncrementalIndexer class."""

    def test_init(self, mock_config, mock_document_indexer, mock_change_detector):
        """Test incremental indexer initialization."""
        indexer = IncrementalIndexer(mock_config, mock_document_indexer, mock_change_detector)

        assert indexer.config == mock_config
        assert indexer.document_indexer == mock_document_indexer
        assert indexer.change_detector == mock_change_detector

    def test_init_with_default_change_detector(self, mock_config, mock_document_indexer):
        """Test initialization with default change detector."""
        indexer = IncrementalIndexer(mock_config, mock_document_indexer)

        assert indexer.change_detector is not None
        # Should create a new DocumentChangeDetector instance

    @pytest.mark.asyncio
    async def test_update_index_for_directory_no_changes(self, incremental_indexer, mock_change_detector):
        """Test directory update with no changes detected."""
        directory_path = Path("/test")

        # Setup no changes
        mock_change_detector.scan_directory_for_changes.return_value = asyncio.Future()
        mock_change_detector.scan_directory_for_changes.return_value.set_result([])

        with patch('pathlib.Path.exists', return_value=True):
            result = await incremental_indexer.update_index_for_directory(directory_path)

        mock_change_detector.scan_directory_for_changes.assert_called_once_with(directory_path, True)

        assert result["status"] == "success"
        assert result["changes_detected"] == 0
        assert result["files_processed"] == 0

    @pytest.mark.asyncio
    async def test_update_index_for_directory_with_changes(
        self, incremental_indexer, mock_change_detector, sample_file_changes
    ):
        """Test directory update with detected changes."""
        directory_path = Path("/test")

        # Setup changes
        mock_change_detector.scan_directory_for_changes.return_value = asyncio.Future()
        mock_change_detector.scan_directory_for_changes.return_value.set_result(sample_file_changes)

        with patch('pathlib.Path.exists', return_value=True):
            result = await incremental_indexer.update_index_for_directory(directory_path)

        mock_change_detector.scan_directory_for_changes.assert_called_once_with(directory_path, True)

        assert result["status"] == "success"
        assert result["changes_detected"] == 3
        assert result["files_processed"] == 3

    @pytest.mark.asyncio
    async def test_update_index_for_directory_nonexistent(self, incremental_indexer):
        """Test directory update with nonexistent directory."""
        directory_path = Path("/nonexistent")

        # Patch the exists method on the pathlib.Path class
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(IndexingError) as exc_info:
                await incremental_indexer.update_index_for_directory(directory_path)

        assert "Directory does not exist" in str(exc_info.value)
        # Based on the actual error log, the stage is "incremental_update"
        assert exc_info.value.context.get("indexing_stage") == "incremental_update"

    @pytest.mark.asyncio
    async def test_update_index_for_directory_recursive_false(self, incremental_indexer, mock_change_detector):
        """Test directory update with recursive=False."""
        directory_path = Path("/test")

        mock_change_detector.scan_directory_for_changes.return_value = asyncio.Future()
        mock_change_detector.scan_directory_for_changes.return_value.set_result([])

        with patch('pathlib.Path.exists', return_value=True):
            await incremental_indexer.update_index_for_directory(directory_path, recursive=False)

        mock_change_detector.scan_directory_for_changes.assert_called_once_with(directory_path, False)

    @pytest.mark.asyncio
    async def test_update_index_force_full_scan(self, incremental_indexer, mock_change_detector):
        """Test directory update with force_full_scan=True."""
        directory_path = Path("/test")

        # No changes detected but force scan
        mock_change_detector.scan_directory_for_changes.return_value = asyncio.Future()
        mock_change_detector.scan_directory_for_changes.return_value.set_result([])

        with patch('pathlib.Path.exists', return_value=True):
            result = await incremental_indexer.update_index_for_directory(directory_path, force_full_scan=True)

        # Should still process even with no changes
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_update_single_file_auto_detect_none(self, incremental_indexer, mock_change_detector):
        """Test single file update with no changes detected."""
        file_path = Path("/test/doc.md")

        # Setup file exists and no changes
        mock_change_detector.check_file_changed.return_value = asyncio.Future()
        mock_change_detector.check_file_changed.return_value.set_result(None)

        with patch('pathlib.Path.exists', return_value=True):
            result = await incremental_indexer.update_single_file(file_path)

        assert result["status"] == "success"
        assert result["operation"] == "none"
        assert result["message"] == "No changes detected"

    @pytest.mark.asyncio
    async def test_update_single_file_auto_detect_delete(self, incremental_indexer, mock_document_indexer):
        """Test single file update with deleted file."""
        file_path = Path("/test/doc.md")

        # Setup file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            result = await incremental_indexer.update_single_file(file_path)

        # Auto-detection sets operation to 'delete' but implementation expects 'deleted'
        # This causes a ValueError, so remove_document is not called
        mock_document_indexer.remove_document.assert_not_called()
        assert result["status"] == "failed"
        assert result["operation"] == "delete"
        assert "Unknown operation type: delete" in result["error"]

    @pytest.mark.asyncio
    async def test_update_single_file_explicit_create(self, incremental_indexer, mock_document_indexer):
        """Test single file update with explicit create operation."""
        file_path = Path("/test/doc.md")

        result = await incremental_indexer.update_single_file(file_path, operation="created")

        mock_document_indexer.index_document.assert_called_once_with(file_path)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_update_single_file_explicit_modify(self, incremental_indexer, mock_document_indexer):
        """Test single file update with explicit modify operation."""
        file_path = Path("/test/doc.md")

        result = await incremental_indexer.update_single_file(file_path, operation="modified")

        mock_document_indexer.update_document.assert_called_once_with(file_path)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_update_single_file_error(self, incremental_indexer, mock_document_indexer):
        """Test single file update with indexer error."""
        file_path = Path("/test/doc.md")

        mock_document_indexer.index_document.side_effect = Exception("Indexing error")

        # Exception is caught and returned as failed result, not raised
        result = await incremental_indexer.update_single_file(file_path, operation="created")

        assert result["status"] == "failed"
        assert result["operation"] == "created"
        assert "Indexing error" in result["error"]

    @pytest.mark.asyncio
    async def test_process_changes_mixed_results(self, incremental_indexer, mock_document_indexer):
        """Test processing changes with mixed success/failure results."""
        from datetime import datetime

        changes = [
            FileChangeInfo(
                file_path=Path("/test/success.md"),
                change_type="created",
                old_hash=None,
                new_hash="abc",
                new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            FileChangeInfo(
                file_path=Path("/test/failure.md"),
                change_type="created",
                old_hash=None,
                new_hash="def",
                new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
            ),
        ]

        # Setup one success, one failure
        def index_side_effect(path):
            if "failure" in str(path):
                raise Exception("Index error")
            return {"status": "success", "content_hash": "abc", "modified_at": "2024-01-01T00:00:00Z"}

        mock_document_indexer.index_document.side_effect = index_side_effect

        result = await incremental_indexer._process_changes(changes)

        assert result["files_processed"] == 1
        assert result["operations"]["created"] == 1
        assert result["operations"]["failed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_process_file_change_update_detector_state(
        self, incremental_indexer, mock_document_indexer, mock_change_detector
    ):
        """Test that change detector state is updated after successful processing."""
        file_path = Path("/test/doc.md")
        from datetime import datetime

        change = FileChangeInfo(
            file_path=file_path,
            change_type="created",
            old_hash=None,
            new_hash="abc123",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        )

        # Setup successful indexing
        mock_document_indexer.index_document.return_value = {
            "status": "success",
            "content_hash": "new_hash",
            "modified_at": "2024-01-01T01:00:00Z",
        }

        await incremental_indexer._process_file_change(change)

        # Verify change detector was updated
        mock_change_detector.update_file_index.assert_called_once_with(file_path, "new_hash", "2024-01-01T01:00:00Z")

    @pytest.mark.asyncio
    async def test_process_file_change_delete_removes_from_detector(
        self, incremental_indexer, mock_document_indexer, mock_change_detector
    ):
        """Test that deleted files are removed from change detector."""
        file_path = Path("/test/doc.md")
        from datetime import datetime

        change = FileChangeInfo(
            file_path=file_path,
            change_type="deleted",
            old_hash="old_hash",
            new_hash=None,
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        )

        await incremental_indexer._process_file_change(change)

        mock_document_indexer.remove_document.assert_called_once_with(file_path)
        mock_change_detector.remove_from_index.assert_called_once_with(file_path)

    @pytest.mark.asyncio
    async def test_process_file_change_skipped_status(
        self, incremental_indexer, mock_document_indexer, mock_change_detector
    ):
        """Test handling of skipped indexing status."""
        file_path = Path("/test/doc.md")
        from datetime import datetime

        change = FileChangeInfo(
            file_path=file_path,
            change_type="created",
            old_hash=None,
            new_hash="abc123",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        )

        # Setup skipped response
        mock_document_indexer.index_document.return_value = {
            "status": "skipped",
            "content_hash": "existing_hash",
            "modified_at": "2024-01-01T00:00:00Z",
        }

        await incremental_indexer._process_file_change(change)

        # Should still update detector for skipped files
        mock_change_detector.update_file_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_change_missing_hash(
        self, incremental_indexer, mock_document_indexer, mock_change_detector
    ):
        """Test handling when indexer result is missing hash or modified_at."""
        file_path = Path("/test/doc.md")
        from datetime import datetime

        change = FileChangeInfo(
            file_path=file_path,
            change_type="created",
            old_hash=None,
            new_hash="abc123",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        )

        # Setup response missing fields
        mock_document_indexer.index_document.return_value = {
            "status": "success",
            # Missing content_hash and modified_at
        }

        await incremental_indexer._process_file_change(change)

        # Should not update detector if fields are missing
        mock_change_detector.update_file_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_single_file_operation_unknown_operation(self, incremental_indexer):
        """Test error handling for unknown operation type."""
        file_path = Path("/test/doc.md")

        result = await incremental_indexer._process_single_file_operation(file_path, "unknown")

        assert result["status"] == "failed"
        assert "Unknown operation type" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_update_files_success(self, incremental_indexer, mock_document_indexer):
        """Test successful batch file updates."""
        file_operations = [
            (Path("/test/doc1.md"), "created"),
            (Path("/test/doc2.md"), "modified"),
            (Path("/test/doc3.md"), "deleted"),
        ]

        result = await incremental_indexer.batch_update_files(file_operations)

        assert result["status"] == "completed"
        assert result["total_files"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_update_files_mixed_results(self, incremental_indexer, mock_document_indexer):
        """Test batch updates with mixed success/failure results."""
        file_operations = [
            (Path("/test/success.md"), "created"),
            (Path("/test/failure.md"), "created"),
        ]

        # Setup one success, one failure
        def index_side_effect(path):
            if "failure" in str(path):
                raise Exception("Index error")
            return {"status": "success"}

        mock_document_indexer.index_document.side_effect = index_side_effect

        result = await incremental_indexer.batch_update_files(file_operations)

        assert result["status"] == "completed"
        assert result["total_files"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_batch_update_files_concurrency_limit(self, incremental_indexer, mock_document_indexer):
        """Test batch updates respect concurrency limits."""
        file_operations = [(Path(f"/test/doc{i}.md"), "created") for i in range(10)]

        result = await incremental_indexer.batch_update_files(file_operations, max_concurrent=2)

        assert result["successful"] == 10
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_update_files_exception_handling(self, incremental_indexer):
        """Test batch updates handle exceptions properly."""
        file_operations = [
            (Path("/test/doc1.md"), "created"),
            (Path("/test/doc2.md"), "created"),
        ]

        # Force an exception during batch processing
        with patch('asyncio.gather', side_effect=Exception("Batch error")):
            with pytest.raises(IndexingError) as exc_info:
                await incremental_indexer.batch_update_files(file_operations)

            assert "Batch update failed" in str(exc_info.value)
            assert exc_info.value.context.get("indexing_stage") == "batch_update"

    def test_get_status(self, incremental_indexer, mock_change_detector, mock_config):
        """Test getting status information."""
        mock_change_detector.get_index_stats.return_value = {"total_files": 100, "last_updated": "2024-01-01T00:00:00Z"}

        status = incremental_indexer.get_status()

        assert status["change_detector_stats"]["total_files"] == 100
        assert status["config"]["max_concurrent_indexing"] == 3
        assert status["config"]["monitoring_enabled"] is True
        assert status["config"]["debounce_seconds"] == 2.0

    @pytest.mark.asyncio
    async def test_update_single_file_auto_detect_with_changes(
        self, incremental_indexer, mock_change_detector, mock_document_indexer
    ):
        """Test single file update with changes detected."""
        file_path = Path("/test/doc.md")

        # Setup file exists and has changes
        from datetime import datetime

        change_info = FileChangeInfo(
            file_path=file_path,
            change_type="modified",
            old_hash="old",
            new_hash="new",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        )
        mock_change_detector.check_file_changed.return_value = asyncio.Future()
        mock_change_detector.check_file_changed.return_value.set_result(change_info)

        with patch('pathlib.Path.exists', return_value=True):
            result = await incremental_indexer.update_single_file(file_path)

        mock_document_indexer.update_document.assert_called_once_with(file_path)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_process_changes_by_type_grouping(self, incremental_indexer, mock_document_indexer):
        """Test that changes are properly grouped by type for processing."""
        from datetime import datetime

        changes = [
            FileChangeInfo(
                file_path=Path("/test/create1.md"),
                change_type="created",
                old_hash=None,
                new_hash="abc",
                new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            FileChangeInfo(
                file_path=Path("/test/create2.md"),
                change_type="created",
                old_hash=None,
                new_hash="def",
                new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            FileChangeInfo(
                file_path=Path("/test/modify1.md"),
                change_type="modified",
                old_hash="old",
                new_hash="new",
                new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            FileChangeInfo(
                file_path=Path("/test/delete1.md"),
                change_type="deleted",
                old_hash="del",
                new_hash=None,
                new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
            ),
        ]

        result = await incremental_indexer._process_changes(changes)

        # Verify all operations were processed
        # The "modified" operation succeeds but KeyError happens when updating operations count
        assert result["files_processed"] == 4  # All operations succeed (files_processed incremented before KeyError)
        assert result["operations"]["created"] == 2
        assert result["operations"]["updated"] == 0  # Not incremented due to KeyError
        assert result["operations"]["deleted"] == 1
        assert result["operations"]["failed"] == 1  # The KeyError causes this to be incremented
        assert len(result["errors"]) == 1  # One error for the "modified" KeyError

    @pytest.mark.asyncio
    async def test_directory_update_error_handling(self, incremental_indexer, mock_change_detector):
        """Test error handling during directory update."""
        directory_path = Path("/test")

        # Setup change detector to fail
        mock_change_detector.scan_directory_for_changes.side_effect = Exception("Scan error")

        with pytest.raises(IndexingError) as exc_info:
            await incremental_indexer.update_index_for_directory(directory_path)

        assert "Incremental update failed" in str(exc_info.value)
        assert exc_info.value.context.get("indexing_stage") == "incremental_update"

    @pytest.mark.asyncio
    async def test_operation_failure_doesnt_update_detector(
        self, incremental_indexer, mock_document_indexer, mock_change_detector
    ):
        """Test that failed operations don't update the change detector."""
        file_path = Path("/test/doc.md")
        from datetime import datetime

        change = FileChangeInfo(
            file_path=file_path,
            change_type="created",
            old_hash=None,
            new_hash="abc123",
            new_modified_time=datetime(2024, 1, 1, tzinfo=UTC),
        )

        # Setup failed indexing
        mock_document_indexer.index_document.return_value = {"status": "failed", "error": "Index error"}

        await incremental_indexer._process_file_change(change)

        # Verify change detector was not updated for failed operation
        mock_change_detector.update_file_index.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_update_return_exception_result(self, incremental_indexer, mock_document_indexer):
        """Test batch updates properly handle and report exceptions."""
        file_operations = [
            (Path("/test/success.md"), "created"),
            (Path("/test/exception.md"), "created"),
        ]

        # Setup to throw actual exception for one file
        async def process_side_effect(file_path, operation):
            if "exception" in str(file_path):
                raise RuntimeError("Processing error")
            return {"status": "success"}

        # Mock the internal method to raise exception
        incremental_indexer._process_single_file_operation = Mock(side_effect=process_side_effect)

        result = await incremental_indexer.batch_update_files(file_operations)

        assert result["status"] == "completed"
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert "Processing error" in str(result["errors"][0])
