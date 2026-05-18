"""
Configuration management for the Markdown RAG MCP system.

Handles environment variables, configuration file loading, and provides
default settings with validation for all system components.
"""

import fnmatch
import os
from enum import Enum
from pathlib import Path
from typing import Any

import torch
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from markdown_rag_mcp.models import ConfigurationError


class LogLevel(str, Enum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EmbeddingDevice(str, Enum):
    """Device options for embedding model inference."""

    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Metal Performance Shaders
    AUTO = "auto"  # Automatically detect best available


class RAGConfig(BaseSettings):
    """
    Central configuration class for the Markdown RAG MCP system.

    Handles all configuration options with environment variable support,
    validation, and sensible defaults for development and production use.
    """

    model_config = SettingsConfigDict(
        env_prefix="MARKDOWN_RAG_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        use_enum_values=True,
    )

    # === Milvus Vector Database Configuration ===
    milvus_host: str = Field(default="localhost", description="Milvus server hostname or IP address")
    milvus_port: int = Field(default=19530, ge=1, le=65535, description="Milvus server port")
    milvus_user: str | None = Field(default=None, description="Milvus username (if authentication enabled)")
    milvus_password: str | None = Field(default=None, description="Milvus password (if authentication enabled)")
    milvus_db_name: str = Field(default="markdown_rag", description="Milvus database name")
    milvus_collection_prefix: str = Field(default="markdown_rag_mcp", description="Prefix for Milvus collection names")
    milvus_connection_timeout: int = Field(default=30, ge=5, le=300, description="Connection timeout in seconds")
    milvus_metric_type: str = Field(default="COSINE", description="Milvus distance metric type (COSINE, L2, IP)")

    # === Embedding Model Configuration ===
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", description="HuggingFace model identifier for embeddings"
    )
    embedding_device: EmbeddingDevice = Field(
        default=EmbeddingDevice.AUTO, description="Device for embedding model inference"
    )
    embedding_batch_size: int = Field(default=32, ge=1, le=256, description="Batch size for embedding generation")
    embedding_max_length: int = Field(default=512, ge=128, le=2048, description="Maximum token length for embeddings")
    embedding_cache_dir: Path | None = Field(default=None, description="Directory for caching embedding models")

    # === Document Processing Configuration ===
    default_documents_dir: Path = Field(
        default=Path("./documents"), description="Default directory containing markdown documents"
    )
    chunk_size_limit: int = Field(default=1000, ge=100, le=4000, description="Maximum tokens per document chunk")
    chunk_overlap: int = Field(default=50, ge=0, le=200, description="Token overlap between chunks")
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity score for search results"
    )
    max_file_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum file size to process (MB)")
    supported_file_extensions: list[str] = Field(
        default=[".md", ".markdown", ".txt"], description="File extensions to process"
    )

    # === Search Configuration ===
    default_search_limit: int = Field(
        default=10, ge=1, le=100, description="Default number of search results to return"
    )
    max_search_limit: int = Field(default=100, ge=1, le=1000, description="Maximum allowed search result limit")
    search_timeout_seconds: int = Field(default=30, ge=5, le=300, description="Search operation timeout")

    # === File Monitoring Configuration ===
    monitoring_enabled: bool = Field(default=True, description="Enable file system monitoring for incremental updates")
    monitoring_debounce_seconds: float = Field(
        default=2.0, ge=0.1, le=30.0, description="Debounce time for file change events"
    )
    monitoring_ignored_patterns: list[str] = Field(
        default=["*.tmp", "*.swp", ".git/*", ".DS_Store"], description="File patterns to ignore during monitoring"
    )

    # === Performance Configuration ===
    max_concurrent_embeddings: int = Field(
        default=4, ge=1, le=16, description="Maximum concurrent embedding operations"
    )
    max_concurrent_indexing: int = Field(
        default=2, ge=1, le=8, description="Maximum concurrent file indexing operations"
    )
    connection_pool_size: int = Field(default=10, ge=1, le=50, description="Milvus connection pool size")

    # === Logging Configuration ===
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_file: Path | None = Field(default=None, description="Log file path (stdout if None)")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log message format"
    )

    # === Development Configuration ===
    debug_mode: bool = Field(default=False, description="Enable debug mode with verbose logging")
    profile_performance: bool = Field(default=False, description="Enable performance profiling")
    validate_schemas: bool = Field(default=True, description="Enable strict data model validation")

    @field_validator('default_documents_dir', mode='before')
    @classmethod
    def validate_default_documents_dir(cls, v):
        """Ensure default_documents_dir is a Path object."""
        if v is None:
            return Path("./documents")
        return Path(v)

    @field_validator('embedding_cache_dir', mode='before')
    @classmethod
    def validate_embedding_cache_dir(cls, v):
        """Set default cache directory if not provided."""
        if v is None:
            # Use user cache directory by default
            cache_home = os.environ.get('XDG_CACHE_HOME')
            if cache_home:
                return Path(cache_home) / "markdown_rag_mcp" / "models"
            else:
                return Path.home() / ".cache" / "markdown_rag_mcp" / "models"
        return Path(v)

    @field_validator('supported_file_extensions')
    @classmethod
    def validate_file_extensions(cls, v):
        """Ensure file extensions start with dot."""
        validated = []
        for ext in v:
            if not ext.startswith('.'):
                ext = f'.{ext}'
            validated.append(ext.lower())
        return validated

    @model_validator(mode='after')
    def validate_chunk_settings(self):
        """Ensure chunk overlap is less than chunk size limit."""
        if self.chunk_overlap >= self.chunk_size_limit:
            raise ConfigurationError(
                "chunk_overlap must be less than chunk_size_limit",
                config_key="chunk_overlap",
                expected_type="int < chunk_size_limit",
                actual_value=self.chunk_overlap,
            )
        return self

    @model_validator(mode='after')
    def validate_search_limits(self):
        """Ensure default search limit doesn't exceed maximum."""
        if self.default_search_limit > self.max_search_limit:
            raise ConfigurationError(
                "default_search_limit cannot exceed max_search_limit",
                config_key="default_search_limit",
                expected_type="int <= max_search_limit",
                actual_value=self.default_search_limit,
            )
        return self

    def get_milvus_connection_params(self) -> dict[str, Any]:
        """Get Milvus connection parameters as dictionary."""
        params = {
            "host": self.milvus_host,
            "port": self.milvus_port,
            "db_name": self.milvus_db_name,
            "timeout": self.milvus_connection_timeout,
        }

        if self.milvus_user:
            params["user"] = self.milvus_user
        if self.milvus_password:
            params["password"] = self.milvus_password

        return params

    def get_collection_names(self) -> dict[str, str]:
        """Get full collection names with prefix."""
        prefix = self.milvus_collection_prefix
        return {"document_vectors": f"{prefix}_document_vectors", "document_metadata": f"{prefix}_document_metadata"}

    def resolve_embedding_device(self) -> str:
        """Resolve the actual device to use for embedding inference."""
        if self.embedding_device == EmbeddingDevice.AUTO:
            # Auto-detect best available device
            try:
                if torch.cuda.is_available():
                    return "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return "mps"
            except ImportError:
                pass
            return "cpu"
        return self.embedding_device.value

    def is_file_supported(self, file_path: str | Path) -> bool:
        """Check if a file type is supported for processing."""
        extension = Path(file_path).suffix.lower()
        return extension in self.supported_file_extensions

    def should_ignore_file(self, file_path: str | Path) -> bool:
        """Check if a file should be ignored based on patterns."""

        path_str = str(file_path)
        return any(fnmatch.fnmatch(path_str, pattern) for pattern in self.monitoring_ignored_patterns)

    def get_log_config(self) -> dict[str, Any]:
        """Get logging configuration dictionary."""
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"standard": {"format": self.log_format}},
            "handlers": {
                "default": {
                    "level": self.log_level.value,
                    "formatter": "standard",
                    "class": "logging.StreamHandler" if not self.log_file else "logging.FileHandler",
                }
            },
            "loggers": {
                "markdown_rag_mcp": {"handlers": ["default"], "level": self.log_level.value, "propagate": False}
            },
        }

        if self.log_file:
            config["handlers"]["default"]["filename"] = str(self.log_file)

        return config


# Global configuration instance
_config: RAGConfig | None = None


def get_config() -> RAGConfig:
    """
    Get the global configuration instance.

    Creates a new instance on first call and reuses it for subsequent calls.
    This ensures consistent configuration across the entire application.
    """
    global _config
    if _config is None:
        _config = RAGConfig()
    return _config


def reload_config() -> RAGConfig:
    """
    Force reload the configuration from environment/files.

    Useful for testing or when configuration needs to be updated at runtime.
    """
    global _config
    _config = RAGConfig()
    return _config


def set_config(config: RAGConfig) -> None:
    """
    Set a custom configuration instance.

    Primarily used for testing or advanced configuration scenarios.
    """
    global _config
    _config = config
