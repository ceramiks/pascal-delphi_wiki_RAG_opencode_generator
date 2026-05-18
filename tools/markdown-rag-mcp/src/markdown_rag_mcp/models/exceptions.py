"""
Custom exception classes for the Markdown RAG system.

Provides specific exception types for different error scenarios to enable
proper error handling and debugging throughout the system.
"""

from typing import Any


class BaseError(Exception):
    """
    Base exception class for all Markdown RAG system errors.

    All custom exceptions in the system should inherit from this base class
    to enable consistent error handling and logging.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        """
        Initialize the RAG error.

        Args:
            message: Human-readable error description
            error_code: Optional error code for programmatic handling
            context: Optional dictionary with error context information
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        """String representation including error code if present."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"context={self.context})"
        )


class ConfigurationError(BaseError):
    """Raised when there are configuration or settings issues."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        expected_type: str | None = None,
        actual_value: Any | None = None,
    ):
        context = {}
        if config_key:
            context["config_key"] = config_key
        if expected_type:
            context["expected_type"] = expected_type
        if actual_value is not None:
            context["actual_value"] = str(actual_value)

        super().__init__(message, error_code="CONFIG_ERROR", context=context)


class MilvusConnectionError(BaseError):
    """Raised when Milvus vector database connection or operation fails."""

    def __init__(
        self,
        message: str,
        host: str | None = None,
        port: int | None = None,
        operation: str | None = None,
        milvus_error: Exception | None = None,
    ):
        context = {}
        if host:
            context["host"] = host
        if port:
            context["port"] = port
        if operation:
            context["operation"] = operation

        super().__init__(message, error_code="MILVUS_ERROR", context=context, cause=milvus_error)


class EmbeddingModelError(BaseError):
    """Raised when embedding model loading or inference fails."""

    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        model_path: str | None = None,
        operation: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if model_name:
            context["model_name"] = model_name
        if model_path:
            context["model_path"] = model_path
        if operation:
            context["operation"] = operation

        super().__init__(
            message,
            error_code="EMBEDDING_ERROR",
            context=context,
            cause=underlying_error,
        )


class DocumentParsingError(BaseError):
    """Raised when document parsing fails."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line_number: int | None = None,
        parsing_stage: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if file_path:
            context["file_path"] = file_path
        if line_number:
            context["line_number"] = line_number
        if parsing_stage:
            context["parsing_stage"] = parsing_stage

        super().__init__(message, error_code="PARSING_ERROR", context=context, cause=underlying_error)


class ParsingError(BaseError):
    """Raised when general parsing operations fail."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        operation: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if file_path:
            context["file_path"] = file_path
        if operation:
            context["operation"] = operation

        super().__init__(message, error_code="PARSING_ERROR", context=context, cause=underlying_error)


class ChunkingError(BaseError):
    """Raised when document chunking operations fail."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        operation: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if file_path:
            context["file_path"] = file_path
        if operation:
            context["operation"] = operation

        super().__init__(message, error_code="CHUNKING_ERROR", context=context, cause=underlying_error)


class IndexingError(BaseError):
    """Raised when document indexing process fails."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        stage: str | None = None,
        documents_processed: int | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if file_path:
            context["file_path"] = file_path
        if stage:
            context["indexing_stage"] = stage
        if documents_processed is not None:
            context["documents_processed"] = documents_processed

        super().__init__(
            message,
            error_code="INDEXING_ERROR",
            context=context,
            cause=underlying_error,
        )


class SearchError(BaseError):
    """Raised when search operation fails."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        search_stage: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if query:
            context["query"] = query
        if search_stage:
            context["search_stage"] = search_stage

        super().__init__(message, error_code="SEARCH_ERROR", context=context, cause=underlying_error)


class VectorStoreError(BaseError):
    """Raised when vector store operations fail."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        collection_name: str | None = None,
        record_count: int | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if operation:
            context["operation"] = operation
        if collection_name:
            context["collection_name"] = collection_name
        if record_count is not None:
            context["record_count"] = record_count

        super().__init__(
            message,
            error_code="VECTOR_STORE_ERROR",
            context=context,
            cause=underlying_error,
        )


class MonitoringError(BaseError):
    """Raised when file monitoring operations fail."""

    def __init__(
        self,
        message: str,
        path: str | None = None,
        operation: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if path:
            context["path"] = path
        if operation:
            context["operation"] = operation

        super().__init__(
            message,
            error_code="MONITORING_ERROR",
            context=context,
            cause=underlying_error,
        )


class ValidationError(BaseError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        expected_value: str | None = None,
        actual_value: Any | None = None,
        validation_rule: str | None = None,
    ):
        context = {}
        if field_name:
            context["field_name"] = field_name
        if expected_value:
            context["expected_value"] = expected_value
        if actual_value is not None:
            context["actual_value"] = str(actual_value)
        if validation_rule:
            context["validation_rule"] = validation_rule

        super().__init__(message, error_code="VALIDATION_ERROR", context=context)


class InitializationError(BaseError):
    """Raised when system initialization fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        initialization_stage: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if component:
            context["component"] = component
        if initialization_stage:
            context["initialization_stage"] = initialization_stage

        super().__init__(
            message,
            error_code="INITIALIZATION_ERROR",
            context=context,
            cause=underlying_error,
        )


class ShutdownError(BaseError):
    """Raised when system shutdown fails."""

    def __init__(
        self,
        message: str,
        component: str | None = None,
        shutdown_stage: str | None = None,
        underlying_error: Exception | None = None,
    ):
        context = {}
        if component:
            context["component"] = component
        if shutdown_stage:
            context["shutdown_stage"] = shutdown_stage

        super().__init__(
            message,
            error_code="SHUTDOWN_ERROR",
            context=context,
            cause=underlying_error,
        )


# Convenience functions for common error scenarios
def raise_config_error(
    message: str,
    config_key: str,
    expected_type: str | None = None,
    actual_value: Any | None = None,
) -> None:
    """Raise a configuration error with context."""
    raise ConfigurationError(
        message=message,
        config_key=config_key,
        expected_type=expected_type,
        actual_value=actual_value,
    )


def raise_milvus_error(
    message: str,
    operation: str,
    host: str | None = None,
    port: int | None = None,
    underlying_error: Exception | None = None,
) -> None:
    """Raise a Milvus error with context."""
    raise MilvusConnectionError(
        message=message,
        host=host,
        port=port,
        operation=operation,
        milvus_error=underlying_error,
    )


def raise_embedding_error(
    message: str,
    model_name: str,
    operation: str,
    underlying_error: Exception | None = None,
) -> None:
    """Raise an embedding model error with context."""
    raise EmbeddingModelError(
        message=message,
        model_name=model_name,
        operation=operation,
        underlying_error=underlying_error,
    )
