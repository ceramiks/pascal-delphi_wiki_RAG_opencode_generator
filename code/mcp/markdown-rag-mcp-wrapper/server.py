from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("markdown-rag-mcp-wrapper")


DEFAULT_BACKEND_DIR = "D:/Works/учёба/вкр/finalversion/tools/markdown-rag-mcp"
DEFAULT_MAX_SECTION_CHARS = 4000


class WrapperError(RuntimeError):
    """Raised for deterministic wrapper failures."""


_engine: Any | None = None
_engine_lock: asyncio.Lock | None = None


def _default_final_root() -> Path:
    """Return finalversion root based on this file location.

    Expected location:
        finalversion/code/mcp/markdown-rag-mcp-wrapper/server.py
    """
    return Path(__file__).resolve().parents[3]


def _default_debug_log_path() -> str:
    return str(_default_final_root() / "data" / "logs" / "markdown-rag-mcp-wrapper.log")


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value if value else default


def _backend_dir() -> str:
    return _env("MARKDOWN_RAG_BACKEND_DIR", DEFAULT_BACKEND_DIR)


def _debug_log_path() -> str:
    return _env("MARKDOWN_RAG_DEBUG_LOG_PATH", _default_debug_log_path())


def _max_section_chars() -> int:
    raw = _env("MARKDOWN_RAG_MAX_SECTION_CHARS", str(DEFAULT_MAX_SECTION_CHARS))

    try:
        value = int(raw)
    except ValueError as exc:
        raise WrapperError(f"MARKDOWN_RAG_MAX_SECTION_CHARS must be an integer, got: {raw!r}") from exc

    if value <= 0:
        raise WrapperError("MARKDOWN_RAG_MAX_SECTION_CHARS must be > 0")

    return value


def _debug_log(message: str) -> None:
    """Write a diagnostic line to a log file.

    Logging must never break the MCP tool itself.
    """
    try:
        log_path = Path(_debug_log_path())
        log_path.parent.mkdir(parents=True, exist_ok=True)

        line = f"{datetime.now().isoformat(timespec='seconds')} {message}\n"
        with log_path.open("a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass


@contextlib.contextmanager
def _capture_backend_output(label: str):
    """Redirect noisy backend stdout/stderr away from MCP stdio.

    MCP stdio uses stdout for protocol messages. Any logs/progress bars printed
    by markdown-rag-mcp, sentence-transformers, tqdm, rich, etc. can corrupt the
    MCP JSON-RPC stream. Therefore backend output must go to a log file.
    """
    log_path = Path(_debug_log_path())
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8", errors="replace") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} capture start: {label}\n")
        f.flush()

        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            try:
                yield
            finally:
                f.write(f"{datetime.now().isoformat(timespec='seconds')} capture end: {label}\n")
                f.flush()


def _validate_backend_paths() -> None:
    backend = Path(_backend_dir())

    if not backend.exists():
        raise WrapperError(f"Backend directory does not exist: {backend}")

    if not (backend / "pyproject.toml").exists():
        raise WrapperError(f"Backend directory does not look like markdown-rag-mcp: {backend}")

    if not (backend / "src" / "markdown_rag_mcp").exists():
        raise WrapperError(f"Backend src package not found: {backend / 'src' / 'markdown_rag_mcp'}")


def _ensure_backend_import_path() -> None:
    """Add backend src to sys.path as a fallback.

    Preferred runtime mode:
        uv --directory <MARKDOWN_RAG_BACKEND_DIR> run python <wrapper/server.py>

    In that mode markdown_rag_mcp is already installed in the backend venv.
    """
    backend_src = str(Path(_backend_dir()) / "src")

    if backend_src not in sys.path:
        sys.path.insert(0, backend_src)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text

    return text[: max_chars - 20].rstrip() + "\n... [truncated]"


def _compact_result(result: Any, max_chars: int) -> dict[str, Any]:
    metadata = getattr(result, "metadata", None)

    if not isinstance(metadata, dict):
        metadata = {}

    section_text = str(getattr(result, "section_text", "") or "")

    return {
        "confidence_score": getattr(result, "confidence_score", None),
        "section_heading": getattr(result, "section_heading", None),
        "section_text": _truncate(section_text, max_chars),
        "file_path": getattr(result, "file_path", None),
        "metadata": {
            "document_id": metadata.get("document_id"),
            "section_id": metadata.get("section_id"),
            "section_heading": metadata.get("section_heading"),
            "chunk_index": metadata.get("chunk_index"),
            "start_position": metadata.get("start_position"),
            "end_position": metadata.get("end_position"),
            "token_count": metadata.get("token_count"),
        },
    }


async def _get_engine() -> Any:
    """Initialize and cache RAGEngine inside the MCP process."""
    global _engine, _engine_lock

    _debug_log("_get_engine enter")

    if _engine_lock is None:
        _debug_log("_get_engine create lock")
        _engine_lock = asyncio.Lock()

    _debug_log("_get_engine before lock")

    async with _engine_lock:
        _debug_log("_get_engine after lock")

        if _engine is not None:
            _debug_log("_get_engine cached engine hit")
            return _engine

        _debug_log("_get_engine validate backend paths start")
        _validate_backend_paths()
        _debug_log("_get_engine validate backend paths success")

        _debug_log("_get_engine ensure backend import path start")
        _ensure_backend_import_path()
        _debug_log("_get_engine ensure backend import path success")

        try:
            _debug_log("_get_engine import markdown_rag_mcp.config start")
            from markdown_rag_mcp.config import get_config
            _debug_log("_get_engine import markdown_rag_mcp.config success")

            _debug_log("_get_engine import markdown_rag_mcp.core start")
            from markdown_rag_mcp.core import RAGEngine
            _debug_log("_get_engine import markdown_rag_mcp.core success")

        except Exception as exc:
            _debug_log(f"_get_engine import failed {type(exc).__name__}: {exc}")
            raise WrapperError(
                "Failed to import markdown_rag_mcp. "
                "Run wrapper through the markdown-rag-mcp backend environment. "
                f"Original error: {type(exc).__name__}: {exc}"
            ) from exc

        try:
            _debug_log("RAGEngine initialization start")

            _debug_log("get_config start")
            config = get_config()
            _debug_log("get_config success")

            _debug_log("RAGEngine constructor start")
            engine = RAGEngine(config)
            _debug_log("RAGEngine constructor success")

            _debug_log("engine.initialize start")
            await engine.initialize()
            _debug_log("engine.initialize success")

            _engine = engine
            _debug_log("RAGEngine initialization success")

            return _engine

        except Exception as exc:
            _engine = None
            _debug_log(f"RAGEngine initialization failed {type(exc).__name__}: {exc}")
            raise WrapperError(f"Failed to initialize RAGEngine: {type(exc).__name__}: {exc}") from exc


async def _shutdown_engine() -> None:
    global _engine

    if _engine is None:
        return

    try:
        _debug_log("RAGEngine shutdown start")

        with _capture_backend_output("shutdown"):
            await _engine.shutdown()

        _debug_log("RAGEngine shutdown success")

    finally:
        _engine = None

@mcp.tool()
async def markdown_rag_warmup() -> dict[str, Any]:
    """Initialize backend imports and cached RAGEngine before real search."""
    try:
        _debug_log("warmup start")

        with _capture_backend_output("warmup"):
            engine = await _get_engine()

        _debug_log("warmup success")

        return {
            "status": "success",
            "message": "RAGEngine is initialized",
            "engine_cached": engine is not None,
        }

    except Exception as exc:
        _debug_log(f"warmup error {type(exc).__name__}: {exc}")

        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

@mcp.tool()
async def markdown_rag_search(
    query: str,
    limit: int = 5,
    threshold: float = 0.1,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """Search the indexed Markdown wiki through markdown-rag-mcp Python API.

    The wiki must be indexed beforehand by the build/orchestration pipeline.
    This tool is intentionally read-only.
    """
    if not query.strip():
        return {
            "status": "error",
            "error": "query must not be empty",
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }

    if limit <= 0:
        return {
            "status": "error",
            "error": "limit must be > 0",
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }

    if threshold < 0.0 or threshold > 1.0:
        return {
            "status": "error",
            "error": "threshold must be in range [0.0, 1.0]",
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }

    try:
        _debug_log(f"search start query={query!r} limit={limit} threshold={threshold}")

        with _capture_backend_output("search"):
            _debug_log("search before _get_engine")
            engine = await _get_engine()
            _debug_log("search after _get_engine")

            _debug_log("search before engine.search")
            results_raw = await engine.search(
                query=query,
                limit=limit,
                similarity_threshold=threshold,
                include_metadata=include_metadata,
            )
            _debug_log("search after engine.search")

        max_chars = _max_section_chars()
        results = [_compact_result(item, max_chars) for item in results_raw]

        _debug_log(f"search success query={query!r} result_count={len(results)}")

        return {
            "status": "success",
            "query": query,
            "limit": limit,
            "threshold": threshold,
            "result_count": len(results),
            "results": results,
        }

    except Exception as exc:
        _debug_log(f"search error {type(exc).__name__}: {exc}")

        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "query": query,
            "limit": limit,
            "threshold": threshold,
        }


@mcp.tool()
async def markdown_rag_reload_engine() -> dict[str, Any]:
    """Shutdown cached RAGEngine so the next search reinitializes it."""
    try:
        _debug_log("reload_engine start")
        await _shutdown_engine()
        _debug_log("reload_engine success")

        return {
            "status": "success",
            "message": "RAGEngine cache cleared",
        }

    except Exception as exc:
        _debug_log(f"reload_engine error {type(exc).__name__}: {exc}")

        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


@mcp.tool()
def markdown_rag_ping() -> dict[str, Any]:
    """Fast diagnostic tool to verify OpenCode can call this MCP server."""
    _debug_log("ping")

    return {
        "status": "success",
        "message": "markdown-rag-mcp-wrapper is reachable",
    }


if __name__ == "__main__":
    mcp.run()