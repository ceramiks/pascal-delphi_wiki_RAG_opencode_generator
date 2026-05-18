"""
Unit tests for the DocumentChangeDetector class.

Tests cover file change detection, directory scanning, hash calculation,
and index management functionality.
"""

import hashlib
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from markdown_rag_mcp.indexing import DocumentChangeDetector
from markdown_rag_mcp.models import Document, IndexingError, ProcessingStatus


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.is_file_supported.return_value = True
    config.should_ignore_file.return_value = False
    return config


@pytest.fixture
def change_detector(mock_config):
    """Create a DocumentChangeDetector instance."""
    return DocumentChangeDetector(mock_config)


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    return Document(
        file_path="/test/sample.md",
        content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
        file_size=1024,
        created_at=datetime.now(UTC),
        modified_at=datetime.now(UTC),
        processing_status=ProcessingStatus.INDEXED,
    )


class TestDocumentChangeDetector:
    """Test cases for DocumentChangeDetector class."""

    def test_init(self, mock_config):
        """Test change detector initialization."""
        detector = DocumentChangeDetector(mock_config)

        assert detector.config == mock_config
        assert detector._file_index == {}

    @pytest.mark.asyncio
    async def test_scan_directory_for_changes_nonexistent_directory(self, change_detector):
        """Test scanning a non-existent directory raises error."""
        non_existent_path = Path("/non/existent/path")

        with pytest.raises(IndexingError) as exc_info:
            await change_detector.scan_directory_for_changes(non_existent_path)

        assert "Directory does not exist" in str(exc_info.value)
        assert exc_info.value.context.get("file_path") == str(non_existent_path)
        assert exc_info.value.context.get("indexing_stage") == "change_detection"

    @pytest.mark.asyncio
    async def test_scan_directory_for_changes_empty_directory(self, change_detector):
        """Test scanning an empty directory returns no changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            changes = await change_detector.scan_directory_for_changes(temp_path)

            assert changes == []

    @pytest.mark.asyncio
    async def test_scan_directory_for_changes_new_file(self, change_detector):
        """Test detecting a new markdown file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"
            test_file.write_text("# Test Content")

            changes = await change_detector.scan_directory_for_changes(temp_path)

            assert len(changes) == 1
            change = changes[0]
            assert change.file_path == test_file
            assert change.change_type == "created"
            assert change.new_hash is not None
            assert change.new_modified_time is not None
            assert change.old_hash is None

    @pytest.mark.asyncio
    async def test_scan_directory_for_changes_modified_file(self, change_detector, sample_document):
        """Test detecting a modified file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"
            test_file.write_text("# Modified Content")

            # Simulate known document with different hash
            sample_document.file_path = str(test_file)
            sample_document.content_hash = "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752"

            changes = await change_detector.scan_directory_for_changes(temp_path, known_documents=[sample_document])

            assert len(changes) == 1
            change = changes[0]
            assert change.file_path == test_file
            assert change.change_type == "modified"
            assert change.old_hash == "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752"
            assert change.new_hash != "60303ae22b998861bce3b28f33eec1be758a213c86c93c076dbe9f558c11c752"

    @pytest.mark.asyncio
    async def test_scan_directory_for_changes_deleted_file(self, change_detector, sample_document):
        """Test detecting a deleted file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # File exists in known documents but not on disk
            sample_document.file_path = str(temp_path / "deleted.md")

            changes = await change_detector.scan_directory_for_changes(temp_path, known_documents=[sample_document])

            assert len(changes) == 1
            change = changes[0]
            assert change.file_path == Path(sample_document.file_path)
            assert change.change_type == "deleted"
            assert change.old_hash == sample_document.content_hash
            assert change.new_hash is None

    @pytest.mark.asyncio
    async def test_scan_directory_for_changes_no_changes(self, change_detector, sample_document):
        """Test scanning when no changes are detected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"
            test_file.write_text("# Test Content")

            # Calculate actual hash for the file
            actual_hash = await change_detector._calculate_file_hash(test_file)
            sample_document.file_path = str(test_file)
            sample_document.content_hash = actual_hash
            sample_document.modified_at = datetime.fromtimestamp(test_file.stat().st_mtime, UTC)

            changes = await change_detector.scan_directory_for_changes(temp_path, known_documents=[sample_document])

            assert changes == []

    @pytest.mark.asyncio
    async def test_check_file_changed_nonexistent_file_no_known_doc(self, change_detector):
        """Test checking a non-existent file with no known document."""
        non_existent_file = Path("/non/existent/file.md")

        result = await change_detector.check_file_changed(non_existent_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_check_file_changed_deleted_file(self, change_detector, sample_document):
        """Test checking a deleted file with known document."""
        deleted_file = Path("/deleted/file.md")

        result = await change_detector.check_file_changed(deleted_file, sample_document)

        assert result is not None
        assert result.change_type == "deleted"
        assert result.file_path == deleted_file
        assert result.old_hash == sample_document.content_hash

    @pytest.mark.asyncio
    async def test_check_file_changed_new_file(self, change_detector):
        """Test checking a new file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "new_file.md"
            test_file.write_text("# New Content")

            result = await change_detector.check_file_changed(test_file)

            assert result is not None
            assert result.change_type == "created"
            assert result.file_path == test_file
            assert result.new_hash is not None
            assert result.old_hash is None

    @pytest.mark.asyncio
    async def test_check_file_changed_modified_file(self, change_detector, sample_document):
        """Test checking a modified file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "modified_file.md"
            test_file.write_text("# Modified Content")

            # Set known document with different hash and older timestamp
            sample_document.file_path = str(test_file)
            sample_document.content_hash = "fd61a03af4f77d870fc21e05e7e80678095c92d808cfb3b5c279ee04c74aca13"
            sample_document.modified_at = datetime.fromtimestamp(test_file.stat().st_mtime - 3600, UTC)  # 1 hour ago

            result = await change_detector.check_file_changed(test_file, sample_document)

            assert result is not None
            assert result.change_type == "modified"
            assert result.old_hash == "fd61a03af4f77d870fc21e05e7e80678095c92d808cfb3b5c279ee04c74aca13"
            assert result.new_hash != "fd61a03af4f77d870fc21e05e7e80678095c92d808cfb3b5c279ee04c74aca13"

    @pytest.mark.asyncio
    async def test_check_file_changed_unchanged_file(self, change_detector, sample_document):
        """Test checking an unchanged file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "unchanged_file.md"
            test_file.write_text("# Unchanged Content")

            # Set known document with same hash and timestamp
            actual_hash = await change_detector._calculate_file_hash(test_file)
            sample_document.file_path = str(test_file)
            sample_document.content_hash = actual_hash
            sample_document.modified_at = datetime.fromtimestamp(test_file.stat().st_mtime, UTC)

            result = await change_detector.check_file_changed(test_file, sample_document)

            assert result is None

    @pytest.mark.asyncio
    async def test_calculate_file_hash(self, change_detector):
        """Test file hash calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "hash_test.md"
            content = "# Test Content for Hashing"
            test_file.write_text(content)

            calculated_hash = await change_detector._calculate_file_hash(test_file)

            # Verify hash format
            assert len(calculated_hash) == 64  # SHA-256 hex string
            assert all(c in '0123456789abcdef' for c in calculated_hash)

            # Hash should be reproducible
            calculated_hash_2 = await change_detector._calculate_file_hash(test_file)
            assert calculated_hash == calculated_hash_2

    @pytest.mark.asyncio
    async def test_calculate_file_hash_error_handling(self, change_detector):
        """Test file hash calculation error handling."""
        non_existent_file = Path("/non/existent/file.md")

        # Should return a fallback hash based on file path
        fallback_hash = await change_detector._calculate_file_hash(non_existent_file)

        assert len(fallback_hash) == 64
        # Should be the hash of the file path string
        expected_hash = hashlib.sha256(str(non_existent_file).encode()).hexdigest()
        assert fallback_hash == expected_hash

    def test_should_process_file_supported(self, change_detector):
        """Test should_process_file with supported file."""
        test_file = Path("/test/file.md")

        result = change_detector._should_process_file(test_file)

        assert result is True
        change_detector.config.is_file_supported.assert_called_once_with(test_file)
        change_detector.config.should_ignore_file.assert_called_once_with(test_file)

    def test_should_process_file_unsupported(self, change_detector):
        """Test should_process_file with unsupported file."""
        test_file = Path("/test/file.txt")
        change_detector.config.is_file_supported.return_value = False

        result = change_detector._should_process_file(test_file)

        assert result is False

    def test_should_process_file_ignored(self, change_detector):
        """Test should_process_file with ignored file."""
        test_file = Path("/test/.hidden.md")
        change_detector.config.should_ignore_file.return_value = True

        result = change_detector._should_process_file(test_file)

        assert result is False

    def test_should_process_file_error(self, change_detector):
        """Test should_process_file error handling."""
        test_file = Path("/test/file.md")
        change_detector.config.is_file_supported.side_effect = Exception("Test error")

        result = change_detector._should_process_file(test_file)

        assert result is False

    def test_update_file_index(self, change_detector):
        """Test updating the file index."""
        file_path = Path("/test/file.md")
        content_hash = "abc123"
        modified_time = datetime.now(UTC)

        change_detector.update_file_index(file_path, content_hash, modified_time)

        file_key = str(file_path)
        assert file_key in change_detector._file_index
        index_entry = change_detector._file_index[file_key]
        assert index_entry['hash'] == content_hash
        assert index_entry['modified_time'] == modified_time
        assert 'last_checked' in index_entry

    def test_remove_from_index(self, change_detector):
        """Test removing a file from the index."""
        file_path = Path("/test/file.md")
        file_key = str(file_path)

        # Add file to index first
        change_detector._file_index[file_key] = {
            'hash': 'abc123',
            'modified_time': datetime.now(UTC),
        }

        change_detector.remove_from_index(file_path)

        assert file_key not in change_detector._file_index

    def test_remove_from_index_nonexistent(self, change_detector):
        """Test removing a non-existent file from index."""
        file_path = Path("/test/nonexistent.md")

        # Should not raise error
        change_detector.remove_from_index(file_path)

        assert str(file_path) not in change_detector._file_index

    def test_get_index_stats_empty(self, change_detector):
        """Test getting index statistics when empty."""
        stats = change_detector.get_index_stats()

        assert stats['indexed_files'] == 0
        assert stats['total_size'] == 0

    def test_get_index_stats_with_files(self, change_detector):
        """Test getting index statistics with files."""
        file_path1 = Path("/test/file1.md")
        file_path2 = Path("/test/file2.md")
        modified_time = datetime.now(UTC)

        change_detector.update_file_index(file_path1, "hash123", modified_time)
        change_detector.update_file_index(file_path2, "hash456", modified_time)

        stats = change_detector.get_index_stats()

        assert stats['indexed_files'] == 2
        assert stats['total_size'] > 0

    @pytest.mark.asyncio
    async def test_check_file_for_changes_mtime_optimization(self, change_detector):
        """Test that files with unchanged mtime are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "mtime_test.md"
            test_file.write_text("# Test Content")

            stat = test_file.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime, UTC)

            known_info = {
                'hash': 'some_hash',
                'modified_time': modified_time,
            }

            result = await change_detector._check_file_for_changes(test_file, known_info)

            assert result is None  # No change detected due to mtime optimization

    @pytest.mark.asyncio
    async def test_check_file_for_changes_same_hash_different_mtime(self, change_detector):
        """Test file with newer mtime but same content hash."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "same_hash_test.md"
            test_file.write_text("# Test Content")

            # Calculate actual hash
            actual_hash = await change_detector._calculate_file_hash(test_file)

            # Simulate older known info
            old_time = datetime.fromtimestamp(test_file.stat().st_mtime - 3600, UTC)
            known_info = {
                'hash': actual_hash,  # Same hash
                'modified_time': old_time,  # Older time
            }

            result = await change_detector._check_file_for_changes(test_file, known_info)

            assert result is None  # No change despite mtime difference

    @pytest.mark.asyncio
    async def test_scan_directory_recursive_vs_non_recursive(self, change_detector):
        """Test recursive vs non-recursive directory scanning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files at different levels
            root_file = temp_path / "root.md"
            root_file.write_text("# Root")

            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            sub_file = sub_dir / "sub.md"
            sub_file.write_text("# Sub")

            # Non-recursive scan
            changes = await change_detector.scan_directory_for_changes(temp_path, recursive=False)
            assert len(changes) == 1
            assert changes[0].file_path.name == "root.md"

            # Recursive scan
            changes = await change_detector.scan_directory_for_changes(temp_path, recursive=True)
            assert len(changes) == 2
            file_names = {change.file_path.name for change in changes}
            assert file_names == {"root.md", "sub.md"}

    @pytest.mark.asyncio
    async def test_scan_directory_exception_handling(self, change_detector):
        """Test exception handling during directory scanning."""
        with patch.object(change_detector, '_check_file_for_changes', side_effect=Exception("Test error")):
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_file = temp_path / "error_test.md"
                test_file.write_text("# Test")

                with pytest.raises(IndexingError) as exc_info:
                    await change_detector.scan_directory_for_changes(temp_path)

                assert "Directory change scan failed" in str(exc_info.value)
                assert exc_info.value.context.get("indexing_stage") == "change_detection"

    @pytest.mark.asyncio
    async def test_check_file_changed_exception_handling(self, change_detector):
        """Test exception handling during file change checking."""
        with patch.object(change_detector, '_check_file_for_changes', side_effect=Exception("Test error")):
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = Path(temp_dir) / "error_test.md"
                test_file.write_text("# Test")

                with pytest.raises(IndexingError) as exc_info:
                    await change_detector.check_file_changed(test_file)

                assert "File change check failed" in str(exc_info.value)
                assert exc_info.value.context.get("indexing_stage") == "file_change_check"
