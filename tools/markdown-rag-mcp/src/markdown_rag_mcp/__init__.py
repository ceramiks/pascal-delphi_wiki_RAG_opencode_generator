"""
Markdown RAG - Local Markdown Retrieval-Augmented Generation System

A modular library for indexing and searching markdown documentation using
semantic similarity with local embeddings and vector storage.

Key Features:
- Local HuggingFace embeddings (no external API dependencies)
- Milvus vector database for fast similarity search
- Frontmatter metadata utilization for enhanced search
- Incremental file monitoring and index updates
- Clean library interfaces for easy integration

Basic Usage:
    ```python
    from markdown_rag_mcp.core import RAGEngine
    from markdown_rag_mcp.config import RAGConfig

    # Initialize with configuration
    config = RAGConfig()
    rag = RAGEngine(config=config)

    # Index documents
    await rag.index_directory("./docs")

    # Search documents
    results = await rag.search("authentication setup", limit=5)
    for result in results:
        print(f"{result.confidence_score:.3f}: {result.section_heading}")
    ```

CLI Usage:
    ```bash
    # Index markdown files
    markdown-rag-mcp index ./docs

    # Search documents
    markdown-rag-mcp search "authentication setup"

    # Enable file monitoring
    markdown-rag-mcp index ./docs --watch
    ```
"""

__version__ = "1.0.0"
__author__ = "Kareem Mohllal"
__email__ = "kareem.mohllal@gmail.com"

# Core exports for library users
from markdown_rag_mcp.config import RAGConfig
from markdown_rag_mcp.core import RAGEngine

__all__ = [
    # Core classes
    "RAGEngine",
    "RAGConfig",
    # Version info
    "__version__",
    "__author__",
    "__email__",
]
