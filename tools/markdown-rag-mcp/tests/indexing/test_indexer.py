"""
Unit tests for the DocumentIndexer class.

Tests cover the complete document indexing pipeline including parsing,
chunking, embedding generation, and vector storage coordination.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from markdown_rag_mcp.indexing.indexer import DocumentIndexer
from markdown_rag_mcp.models import (
    Document,
    DocumentSection,
    IndexingError,
    ProcessingStatus,
    SectionType,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    config.max_concurrent_indexing = 5
    config.chunk_size_limit = 500
    config.chunk_overlap = 50
    return config


@pytest.fixture
def mock_document_parser():
    """Create a mock document parser."""
    parser = AsyncMock()
    return parser


@pytest.fixture
def mock_embedding_provider():
    """Create a mock embedding provider."""
    provider = AsyncMock()
    provider.generate_batch_embeddings.return_value = [[0.1, 0.2, 0.3]] * 3  # Mock 3 embeddings
    return provider


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = AsyncMock()
    store.store_document_sections = AsyncMock()
    store.delete_document = AsyncMock()
    store.get_document_by_hash = AsyncMock(return_value=None)  # No existing document by default
    return store


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    doc = Document(
        file_path="/test/sample.md",
        content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
        file_size=1024,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        modified_at=datetime(2024, 1, 1, tzinfo=UTC),
        processing_status=ProcessingStatus.PENDING,
        frontmatter={"title": "Sample Document", "tags": ["test"]},
    )
    # Add raw content as private attribute (this is how the parser provides it)
    doc._raw_content = "# Sample Document\n\nThis is test content for the document."
    return doc


@pytest.fixture
def sample_sections():
    """Create sample DocumentSections for testing."""
    doc_id = uuid4()
    return [
        DocumentSection(
            document_id=doc_id,
            section_text="Enhanced section 1 content",
            heading="Section 1",
            heading_level=1,
            chunk_index=0,
            token_count=25,
            start_position=0,
            end_position=50,
            section_type=SectionType.HEADING,
        ),
        DocumentSection(
            document_id=doc_id,
            section_text="Enhanced section 2 content",
            heading="Section 2",
            heading_level=2,
            chunk_index=1,
            token_count=30,
            start_position=50,
            end_position=100,
            section_type=SectionType.HEADING,
        ),
        DocumentSection(
            document_id=doc_id,
            section_text="Enhanced paragraph content",
            heading=None,
            heading_level=None,
            chunk_index=2,
            token_count=20,
            start_position=100,
            end_position=150,
            section_type=SectionType.PARAGRAPH,
        ),
    ]


@pytest.fixture
def indexer(mock_config, mock_document_parser, mock_embedding_provider, mock_vector_store):
    """Create a DocumentIndexer instance with mocked dependencies."""
    # Create mock metadata enhancer and chunker
    mock_metadata_enhancer = Mock()
    mock_chunker = Mock()

    indexer = DocumentIndexer(
        config=mock_config,
        document_parser=mock_document_parser,
        embedding_provider=mock_embedding_provider,
        vector_store=mock_vector_store,
        metadata_enhancer=mock_metadata_enhancer,
        chunker=mock_chunker,
    )

    return indexer


class TestDocumentIndexer:
    """Test cases for DocumentIndexer class."""

    def test_init(self, mock_config, mock_document_parser, mock_embedding_provider, mock_vector_store):
        """Test indexer initialization."""
        indexer = DocumentIndexer(
            config=mock_config,
            document_parser=mock_document_parser,
            embedding_provider=mock_embedding_provider,
            vector_store=mock_vector_store,
        )

        assert indexer.config == mock_config
        assert indexer.document_parser == mock_document_parser
        assert indexer.embedding_provider == mock_embedding_provider
        assert indexer.vector_store == mock_vector_store
        assert indexer.metadata_enhancer is not None
        assert indexer.chunker is not None

    @pytest.mark.asyncio
    async def test_index_document_success(self, indexer, sample_document, sample_sections):
        """Test successful document indexing."""
        file_path = Path("/test/sample.md")

        # Setup mocks
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {
            "total_sections": 3,
            "avg_tokens": 25.0,
            "sections_with_headings": 2,
        }
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {
            "has_frontmatter": True,
            "has_title": True,
            "metadata_fields": ["title", "tags"],
        }

        result = await indexer.index_document(file_path)

        # Verify calls
        indexer.document_parser.parse_file.assert_called_once_with(file_path)
        indexer.chunker.chunk_document.assert_called_once_with(sample_document, sample_document._raw_content)
        indexer.embedding_provider.generate_batch_embeddings.assert_called_once()
        indexer.vector_store.store_document_sections.assert_called_once()

        # Verify result
        assert result["status"] == "success"
        assert result["file_path"] == str(file_path)
        assert result["sections_created"] == 3
        assert result["has_frontmatter"] is True
        assert "processing_time" in result
        assert "chunking_stats" in result
        assert "enhancement_stats" in result

    @pytest.mark.asyncio
    async def test_index_document_no_raw_content(self, indexer):
        """Test indexing fails when document has no raw content."""
        file_path = Path("/test/sample.md")

        document = Document(
            file_path=str(file_path),
            content_hash="1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014",
            file_size=1024,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            modified_at=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=ProcessingStatus.PENDING,
        )
        # No _raw_content attribute

        indexer.document_parser.parse_file.return_value = document

        with pytest.raises(IndexingError) as exc_info:
            await indexer.index_document(file_path)

        assert "Document parser did not provide raw content" in str(exc_info.value)
        assert exc_info.value.context.get("file_path") == str(file_path)
        assert exc_info.value.context.get("indexing_stage") == "indexing_pipeline"

    @pytest.mark.asyncio
    async def test_index_document_no_sections(self, indexer, sample_document):
        """Test indexing document that produces no sections."""
        file_path = Path("/test/empty.md")

        # Setup mocks
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = []  # No sections

        result = await indexer.index_document(file_path)

        # Verify result
        assert result["status"] == "success"
        assert result["sections_created"] == 0
        assert result["message"] == "No content to index"

    @pytest.mark.asyncio
    async def test_index_document_skip_existing(self, indexer, sample_document):
        """Test skipping indexing for existing document with same hash."""
        file_path = Path("/test/sample.md")

        # Setup existing document
        existing_doc = {
            "file_path": str(file_path),
            "content_hash": sample_document.content_hash,
        }
        indexer.vector_store.get_document_by_hash.return_value = existing_doc
        indexer.document_parser.parse_file.return_value = sample_document

        result = await indexer.index_document(file_path, force_reindex=False)

        # Should skip indexing
        assert result["status"] == "skipped"
        assert "already indexed with same content" in result["message"]
        indexer.chunker.chunk_document.assert_not_called()
        indexer.embedding_provider.generate_batch_embeddings.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_document_force_reindex(self, indexer, sample_document, sample_sections):
        """Test force reindexing existing document."""
        file_path = Path("/test/sample.md")

        # Setup existing document
        existing_doc = {
            "file_path": str(file_path),
            "content_hash": sample_document.content_hash,
        }
        indexer.vector_store.get_document_by_hash.return_value = existing_doc
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        result = await indexer.index_document(file_path, force_reindex=True)

        # Should proceed with indexing
        assert result["status"] == "success"
        indexer.chunker.chunk_document.assert_called_once()
        indexer.embedding_provider.generate_batch_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_document_embedding_count_mismatch(self, indexer, sample_document, sample_sections):
        """Test error when embedding count doesn't match sections."""
        file_path = Path("/test/sample.md")

        # Setup mocks with mismatched counts
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections  # 3 sections
        indexer.embedding_provider.generate_batch_embeddings.return_value = [[0.1, 0.2]] * 2  # Only 2 embeddings

        with pytest.raises(IndexingError) as exc_info:
            await indexer.index_document(file_path)

        assert "Embedding count mismatch" in str(exc_info.value)
        assert exc_info.value.context.get("indexing_stage") == "indexing_pipeline"

    @pytest.mark.asyncio
    async def test_index_document_parsing_error(self, indexer):
        """Test error handling during document parsing."""
        file_path = Path("/test/sample.md")

        # Setup parser to raise exception
        indexer.document_parser.parse_file.side_effect = Exception("Parse error")

        with pytest.raises(IndexingError) as exc_info:
            await indexer.index_document(file_path)

        assert "Document indexing failed" in str(exc_info.value)
        assert exc_info.value.context.get("indexing_stage") == "indexing_pipeline"

    @pytest.mark.asyncio
    async def test_update_document(self, indexer, sample_document, sample_sections):
        """Test updating an existing document."""
        file_path = Path("/test/sample.md")

        # Setup mocks
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        result = await indexer.update_document(file_path)

        # Verify deletion and reindexing
        indexer.vector_store.delete_document.assert_called_once_with(str(file_path))
        indexer.document_parser.parse_file.assert_called_once_with(file_path)

        assert result["status"] == "success"
        assert result["operation"] == "update"

    @pytest.mark.asyncio
    async def test_update_document_error(self, indexer):
        """Test error handling during document update."""
        file_path = Path("/test/sample.md")

        # Setup vector store to raise exception
        indexer.vector_store.delete_document.side_effect = Exception("Delete error")

        with pytest.raises(IndexingError) as exc_info:
            await indexer.update_document(file_path)

        assert "Document update failed" in str(exc_info.value)
        assert exc_info.value.context.get("indexing_stage") == "document_update"

    @pytest.mark.asyncio
    async def test_remove_document(self, indexer):
        """Test removing a document from the index."""
        file_path = Path("/test/sample.md")

        result = await indexer.remove_document(file_path)

        # Verify deletion
        indexer.vector_store.delete_document.assert_called_once_with(str(file_path))

        assert result["status"] == "success"
        assert result["operation"] == "remove"
        assert result["file_path"] == str(file_path)

    @pytest.mark.asyncio
    async def test_remove_document_error(self, indexer):
        """Test error handling during document removal."""
        file_path = Path("/test/sample.md")

        # Setup vector store to raise exception
        indexer.vector_store.delete_document.side_effect = Exception("Delete error")

        with pytest.raises(IndexingError) as exc_info:
            await indexer.remove_document(file_path)

        assert "Document removal failed" in str(exc_info.value)
        assert exc_info.value.context.get("indexing_stage") == "document_removal"

    @pytest.mark.asyncio
    async def test_batch_index_documents_success(self, indexer, sample_document, sample_sections):
        """Test successful batch indexing."""
        file_paths = [Path(f"/test/doc{i}.md") for i in range(3)]

        # Setup mocks for all documents
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        result = await indexer.batch_index_documents(file_paths)

        # Verify calls
        assert indexer.document_parser.parse_file.call_count == 3
        assert indexer.embedding_provider.generate_batch_embeddings.call_count == 3

        # Verify result
        assert result["status"] == "completed"
        assert result["total_files"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_index_documents_mixed_results(self, indexer, sample_document, sample_sections):
        """Test batch indexing with some failures."""
        file_paths = [Path(f"/test/doc{i}.md") for i in range(3)]

        # Setup mixed results - first two succeed, third fails
        def parse_side_effect(path):
            if "doc2" in str(path):
                raise Exception("Parse error")
            return sample_document

        indexer.document_parser.parse_file.side_effect = parse_side_effect
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        result = await indexer.batch_index_documents(file_paths)

        # Verify result
        assert result["status"] == "completed"
        assert result["total_files"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_batch_index_documents_concurrency_limit(self, indexer, sample_document, sample_sections):
        """Test batch indexing respects concurrency limits."""
        file_paths = [Path(f"/test/doc{i}.md") for i in range(10)]

        # Setup mocks
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        # Test with custom concurrency limit
        result = await indexer.batch_index_documents(file_paths, max_concurrent=3)

        assert result["successful"] == 10
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_index_documents_error(self, indexer):
        """Test error handling during batch indexing setup."""
        # Create an invalid scenario that causes batch processing to fail
        with patch('asyncio.gather', side_effect=Exception("Batch error")):
            file_paths = [Path("/test/doc1.md")]

            with pytest.raises(IndexingError) as exc_info:
                await indexer.batch_index_documents(file_paths)

            assert "Batch indexing failed" in str(exc_info.value)
            assert exc_info.value.context.get("indexing_stage") == "batch_processing"

    @pytest.mark.asyncio
    async def test_document_status_tracking(self, indexer, sample_document, sample_sections):
        """Test that document status is properly tracked during indexing."""
        file_path = Path("/test/sample.md")

        # Setup mocks
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        # Mock document methods by patching the class methods
        with (
            patch.object(Document, 'mark_as_processing') as mock_processing,
            patch.object(Document, 'mark_as_indexed') as mock_indexed,
        ):

            await indexer.index_document(file_path)

            # Verify status tracking
            mock_processing.assert_called_once()
            mock_indexed.assert_called_once()

    @pytest.mark.asyncio
    async def test_document_failure_tracking(self, indexer, sample_document):
        """Test that document failure status is tracked on errors."""
        file_path = Path("/test/sample.md")

        # Setup document and chunker to fail
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.side_effect = Exception("Chunking error")

        # Mock document methods by patching the class methods
        with (
            patch.object(Document, 'mark_as_processing') as _,
            patch.object(Document, 'mark_as_failed') as mock_failed,
        ):

            with pytest.raises(IndexingError):
                await indexer.index_document(file_path)

            # Verify failure tracking
            mock_failed.assert_called_once_with("Chunking error")

    @pytest.mark.asyncio
    async def test_hash_check_error_continues_indexing(self, indexer, sample_document, sample_sections):
        """Test that hash check errors don't prevent indexing."""
        file_path = Path("/test/sample.md")

        # Setup hash check to fail but indexing to succeed
        indexer.vector_store.get_document_by_hash.side_effect = Exception("Hash check error")
        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        result = await indexer.index_document(file_path)

        # Should continue with indexing despite hash check error
        assert result["status"] == "success"
        indexer.chunker.chunk_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_word_count_calculation(self, indexer, sample_document, sample_sections):
        """Test word count calculation in indexing results."""
        file_path = Path("/test/sample.md")

        # Setup document with specific content (exactly 8 words)
        sample_document._raw_content = "This is a test document with exactly eight"

        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = sample_sections
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 3}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": True}

        result = await indexer.index_document(file_path)

        assert result["word_count"] == 8

    @pytest.mark.asyncio
    async def test_empty_content_word_count(self, indexer, sample_document, sample_sections):
        """Test word count with empty content."""
        file_path = Path("/test/sample.md")

        # Setup document with empty content
        sample_document._raw_content = ""

        indexer.document_parser.parse_file.return_value = sample_document
        indexer.chunker.chunk_document.return_value = []  # No sections for empty content
        indexer.chunker.get_chunking_stats.return_value = {"total_sections": 0}
        indexer.metadata_enhancer.get_enhancement_stats.return_value = {"has_frontmatter": False}

        result = await indexer.index_document(file_path)

        # The early return for no sections doesn't include word_count field
        assert result["sections_created"] == 0
        assert result["message"] == "No content to index"
        assert "word_count" not in result
