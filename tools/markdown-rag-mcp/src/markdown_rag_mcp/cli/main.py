"""
Main CLI entry point for the Markdown RAG MCP system.

Bundles all CLI commands together and provides the main entry point.
"""

import logging
import sys

import rich_click as click
from rich.console import Console

from markdown_rag_mcp.cli.commands import config, generate_docs, index, search, status

console = Console()

# Configure rich-click for enhanced CLI experience
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.SHOW_METAVARS_COLUMN = False
click.rich_click.APPEND_METAVARS_HELP = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "magenta italic"
click.rich_click.STYLE_SWITCH = "bold green"
click.rich_click.STYLE_OPTION = "bold cyan"
click.rich_click.STYLE_ARGUMENT = "bold yellow"
click.rich_click.STYLE_COMMAND = "bold blue"
click.rich_click.STYLE_HELPTEXT = "dim"


def setup_logging(log_level: str, log_file: str = None):
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file) if log_file else logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)


@click.group(
    name='markdown-rag-mcp',
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
    default='INFO',
    help='Set logging level for system output',
)
@click.option('--log-file', type=click.Path(), help='Log file path (stdout if not specified)')
@click.pass_context
def cli(ctx, log_level, log_file):
    """
    Markdown RAG MCP - Local semantic search for markdown documents

    A CLI for indexing, searching, and monitoring markdown document collections
    using advanced semantic search powered by embeddings and vector databases.

    Features:
    • Semantic Search - Natural language queries across your documents
    • Real-time Monitoring - Automatic index updates on file changes
    • Rich Metadata Support - YAML frontmatter integration
    • Vector Storage - Efficient similarity search with Milvus

    Quick Start:
    ```
    # Index your markdown files
    markdown-rag-mcp index /path/to/docs

    # Search with natural language
    markdown-rag-mcp search "how to configure the system"

    # Check system status
    markdown-rag-mcp status
    ```
    """
    ctx.ensure_object(dict)
    ctx.obj['log_level'] = log_level
    ctx.obj['log_file'] = log_file

    setup_logging(log_level, log_file)


# Add all the commands to the main CLI group
cli.add_command(index)
cli.add_command(search)
cli.add_command(status)
cli.add_command(config)
cli.add_command(generate_docs)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚡ Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error:[/red] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
