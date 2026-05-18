"""
Status command implementation for the Markdown RAG MCP CLI.

Displays system status and statistics.
"""

import asyncio
import json
import sys

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from markdown_rag_mcp.config import get_config
from markdown_rag_mcp.core import RAGEngine
from markdown_rag_mcp.models import BaseError

console = Console()


@click.command()
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['json', 'human']),
    default='human',
    help='Output format for status information',
)
def status(output_format):
    """
    Show system status and statistics

    Displays comprehensive information about the RAG system including
    database connections, document counts, and monitoring status.

    Example:
    ```
    # Check system status
    markdown-rag-mcp status

    # Get status as JSON
    markdown-rag-mcp status --format json
    ```
    """

    async def _status():
        config = get_config()
        engine = RAGEngine(config)

        try:
            # Initialize with progress
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                init_task = progress.add_task("Checking system status...", total=None)
                await engine.initialize()
                status_info = await engine.get_status()
                progress.update(init_task, completed=True)

            if output_format == 'json':
                click.echo(json.dumps(status_info, indent=2))
            else:
                # Rich human-readable output
                title_panel = Panel.fit("[bold blue]Markdown RAG MCP System Status[/bold blue]", border_style="blue")
                console.print(title_panel)

                # Main status table
                status_table = Table(show_header=True, header_style="bold cyan")
                status_table.add_column("Component", style="white", width=20)
                status_table.add_column("Status", style="white", width=15)
                status_table.add_column("Details", style="dim", min_width=30)

                # Overall status
                overall_status = status_info.get("status", "unknown")
                status_icon = "✅" if overall_status == "ready" else "❌"
                status_table.add_row("System", f"{status_icon} {overall_status.title()}", "Overall system health")

                # Document statistics
                if "total_documents" in status_info:
                    total_docs = status_info.get('total_documents', 0)
                    total_sections = status_info.get('total_sections', 0)
                    status_table.add_row(
                        "Document Index", f"📄 {total_docs} documents", f"{total_sections} sections indexed"
                    )

                # Milvus status
                if "milvus" in status_info:
                    milvus = status_info["milvus"]
                    milvus_connected = milvus.get("connected", False)
                    milvus_icon = "✅" if milvus_connected else "❌"
                    milvus_details = f"Host: {config.milvus_host}:{config.milvus_port}"
                    status_table.add_row(
                        "Vector Database",
                        f"{milvus_icon} {'Connected' if milvus_connected else 'Disconnected'}",
                        milvus_details,
                    )

                # Embedding model
                if "embedding_model" in status_info:
                    model = status_info["embedding_model"]
                    model_name = model.get('model_name', 'Unknown')
                    device = model.get('device', 'Unknown')
                    status_table.add_row("Embedding Model", f"🤖 {model_name}", f"Device: {device}")

                # Monitoring status
                if "monitoring" in status_info:
                    monitoring = status_info["monitoring"]
                    monitoring_active = monitoring.get("active", False)
                    monitoring_icon = "✅" if monitoring_active else "⭕"
                    monitoring_details = "Real-time file monitoring" if monitoring_active else "Not monitoring files"
                    status_table.add_row(
                        "File Monitoring",
                        f"{monitoring_icon} {'Active' if monitoring_active else 'Inactive'}",
                        monitoring_details,
                    )

                console.print(status_table)

                # Additional configuration info
                config_panel = Panel(
                    f"[yellow]Configuration:[/yellow]\n"
                    f"• Similarity threshold: [cyan]{config.similarity_threshold}[/cyan]\n"
                    f"• Chunk size limit: [cyan]{config.chunk_size_limit}[/cyan]\n"
                    f"• Monitoring enabled: [cyan]{'Yes' if config.monitoring_enabled else 'No'}[/cyan]",
                    title="⚙️ Configuration",
                    border_style="yellow",
                )
                console.print(config_panel)

                # System health summary
                health_status = "healthy" if overall_status == "ready" else "degraded"
                health_color = "green" if health_status == "healthy" else "yellow"
                summary_panel = Panel.fit(
                    f"[{health_color}]System is {health_status}[/{health_color}]",
                    title="📊 Health Summary",
                    border_style=health_color,
                )
                console.print(summary_panel)

        except BaseError as e:
            click.echo(f"[red]❌ Status check failed:[/red] {e}", err=True)
            sys.exit(1)
        finally:
            await engine.shutdown()

    asyncio.run(_status())
