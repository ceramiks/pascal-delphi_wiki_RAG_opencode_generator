"""
Indexing package for document processing and embedding generation.

This package handles the complete document indexing pipeline including:
- Document chunking with metadata enhancement
- Frontmatter metadata integration
- Embedding generation coordination
- Vector storage orchestration
"""

from markdown_rag_mcp.embeddings import HuggingFaceEmbedder, LangChainEmbeddingAdapter
from markdown_rag_mcp.indexing.change_detector import DocumentChangeDetector
from markdown_rag_mcp.indexing.chunker import DocumentChunker
from markdown_rag_mcp.indexing.incremental_indexer import IncrementalIndexer
from markdown_rag_mcp.indexing.indexer import DocumentIndexer
from markdown_rag_mcp.indexing.metadata_enhancer import MetadataEnhancer

__all__ = [
    "DocumentChangeDetector",
    "DocumentChunker",
    "HuggingFaceEmbedder",
    "IncrementalIndexer",
    "DocumentIndexer",
    "LangChainEmbeddingAdapter",
    "MetadataEnhancer",
]
