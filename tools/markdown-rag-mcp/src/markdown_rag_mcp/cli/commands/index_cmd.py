"""
Index command implementation for the Markdown RAG MCP CLI.

Processes markdown documents and creates searchable vector embeddings.
"""

import asyncio
import json
import sys
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from markdown_rag_mcp.config import get_config
from markdown_rag_mcp.core import RAGEngine
from markdown_rag_mcp.models import BaseError

console = Console()


@click.command()
@click.option(
    '--index-dir',
    help='Directory to index (uses config default if not specified)',
    type=click.Path(exists=True, path_type=Path),
    default=None,
)
@click.option('--recursive/--no-recursive', default=True, help='Search subdirectories recursively')
@click.option('--force', is_flag=True, help='Force re-indexing of existing files')
@click.option('--watch', is_flag=True, help='Start monitoring for file changes after indexing')
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['json', 'human']),
    default='human',
    help='Output format for results',
)
@click.pass_context
def index(_ctx, index_dir, recursive, force, watch, output_format):
    """
    Index markdown files in a directory

    Processes markdown documents and creates searchable vector embeddings.
    Supports YAML frontmatter extraction and incremental indexing. Uses the
    default documents directory from config if no directory is specified.

    Examples:
    ```
    # Index files in default documents directory
    markdown-rag-mcp index

    # Index all markdown files recursively from specific directory
    markdown-rag-mcp index /path/to/docs

    # Force re-index and start monitoring
    markdown-rag-mcp index /path/to/docs --force --watch
    ```
    """

    async def _index():
        config = get_config()

        # Use default documents directory if none provided
        target_directory = index_dir if index_dir is not None else config.default_documents_dir

        # Ensure the directory exists
        if not target_directory.exists():
            console.print(f"[red]❌ Error:[/red] Index directory {target_directory} does not exist")
            sys.exit(1)

        engine = RAGEngine(config)

        # Show indexing start panel
        start_panel = Panel.fit(
            f"📁 [bold cyan]{target_directory}[/bold cyan]\n"
            f"🔄 Recursive: [yellow]{'Yes' if recursive else 'No'}[/yellow]\n"
            f"⚡ Force: [yellow]{'Yes' if force else 'No'}[/yellow]\n"
            f"👀 Watch: [yellow]{'Yes' if watch else 'No'}[/yellow]",
            title="🚀 Indexing Configuration",
            border_style="blue",
        )
        console.print(start_panel)

        try:
            # Initialize with progress
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                init_task = progress.add_task("Initializing RAG engine...", total=None)
                await engine.initialize()
                progress.update(init_task, completed=True)

            console.print("[green]✅ Engine initialized[/green] - Starting indexing process")

            # Perform indexing with progress indication
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn()
            ) as progress:
                index_task = progress.add_task("Indexing documents...", total=None)
                result = await engine.index_directory(
                    directory_path=target_directory, recursive=recursive, force_reindex=force
                )
                progress.update(index_task, completed=True)

            if output_format == 'json':
                click.echo(json.dumps(result, indent=2))
            else:
                # Create rich results table
                results_table = Table(title="📊 Indexing Results", show_header=True)
                results_table.add_column("Metric", style="cyan", width=20)
                results_table.add_column("Value", style="white", width=15)
                results_table.add_column("Status", style="dim", width=15)

                # Status indicator
                status_icon = "✅" if result["status"] == "success" else "❌"
                results_table.add_row("Status", result["status"].title(), status_icon)
                results_table.add_row("Files Indexed", str(result.get('indexed_files', 0)), "📝")
                results_table.add_row(
                    "Files Failed",
                    str(result.get('failed_files', 0)),
                    "❌" if result.get('failed_files', 0) > 0 else "✅",
                )
                processing_time = result.get('processing_time', 0)
                try:
                    processing_time = float(processing_time)
                    time_str = f"{processing_time:.2f}s"
                except (ValueError, TypeError):
                    time_str = str(processing_time) if processing_time else "0.00s"
                results_table.add_row("Processing Time", time_str, "⏱️")

                console.print(results_table)

                # Show errors if any
                if result.get('errors'):
                    error_panel = Panel(
                        "\n".join(f"• {error}" for error in result['errors']),
                        title="❌ Errors Encountered",
                        border_style="red",
                    )
                    console.print(error_panel)

            # Start monitoring if requested
            if watch:
                monitor_panel = Panel.fit(
                    "[bold yellow]File monitoring started[/bold yellow]\n"
                    "[dim]The system will automatically detect and index file changes.\n"
                    "Press Ctrl+C to stop monitoring.[/dim]",
                    title="👀 Monitoring Active",
                    border_style="yellow",
                )
                console.print(monitor_panel)

                await engine.start_monitoring(target_directory, recursive=recursive)

                try:
                    # Keep monitoring until interrupted
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow]⚡ Stopping file monitoring...[/yellow]")
                    await engine.stop_monitoring()
                    console.print("[green]✅ Monitoring stopped[/green]")

        except BaseError as e:
            click.echo(f"[red]❌ Error:[/red] {e}", err=True)
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]⚡ Operation cancelled[/yellow]")
        finally:
            await engine.shutdown()

    asyncio.run(_index())
