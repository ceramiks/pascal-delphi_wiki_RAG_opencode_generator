#!/usr/bin/env python3
"""
Demonstration script for the Markdown RAG monitoring system.

This script shows how to use the monitoring components to automatically
track changes in a directory of markdown files and update the search index.

Usage:
    python examples/file_monitoring_demo.py [--watch-dir PATH] [--duration SECONDS]
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import rich_click as click
from markdown_rag_mcp.monitoring import MonitoringCoordinator
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, track
from rich.table import Table

# Configure rich-click
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize rich console
console = Console()


# Mock classes for demonstration (in real usage, these would be imported)
class MockRAGConfig:
    """Mock RAG configuration for demonstration."""

    def __init__(self):
        self.monitoring_enabled = True
        self.monitoring_debounce_seconds = 2.0
        self.max_concurrent_indexing = 3
        self.supported_extensions = {'.md', '.markdown', '.txt'}
        self.ignored_patterns = {'.*', '_*', 'node_modules/*', '.git/*'}

    def is_file_supported(self, file_path: Path) -> bool:
        """Check if file type is supported."""
        return file_path.suffix.lower() in self.supported_extensions

    def should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        # Simple pattern matching for demo
        name = file_path.name
        return (
            name.startswith('.') or name.startswith('_') or 'node_modules' in str(file_path) or '.git' in str(file_path)
        )


class MockIncrementalIndexer:
    """Mock incremental indexer for demonstration."""

    def __init__(self):
        self.processed_files = []
        self.operations_count = {"created": 0, "modified": 0, "deleted": 0}

    async def update_index_for_directory(self, directory_path: Path, recursive: bool = True) -> dict[str, Any]:
        """Simulate directory indexing."""
        await asyncio.sleep(0.5)  # Simulate processing time

        files_found = []
        if recursive:
            files_found = list(directory_path.rglob("*.md"))
        else:
            files_found = list(directory_path.glob("*.md"))

        console.print(f"📁 Initial directory scan: found [bold green]{len(files_found)}[/bold green] markdown files")

        return {
            "status": "success",
            "changes_detected": len(files_found),
            "files_processed": len(files_found),
            "directory": str(directory_path),
        }

    async def update_single_file(self, file_path: Path, operation: str = 'modified') -> dict[str, Any]:
        """Simulate single file indexing."""
        await asyncio.sleep(0.2)  # Simulate processing time

        self.processed_files.append(str(file_path))
        self.operations_count[operation] += 1

        console.print(f"✅ Processed [cyan]{operation}[/cyan] operation for: [italic]{file_path}[/italic]")

        return {"status": "success", "operation": operation, "file_path": str(file_path), "timestamp": time.time()}


def create_monitoring_stats_table(stats: dict) -> Table:
    """Create a rich table for monitoring statistics."""
    table = Table(title="📊 Real-time Monitoring Statistics", show_header=True)
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="white", width=15)
    table.add_column("Details", style="dim", width=30)

    processing_stats = stats["processing_stats"]
    file_watcher_stats = stats["file_watcher_status"]

    table.add_row("📁 Files Processed", str(processing_stats['files_processed']), "Total indexed files")
    table.add_row("➕ Created", str(processing_stats['operations']['created']), "New files indexed")
    table.add_row("✏️  Modified", str(processing_stats['operations']['modified']), "Updated files")
    table.add_row("🗑️  Deleted", str(processing_stats['operations']['deleted']), "Removed from index")
    table.add_row("⚠️  Failed", str(processing_stats['operations']['failed']), "Processing errors")
    table.add_row("⏳ Pending Events", str(file_watcher_stats['pending_events']), "Queued file changes")

    if processing_stats['errors']:
        table.add_row("🔴 Recent Errors", str(len(processing_stats['errors'])), "See logs for details")

    return table


async def demonstrate_monitoring_system(watch_directory: Path, duration: int = 60):
    """
    Demonstrate the complete monitoring system functionality.

    Args:
        watch_directory: Directory to monitor for changes
        duration: How long to run the demo (in seconds)
    """
    try:
        # Display demo purpose panel
        console.print(
            Panel.fit(
                "🔍 [bold blue]File Monitoring & Automatic Index Updates Demo[/bold blue]\n"
                "This demo showcases the monitoring system capabilities including:\n"
                "• Real-time file change detection (create, modify, delete)\n"
                "• Automatic index synchronization\n"
                "• Debounced event processing to avoid duplicate work\n"
                "• Live statistics and performance monitoring\n"
                "• Manual scan capabilities for on-demand updates\n\n"
                f"📁 Watching: [cyan]{watch_directory}[/cyan] | "
                f"⏱️  Duration: [yellow]{duration}s[/yellow]",
                title="Markdown RAG Monitoring Demo",
                border_style="blue",
            )
        )

        # Create mock dependencies
        config = MockRAGConfig()
        indexer = MockIncrementalIndexer()

        # Initialize the monitoring coordinator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing monitoring coordinator...", total=None)
            coordinator = MonitoringCoordinator(config=config, incremental_indexer=indexer)
            progress.update(task, completed=True)

        # Start monitoring with initial scan
        console.print("\n🔍 [bold yellow]Starting monitoring with initial directory scan...[/bold yellow]")
        await coordinator.start_monitoring(directory_path=watch_directory, recursive=True, initial_scan=True)

        console.print("✅ [bold green]Monitoring started successfully![/bold green]")

        # Display instructions panel
        instructions = Panel(
            f"[bold yellow]Testing Instructions:[/bold yellow]\n\n"
            f"1. Create a new .md file in [cyan]{watch_directory}[/cyan]\n"
            f"2. Modify an existing .md file in [cyan]{watch_directory}[/cyan]\n"
            f"3. Delete a .md file from [cyan]{watch_directory}[/cyan]\n"
            f"4. Watch the live statistics update below!\n\n"
            f"[dim]The system will automatically detect and process changes...[/dim]",
            title="📝 How to Test",
            border_style="yellow",
        )
        console.print(instructions)

        # Monitor for the specified duration with live updates
        start_time = time.time()
        elapsed_time = 0

        with Progress(
            TextColumn("[progress.description]"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:

            monitoring_task = progress.add_task(f"⏱️  Monitoring active (0/{duration}s)", total=duration)

            while elapsed_time < duration:
                await asyncio.sleep(2)  # Check every 2 seconds
                elapsed_time = time.time() - start_time

                # Update progress
                progress.update(
                    monitoring_task,
                    completed=elapsed_time,
                    description=f"⏱️  Monitoring active ({int(elapsed_time)}/{duration}s)",
                )

                # Display stats every 10 seconds
                if int(elapsed_time) % 10 == 0 and elapsed_time > 0:
                    stats = coordinator.get_monitoring_stats()
                    stats_table = create_monitoring_stats_table(stats)
                    console.print(f"\n[bold cyan]Statistics Update - {int(elapsed_time)}s elapsed:[/bold cyan]")
                    console.print(stats_table)

        console.print(f"\n⏰ [bold yellow]Demo time completed ({duration} seconds)[/bold yellow]")

        # Perform a final manual scan
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Performing final manual scan...", total=None)
            scan_result = await coordinator.perform_manual_scan()
            progress.update(task, completed=True)

        # Display scan results in a table
        scan_table = Table(title="🔄 Final Manual Scan Results", show_header=True)
        scan_table.add_column("Metric", style="cyan")
        scan_table.add_column("Value", style="white")

        scan_table.add_row("Status", scan_result.get('status', 'Unknown'))
        scan_table.add_row("Directories Scanned", str(scan_result.get('directories_scanned', 0)))
        scan_table.add_row("Changes Detected", str(scan_result.get('total_changes_detected', 0)))
        scan_table.add_row("Files Processed", str(scan_result.get('total_files_processed', 0)))

        console.print(scan_table)

        # Show final statistics
        final_stats = coordinator.get_monitoring_stats()
        final_table = create_monitoring_stats_table(final_stats)

        console.print("\n[bold green]📈 Final Monitoring Statistics:[/bold green]")
        console.print(final_table)

        # Additional indexer statistics
        indexer_table = Table(title="🔧 Indexer Performance", show_header=True)
        indexer_table.add_column("Metric", style="cyan")
        indexer_table.add_column("Value", style="white")

        indexer_table.add_row("Total Files Processed", str(len(indexer.processed_files)))
        indexer_table.add_row("Create Operations", str(indexer.operations_count['created']))
        indexer_table.add_row("Modify Operations", str(indexer.operations_count['modified']))
        indexer_table.add_row("Delete Operations", str(indexer.operations_count['deleted']))

        console.print(indexer_table)

        # Stop monitoring
        console.print("\n🛑 [yellow]Stopping monitoring...[/yellow]")
        coordinator.stop_monitoring()
        console.print("✅ [bold green]Monitoring stopped successfully![/bold green]")

    except ImportError as e:
        console.print(f"❌ [red]Import error:[/red] {e}")
        console.print("This demo requires the monitoring components to be available.")
        console.print("Make sure you're running from the project root directory.")
    except Exception as e:
        console.print(f"❌ [red]Demo failed:[/red] {e}")
        logger.error("Demo failed: %s", e)
        raise


async def create_sample_files(directory: Path):
    """Create some sample markdown files for testing."""
    directory.mkdir(parents=True, exist_ok=True)

    sample_files = {
        "README.md": """# Sample Project

This is a sample markdown file for testing the monitoring system.

## Features

- Automatic file monitoring
- Real-time index updates
- Debounced event processing
""",
        "docs/getting-started.md": """---
title: Getting Started Guide
tags: [documentation, guide, setup]
topics: [setup, configuration]
summary: Complete guide to get started with the Markdown RAG system
---

# Getting Started

Welcome to the Markdown RAG system! This guide will help you get up and running.

## Installation

Follow these steps to install the system...
""",
        "docs/api-reference.md": """---
title: API Reference
tags: [api, reference, documentation]
topics: [api, methods, functions]
keywords: [search, index, monitor, query]
---

# API Reference

## Search Methods

### semantic_search()
Performs semantic search across indexed documents.

### monitor_directory()
Starts monitoring a directory for file changes.
""",
    }

    console.print("📝 [bold blue]Creating Sample Files[/bold blue]")

    # Create files with progress tracking
    for file_path, content in track(sample_files.items(), description="Creating files..."):
        full_path = directory / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')

    # Display created files in a table
    files_table = Table(title="📁 Created Sample Files", show_header=True)
    files_table.add_column("File", style="cyan")
    files_table.add_column("Location", style="white")
    files_table.add_column("Size", style="dim")

    for file_path in sample_files.keys():
        full_path = directory / file_path
        size = full_path.stat().st_size
        files_table.add_row(full_path.name, str(full_path.parent), f"{size} bytes")

    console.print(files_table)
    console.print(f"✅ [bold green]Created {len(sample_files)} sample markdown files in {directory}[/bold green]")


@click.command()
@click.option(
    '--watch-dir',
    '-d',
    type=click.Path(path_type=Path),
    default=Path('./test_markdown'),
    help='[cyan]Directory to monitor[/cyan] (will be created if it doesn\'t exist)',
)
@click.option('--duration', '-t', type=int, default=60, help='[yellow]Duration to run the demo in seconds[/yellow]')
@click.option('--create-samples', '-s', is_flag=True, help='[green]Create sample markdown files for testing[/green]')
@click.option('--verbose', '-v', is_flag=True, help='[blue]Enable verbose logging[/blue]')
def main(watch_dir: Path, duration: int, create_samples: bool, verbose: bool):
    """
    [bold blue]Run the Markdown RAG monitoring system demonstration[/bold blue]

    [dim]This script demonstrates the automatic file monitoring and indexing
    capabilities of the Markdown RAG system.[/dim]

    [yellow]Features Demonstrated:[/yellow]
    • Set up monitoring on the specified directory
    • Perform an initial scan of existing files
    • Watch for file changes (create, modify, delete)
    • Automatically update the search index
    • Report statistics and progress

    [yellow]Example Usage:[/yellow]
    ```
    # Run with default settings (60 seconds, ./test_markdown directory)
    python examples/file_monitoring_demo.py

    # Monitor a specific directory for 2 minutes
    python examples/file_monitoring_demo.py -d /path/to/docs -t 120

    # Create samples and run with verbose output
    python examples/file_monitoring_demo.py -s -v -t 30
    ```
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(
        Panel.fit(
            "🎯 [bold blue]Markdown RAG Monitoring System Demo[/bold blue]\n\n"
            "This interactive demonstration showcases the real-time file\n"
            "monitoring and automatic indexing capabilities of the system.",
            title="Welcome",
            border_style="blue",
        )
    )

    try:
        if create_samples:
            asyncio.run(create_sample_files(watch_dir))

        # Run the monitoring demonstration
        asyncio.run(demonstrate_monitoring_system(watch_dir, duration))

    except KeyboardInterrupt:
        console.print("\n⚡ [yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"❌ [red]Demo failed:[/red] {e}")
        logger.exception("Full error details:")
        return 1

    console.print("\n🎉 [bold green]Demo completed successfully![/bold green]")
    return 0


if __name__ == '__main__':
    exit(main())
