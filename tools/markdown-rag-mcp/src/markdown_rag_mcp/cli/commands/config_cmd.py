"""
Config command implementation for the Markdown RAG MCP CLI.

Shows current configuration settings.
"""

import json

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from markdown_rag_mcp.config import get_config

console = Console()


@click.command()
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['json', 'human']),
    default='human',
    help='Output format for configuration display',
)
def config(output_format):
    """
    Show current configuration settings

    Displays all configuration parameters for the RAG system
    including database connections, model settings, and preferences.

    Example:
    ```
    # Show current configuration
    markdown-rag-mcp config

    # Export configuration as JSON
    markdown-rag-mcp config --format json
    ```
    """
    config_obj = get_config()

    if output_format == 'json':
        config_data = {
            'milvus_host': config_obj.milvus_host,
            'milvus_port': config_obj.milvus_port,
            'embedding_model': config_obj.embedding_model,
            'embedding_device': config_obj.resolve_embedding_device(),
            'default_documents_dir': str(config_obj.default_documents_dir),
            'similarity_threshold': config_obj.similarity_threshold,
            'chunk_size_limit': config_obj.chunk_size_limit,
            'monitoring_enabled': config_obj.monitoring_enabled,
        }
        click.echo(json.dumps(config_data, indent=2))
    else:
        # Rich human-readable output
        title_panel = Panel.fit("[bold blue]Markdown RAG MCP Configuration[/bold blue]", border_style="blue")
        console.print(title_panel)

        # Database Configuration
        db_table = Table(title="🗄️ Database Configuration", show_header=True)
        db_table.add_column("Setting", style="cyan", width=20)
        db_table.add_column("Value", style="white", width=30)
        db_table.add_column("Description", style="dim", min_width=25)

        db_table.add_row("Milvus Host", config_obj.milvus_host, "Vector database host")
        db_table.add_row("Milvus Port", str(config_obj.milvus_port), "Vector database port")
        db_table.add_row("Connection", f"{config_obj.milvus_host}:{config_obj.milvus_port}", "Full connection string")

        console.print(db_table)

        # Model Configuration
        model_table = Table(title="🤖 Embedding Model Configuration", show_header=True)
        model_table.add_column("Setting", style="cyan", width=20)
        model_table.add_column("Value", style="white", width=30)
        model_table.add_column("Description", style="dim", min_width=25)

        model_table.add_row("Model Name", config_obj.embedding_model, "HuggingFace model identifier")
        model_table.add_row("Device", config_obj.resolve_embedding_device(), "Computation device (CPU/GPU)")

        console.print(model_table)

        # Processing Configuration
        proc_table = Table(title="⚙️ Processing Configuration", show_header=True)
        proc_table.add_column("Setting", style="cyan", width=20)
        proc_table.add_column("Value", style="white", width=30)
        proc_table.add_column("Description", style="dim", min_width=25)

        proc_table.add_row(
            "Documents Directory", str(config_obj.default_documents_dir), "Default markdown documents location"
        )
        proc_table.add_row(
            "Similarity Threshold", f"{config_obj.similarity_threshold:.2f}", "Minimum similarity for search results"
        )
        proc_table.add_row(
            "Chunk Size Limit", f"{config_obj.chunk_size_limit:,}", "Maximum characters per document chunk"
        )
        proc_table.add_row(
            "File Monitoring",
            "Enabled" if config_obj.monitoring_enabled else "Disabled",
            "Automatic file change detection",
        )

        console.print(proc_table)

        # Configuration source info
        source_panel = Panel(
            "[yellow]Configuration Source:[/yellow]\n"
            "• Environment variables (highest priority)\n"
            "• Configuration files\n"
            "• Default values (lowest priority)\n\n"
            "[dim]Use environment variables like MILVUS_HOST, EMBEDDING_MODEL, etc. to override settings.[/dim]",
            title="📋 Configuration Management",
            border_style="yellow",
        )
        console.print(source_panel)
