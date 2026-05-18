"""
Embedding providers and adapters.

This module provides embedding generation functionality including
HuggingFace embedders and LangChain compatibility adapters.
"""

from markdown_rag_mcp.embeddings.embedder import HuggingFaceEmbedder
from markdown_rag_mcp.embeddings.langchain_adapter import LangChainEmbeddingAdapter

__all__ = [
    "HuggingFaceEmbedder",
    "LangChainEmbeddingAdapter",
]
