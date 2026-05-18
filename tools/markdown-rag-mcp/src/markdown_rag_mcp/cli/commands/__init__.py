"""
CLI command modules for the Markdown RAG MCP system.

Each command is implemented in its own module for better organization and maintainability.
"""

from markdown_rag_mcp.cli.commands.config_cmd import config
from markdown_rag_mcp.cli.commands.generate_docs_cmd import generate_docs
from markdown_rag_mcp.cli.commands.index_cmd import index
from markdown_rag_mcp.cli.commands.search_cmd import search
from markdown_rag_mcp.cli.commands.status_cmd import status

__all__ = ['index', 'search', 'status', 'config', 'generate_docs']
