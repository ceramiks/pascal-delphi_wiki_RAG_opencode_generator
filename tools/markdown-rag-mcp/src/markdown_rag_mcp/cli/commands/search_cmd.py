"""
Search command implementation for the Markdown RAG MCP CLI.

Performs semantic search across indexed markdown documents.
"""

import asyncio
import json
import sys
from pathlib import Path

import rich_click as click
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from markdown_rag_mcp.config import get_config
from markdown_rag_mcp.core import RAGEngine
from markdown_rag_mcp.models import BaseError

console = Console()


@click.command()
@click.argument('query')
@click.option('--limit', type=int, default=10, help='Maximum number of results to return')
@click.option('--threshold', type=float, default=0.7, help='Minimum similarity threshold (0.0-1.0)')
@click.option('--include-metadata', is_flag=True, help='Include document metadata in results')
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['json', 'human']),
    default='human',
    help='Output format for results',
)
@click.pass_context
def search(_ctx, query, limit, threshold, include_metadata, output_format):
    """
    Search indexed documents using natural language

    Performs semantic search across your indexed markdown documents
    using advanced vector embeddings and similarity matching.

    Examples:
    ```
    # Basic search
    markdown-rag-mcp search "how to configure the system"

    # Search with custom threshold and metadata
    markdown-rag-mcp search "deployment guide" --threshold 0.5 --include-metadata

    # Get more results with lower threshold
    markdown-rag-mcp search "API reference" --limit 20 --threshold 0.4
    ```
    """

    async def _search():
        config = get_config()
        engine = RAGEngine(config)

        # Show search configuration panel
        search_panel = Panel.fit(
            f"🔍 [bold cyan]Query:[/bold cyan] {query}\n"
            f"📊 [bold yellow]Limit:[/bold yellow] {limit} results\n"
            f"🎯 [bold yellow]Threshold:[/bold yellow] {threshold:.1f}\n"
            f"📝 [bold yellow]Metadata:[/bold yellow] {'Yes' if include_metadata else 'No'}",
            title="🔍 Search Configuration",
            border_style="blue",
        )
        console.print(search_panel)

        try:
            # Initialize with progress
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                init_task = progress.add_task("Initializing search engine...", total=None)
                await engine.initialize()
                progress.update(init_task, completed=True)

            # Perform search with progress
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn()
            ) as progress:
                search_task = progress.add_task("Searching documents...", total=None)
                results = await engine.search(
                    query=query, limit=limit, similarity_threshold=threshold, include_metadata=include_metadata
                )
                progress.update(search_task, completed=True)

            if output_format == 'json':
                # Convert results to serializable format
                results_data = [
                    {
                        'confidence_score': r.confidence_score,
                        'file_path': r.file_path,
                        'section_heading': r.section_heading,
                        'section_text': r.section_text,
                        'metadata': r.metadata if include_metadata else {},
                    }
                    for r in results
                ]
                click.echo(json.dumps({'results': results_data}, indent=2))
            else:
                # Rich human-readable output
                if not results:
                    no_results_panel = Panel.fit(
                        "[yellow]No documents match your search criteria.[/yellow]\n\n"
                        "[dim]Try adjusting your search parameters:[/dim]\n"
                        "• Lower the similarity threshold (--threshold)\n"
                        "• Use different keywords\n"
                        "• Check if documents are properly indexed",
                        title="🔍 No Results Found",
                        border_style="yellow",
                    )
                    console.print(no_results_panel)
                    return

                # Create results header
                header = Text()
                header.append("Found ", style="white")
                header.append(f"{len(results)}", style="bold green")
                header.append(" results", style="white")
                console.print(Align.center(header))
                console.print()

                # Display results in a rich table
                results_table = Table(show_header=True, header_style="bold blue")
                results_table.add_column("#", style="dim", width=3)
                results_table.add_column("File", style="cyan", min_width=20)
                results_table.add_column("Section", style="yellow", min_width=15)
                results_table.add_column("Score", style="green", width=8)
                results_table.add_column("Preview", style="white", min_width=40)

                for i, result in enumerate(results, 1):
                    filename = Path(result.file_path).name
                    section = result.section_heading or "[dim]main[/dim]"
                    score = f"{result.confidence_score:.3f}"

                    # Create preview with truncation
                    preview_text = result.section_text.replace('\n', ' ').strip()
                    if len(preview_text) > 60:
                        preview_text = preview_text[:57] + "..."

                    results_table.add_row(str(i), filename, section, score, preview_text)

                console.print(results_table)

                # Show metadata if requested
                if include_metadata and any(r.metadata for r in results):
                    console.print("\n[bold blue]📝 Document Metadata:[/bold blue]")
                    for i, result in enumerate(results, 1):
                        if result.metadata:
                            meta_table = Table(title=f"Result {i} - {Path(result.file_path).name}", show_header=True)
                            meta_table.add_column("Field", style="cyan")
                            meta_table.add_column("Value", style="white")

                            for key, value in result.metadata.items():
                                # Handle list values
                                if isinstance(value, list):
                                    display_value = ", ".join(str(v) for v in value[:3])
                                    if len(value) > 3:
                                        display_value += f" (+{len(value)-3} more)"
                                else:
                                    display_value = str(value)

                                meta_table.add_row(key, display_value)

                            console.print(meta_table)
                            console.print()

        except BaseError as e:
            click.echo(f"[red]❌ Search error:[/red] {e}", err=True)
            sys.exit(1)
        finally:
            await engine.shutdown()

    asyncio.run(_search())
