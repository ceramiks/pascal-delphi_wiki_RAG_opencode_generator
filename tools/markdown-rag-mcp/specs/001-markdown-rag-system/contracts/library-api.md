# Library API Contract

**Version**: 1.0.0
**Date**: 2025-10-08
**Purpose**: Modular interface for external component integration (MCP servers, APIs)

## Core Library Interface

### RAGEngine Class (Primary Interface)

**Purpose**: Main orchestration class for all RAG operations - designed for easy integration into any external interface

```python
from markdown_rag_mcp.core import RAGEngine, IRAGEngine
from markdown_rag_mcp.models import QueryResult, DocumentInfo, IndexResult
from markdown_rag_mcp.config import RAGConfig
from typing import List, Optional

class RAGEngine(IRAGEngine):
    """Core RAG engine for markdown document processing and search.

    This is the main interface for integrating RAG functionality into
    external applications, servers, or interfaces.
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.7,
        device: str = "auto"
    ):
        """Initialize RAG engine with configuration.

        Args:
            config: Optional configuration object (overrides individual params)
            milvus_host: Milvus server host
            milvus_port: Milvus server port
            embedding_model: HuggingFace model identifier
            similarity_threshold: Minimum similarity score for results
            device: Embedding computation device ("cpu", "cuda", "mps", "auto")
        """
        pass

    async def index_directory(
        self,
        directory_path: str,
        force_reindex: bool = False
    ) -> IndexResult:
        """Index all markdown files in directory."""
        pass

    async def index_file(
        self,
        file_path: str,
        force_reindex: bool = False
    ) -> DocumentInfo:
        """Index a single markdown file."""
        pass

    async def search(
        self,
        query: str,
        limit: int = 10,
        include_metadata: bool = False
    ) -> List[QueryResult]:
        """Search for relevant content."""
        pass

    async def get_document_info(self, file_path: str) -> Optional[DocumentInfo]:
        """Get document processing information."""
        pass

    async def delete_document(self, file_path: str) -> bool:
        """Remove document from index."""
        pass

    async def get_system_status(self) -> SystemStatus:
        """Get system statistics and health."""
        pass
```

### Data Models

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"

class QueryResult(BaseModel):
    """Single search result."""
    section_text: str
    file_path: str
    confidence_score: float
    section_heading: Optional[str] = None
    heading_level: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    chunk_index: int

class DocumentInfo(BaseModel):
    """Document processing information."""
    file_path: str
    processing_status: ProcessingStatus
    file_hash: str
    file_size: int
    section_count: int
    word_count: int
    has_frontmatter: bool
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class IndexResult(BaseModel):
    """Result of directory indexing operation."""
    indexed_files: int
    failed_files: int
    processing_time: float
    errors: List[Dict[str, str]]

class SystemStatus(BaseModel):
    """System health and statistics."""
    database_connected: bool
    total_documents: int
    total_sections: int
    total_embeddings: int
    directory_path: str
    last_scan: Optional[datetime] = None
    avg_query_time: Optional[float] = None
```

### Configuration Management

```python
from pydantic_settings import BaseSettings

class MarkdownRAGConfig(BaseSettings):
    """Configuration settings with environment variable support."""

    # Milvus Vector Database
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection_prefix: str = "markdown_rag_mcp"

    # Local Embedding Model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "auto"  # "cpu", "cuda", "mps", or "auto"
    embedding_batch_size: int = 32

    # Processing
    chunk_size_limit: int = 1000
    similarity_threshold: float = 0.7
    max_file_size_mb: int = 50

    # Directories
    markdown_directory: str = "./documents"
    cache_directory: str = "~/.cache/markdown-rag-mcp"
    model_cache_directory: str = "~/.cache/huggingface"

    class Config:
        env_prefix = "MARKDOWN_RAG_MCP_"
        env_file = ".env"
```

### File Monitoring Interface

```python
from abc import ABC, abstractmethod
from typing import Callable, Protocol

class FileChangeCallback(Protocol):
    """Callback for file system changes."""

    async def __call__(
        self,
        event_type: str,  # "created", "modified", "deleted"
        file_path: str
    ) -> None: ...

class FileMonitor(ABC):
    """Abstract interface for file system monitoring."""

    @abstractmethod
    async def start_monitoring(
        self,
        directory_path: str,
        callback: FileChangeCallback
    ) -> None:
        """Start monitoring directory for changes."""
        pass

    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop file system monitoring."""
        pass
```

### Error Types

```python
class BaseError(Exception):
    """Base exception for all RAG system errors."""
    pass

class MilvusConnectionError(BaseError):
    """Milvus connection or collection errors."""
    pass

class EmbeddingModelError(BaseError):
    """Local embedding model loading or inference errors."""
    pass

class DocumentProcessingError(BaseError):
    """Document parsing or processing errors."""
    pass

class ConfigurationError(BaseError):
    """Invalid configuration or missing settings."""
    pass

class CollectionError(BaseError):
    """Milvus collection creation or management errors."""
    pass
```

## Usage Examples

### Basic Setup and Indexing

```python
import asyncio
from markdown_rag_mcp import MarkdownRAG, MarkdownRAGConfig

async def basic_example():
    # Load configuration
    config = MarkdownRAGConfig()

    # Initialize RAG system
    rag = MarkdownRAG(
        milvus_host=config.milvus_host,
        milvus_port=config.milvus_port,
        embedding_model=config.embedding_model,
        similarity_threshold=config.similarity_threshold,
        device=config.embedding_device
    )

    # Index documents
    result = await rag.index_directory("./documents")
    print(f"Indexed {result.indexed_files} files")

    # Search for content
    results = await rag.search("authentication setup", limit=5)
    for result in results:
        print(f"Score: {result.confidence_score:.2f}")
        print(f"File: {result.file_path}")
        print(f"Section: {result.section_heading}")
        print("---")

# Run example
asyncio.run(basic_example())
```

### Library Extension Pattern

```python
from markdown_rag_mcp.core import RAGEngine, IRAGEngine
from markdown_rag_mcp.models import QueryResult
from typing import List, Dict, Any

class ExtendedRAGEngine:
    """Example of extending core RAG functionality for specific use cases."""

    def __init__(self, core_engine: IRAGEngine):
        """Wrap core engine with additional functionality."""
        self.core = core_engine

    async def search_with_context(
        self,
        query: str,
        include_metadata: bool = True,
        context_window: int = 2
    ) -> Dict[str, Any]:
        """Enhanced search with additional context and formatting."""
        results = await self.core.search(query, limit=10)

        return {
            "query": query,
            "results": [
                {
                    "content": result.section_text,
                    "file": result.file_path,
                    "score": result.confidence_score,
                    "heading": result.section_heading,
                    "metadata": result.metadata if include_metadata else None
                }
                for result in results
            ],
            "total_results": len(results)
        }

    async def batch_process_directories(
        self,
        directories: List[str]
    ) -> Dict[str, IndexResult]:
        """Process multiple directories and return combined results."""
        results = {}
        for directory in directories:
            try:
                result = await self.core.index_directory(directory)
                results[directory] = result
            except Exception as e:
                results[directory] = {"error": str(e)}
        return results
```

### Custom Embedding Provider

```python
from markdown_rag_mcp.embeddings import BaseEmbeddingProvider
from typing import List
import httpx

class CustomEmbeddingProvider(BaseEmbeddingProvider):
    """Custom embedding provider implementation."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.example.com/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"text": text, "model": self.model}
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # Implement batch processing
        pass

# Register custom provider
from markdown_rag_mcp import register_embedding_provider
register_embedding_provider("custom", CustomEmbeddingProvider)
```

### File Monitoring Integration

```python
from markdown_rag_mcp import MarkdownRAG
from markdown_rag_mcp.monitoring import FileMonitor

async def monitoring_example():
    rag = MarkdownRAG(...)
    monitor = FileMonitor()

    async def handle_file_change(event_type: str, file_path: str):
        """Handle file system changes."""
        if event_type == "created" or event_type == "modified":
            if file_path.endswith(".md"):
                await rag.index_file(file_path)
                print(f"Indexed: {file_path}")
        elif event_type == "deleted":
            await rag.delete_document(file_path)
            print(f"Removed: {file_path}")

    # Start monitoring
    await monitor.start_monitoring("./documents", handle_file_change)

    # Keep running
    try:
        await asyncio.Event().wait()
    finally:
        await monitor.stop_monitoring()
```

## Integration Patterns

### Configuration Management Pattern

```python
from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.core import RAGEngine
from pathlib import Path
import os

class ConfiguredRAGEngine:
    """Example of configuration-driven RAG engine setup."""

    @classmethod
    def from_env(cls) -> RAGEngine:
        """Create RAG engine from environment variables."""
        config = RAGConfig()
        return RAGEngine(config=config)

    @classmethod
    def from_config_file(cls, config_path: Path) -> RAGEngine:
        """Create RAG engine from TOML configuration file."""
        # Load config from file
        config = RAGConfig.from_toml(config_path)
        return RAGEngine(config=config)

    @classmethod
    def for_development(cls, markdown_dir: str = "./documents") -> RAGEngine:
        """Create RAG engine with development-friendly defaults."""
        return RAGEngine(
            milvus_host="localhost",
            milvus_port=19530,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",  # Safer default for development
            similarity_threshold=0.6  # Lower threshold for development
        )

# Usage examples
dev_engine = ConfiguredRAGEngine.for_development()
prod_engine = ConfiguredRAGEngine.from_env()
```

### Async Context Manager

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def markdown_rag_session(config: MarkdownRAGConfig):
    """Async context manager for RAG sessions."""
    rag = MarkdownRAG(...)
    try:
        # Ensure database connection
        status = await rag.get_system_status()
        if not status.database_connected:
            raise DatabaseConnectionError("Cannot connect to database")

        yield rag
    finally:
        # Cleanup resources
        await rag.close()

# Usage
async def example():
    config = MarkdownRAGConfig()
    async with markdown_rag_session(config) as rag:
        results = await rag.search("example query")
```

This library API contract provides a clean, modular core interface designed for maximum extensibility.

The library can be easily integrated into future MCP servers, web APIs, or other external interfaces without modification to core functionality, maintaining strict adherence to library-first architectural principles.
