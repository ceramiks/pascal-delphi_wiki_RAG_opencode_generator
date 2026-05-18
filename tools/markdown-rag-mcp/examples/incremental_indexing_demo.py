#!/usr/bin/env python3
"""
Demonstration of incremental indexing functionality.

This script shows how the incremental indexer detects changes in markdown
files and updates the search index accordingly, using content hashing
to detect modifications efficiently.

Usage:
    python examples/incremental_indexing_demo.py [--directory PATH] [--runs NUMBER]
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import rich_click as click
from markdown_rag_mcp.indexing import DocumentChangeDetector, IncrementalIndexer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, track
from rich.table import Table

# Configure rich-click
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize rich console
console = Console()


class MockRAGConfig:
    """Mock configuration for incremental indexing demo."""

    def __init__(self):
        self.supported_extensions = {'.md', '.markdown', '.txt'}
        self.ignored_patterns = {'.*', '_*'}
        self.max_concurrent_indexing = 3
        self.chunk_size_limit = 500
        self.chunk_overlap = 50
        self.monitoring_enabled = True
        self.monitoring_debounce_seconds = 2.0

    def is_file_supported(self, file_path: Path) -> bool:
        """Check if file type is supported."""
        return file_path.suffix.lower() in self.supported_extensions

    def should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        name = file_path.name
        return name.startswith('.') or name.startswith('_')


class MockVectorStore:
    """Mock vector store for demonstration."""

    def __init__(self):
        self.documents = {}
        self.operation_log = []

    async def store_document_sections(self, sections: list, embeddings: list) -> dict[str, Any]:
        """Store document sections with embeddings in mock vector store."""
        await asyncio.sleep(0.1)  # Simulate storage time

        for i, section in enumerate(sections):
            doc_id = f"{section.document_id}#{section.chunk_index}"
            self.documents[doc_id] = {"section": section, "embedding": embeddings[i] if i < len(embeddings) else None}
            self.operation_log.append(f"STORED: {doc_id}")

        console.print(f"📥 Stored [bold green]{len(sections)}[/bold green] document sections")

        return {"status": "success", "documents_stored": len(sections), "total_documents": len(self.documents)}

    async def delete_document(self, file_path: str) -> dict[str, Any]:
        """Remove documents by file path."""
        await asyncio.sleep(0.05)  # Simulate removal time

        removed_docs = []
        for doc_id in list(self.documents.keys()):
            if file_path in str(self.documents[doc_id]["section"].document_id):
                removed_docs.append(self.documents.pop(doc_id))
                self.operation_log.append(f"REMOVED: {doc_id}")

        console.print(
            f"🗑️  Removed [bold red]{len(removed_docs)}[/bold red] document sections for [italic]{file_path}[/italic]"
        )

        return {"status": "success", "documents_removed": len(removed_docs), "total_documents": len(self.documents)}

    def get_stats(self):
        """Get vector store statistics."""
        return {
            "total_documents": len(self.documents),
            "operations_performed": len(self.operation_log),
            "recent_operations": self.operation_log[-10:] if self.operation_log else [],
        }


class MockDocumentIndexer:
    """Mock document indexer for demonstration."""

    def __init__(self, config, vector_store):
        self.config = config
        self.vector_store = vector_store
        self.operation_log = []

    async def index_document(self, file_path: Path, force_reindex: bool = False) -> dict[str, Any]:
        """Mock document indexing."""
        await asyncio.sleep(0.2)  # Simulate processing time

        # Simulate reading and processing file
        if file_path.exists():
            content = file_path.read_text()
            word_count = len(content.split())

            # Create mock sections
            from datetime import datetime

            sections_created = max(1, word_count // 100)  # Roughly 1 section per 100 words

            result = {
                "status": "success",
                "file_path": str(file_path),
                "document_id": f"doc_{hash(str(file_path)) % 10000}",
                "content_hash": f"hash_{hash(content) % 1000000:06x}",
                "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "sections_created": sections_created,
                "word_count": word_count,
                "processing_time": "0.20s",
                "has_frontmatter": content.startswith('---'),
            }

            self.operation_log.append(f"INDEXED: {file_path.name} -> {sections_created} sections")
            console.print(f"📚 Indexed [cyan]{file_path.name}[/cyan]: {sections_created} sections, {word_count} words")

            return result
        else:
            raise FileNotFoundError(f"File not found: {file_path}")

    async def update_document(self, file_path: Path) -> dict[str, Any]:
        """Mock document update."""
        console.print(f"🔄 Updating [cyan]{file_path.name}[/cyan]")

        # First remove, then reindex
        await self.vector_store.delete_document(str(file_path))
        result = await self.index_document(file_path, force_reindex=True)
        result["operation"] = "update"

        self.operation_log.append(f"UPDATED: {file_path.name}")
        return result

    async def remove_document(self, file_path: Path) -> dict[str, Any]:
        """Mock document removal."""
        console.print(f"🗑️  Removing [cyan]{file_path.name}[/cyan]")

        result = await self.vector_store.delete_document(str(file_path))
        result["operation"] = "remove"
        result["file_path"] = str(file_path)

        self.operation_log.append(f"REMOVED: {file_path.name}")
        return result


def create_indexing_results_table(result: dict, run_num: int, elapsed: float) -> Table:
    """Create a rich table for indexing results."""
    table = Table(title=f"📊 Indexing Results - Run {run_num}", show_header=True)
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="white", width=15)
    table.add_column("Description", style="dim", width=30)

    table.add_row("⏱️  Duration", f"{elapsed:.2f}s", "Total processing time")
    table.add_row("📋 Status", result.get('status', 'Unknown'), "Operation outcome")
    table.add_row("📁 Directory", result.get('directory', 'Unknown'), "Target directory")
    table.add_row("🔄 Changes Detected", str(result.get('changes_detected', 0)), "Files with changes")
    table.add_row("⚡ Files Processed", str(result.get('files_processed', 0)), "Files actually indexed")

    if 'operations' in result:
        operations = result['operations']
        table.add_row("", "", "")  # Separator
        table.add_row("➕ Created Files", str(operations.get('created', 0)), "First-time indexing")
        table.add_row("✏️  Modified Files", str(operations.get('modified', 0)), "Updated content")
        table.add_row("🗑️  Deleted Files", str(operations.get('deleted', 0)), "Removed from index")
        table.add_row("❌ Failed Operations", str(operations.get('failed', 0)), "Processing errors")

    if result.get('errors'):
        table.add_row("🚨 Errors", str(len(result['errors'])), "Number of errors")

    return table


def create_vector_store_stats_table(stats: dict) -> Table:
    """Create a rich table for vector store statistics."""
    table = Table(title="📦 Vector Store Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("📄 Total Documents", str(stats['total_documents']))
    table.add_row("🔧 Operations Performed", str(stats['operations_performed']))

    if stats['recent_operations']:
        table.add_row("🕒 Recent Operations", f"{len(stats['recent_operations'])} recent")

    return table


async def demonstrate_incremental_indexing(directory: Path, num_runs: int = 3):
    """
    Demonstrate incremental indexing functionality.

    Args:
        directory: Directory containing markdown files to index
        num_runs: Number of indexing runs to perform
    """
    try:
        # Display demo purpose panel
        console.print(
            Panel.fit(
                "🔄 [bold blue]Incremental Indexing & Change Detection Demo[/bold blue]\n"
                "This demo showcases smart indexing capabilities including:\n"
                "• Content-based change detection using file hashing\n"
                "• Incremental processing of only modified files\n"
                "• Automatic handling of file create/update/delete operations\n"
                "• Performance optimization through selective reprocessing\n"
                "• Change detection state management and persistence\n"
                "• Batch vs. single file processing demonstrations\n\n"
                f"📁 Directory: [cyan]{directory}[/cyan] | "
                f"🔢 Runs: [yellow]{num_runs}[/yellow]",
                title="Markdown RAG Incremental Indexing Demo",
                border_style="blue",
            )
        )

        # Create mock dependencies
        config = MockRAGConfig()
        vector_store = MockVectorStore()

        # Initialize components with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing incremental indexer...", total=None)
            change_detector = DocumentChangeDetector(config=config)
            document_indexer = MockDocumentIndexer(config, vector_store)
            indexer = IncrementalIndexer(
                config=config, document_indexer=document_indexer, change_detector=change_detector
            )
            progress.update(task, completed=True)

        console.print("✅ [bold green]Initialized incremental indexer[/bold green]")

        # Track overall progress across runs
        overall_progress = Progress(
            TextColumn("[progress.description]"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        )

        with overall_progress:
            overall_task = overall_progress.add_task("Incremental indexing demo", total=num_runs)

            # Perform multiple indexing runs to show incremental behavior
            for run_num in range(1, num_runs + 1):
                # Display run header
                run_panel = Panel(
                    f"[bold yellow]Run {run_num} of {num_runs}[/bold yellow]",
                    title=f"🚀 Indexing Run {run_num}",
                    border_style="yellow",
                )
                console.print(f"\n{run_panel}")

                if run_num > 1:
                    # Modify some files between runs to show incremental updates
                    await modify_test_files(directory, run_num)

                # Perform indexing with timing
                console.print(f"🚀 [bold cyan]Starting indexing run {run_num}...[/bold cyan]")
                start_time = time.time()

                result = await indexer.update_index_for_directory(directory, recursive=True)

                elapsed = time.time() - start_time

                # Display results in a rich table
                results_table = create_indexing_results_table(result, run_num, elapsed)
                console.print(results_table)

                # Show vector store stats
                store_stats = vector_store.get_stats()
                stats_table = create_vector_store_stats_table(store_stats)
                console.print(stats_table)

                # Show recent operations if available
                if store_stats['recent_operations']:
                    ops_panel = Panel(
                        "\n".join(store_stats['recent_operations'][-5:]),
                        title="🕒 Recent Operations",
                        border_style="dim",
                    )
                    console.print(ops_panel)

                # Demonstrate single file processing
                if run_num == 2:
                    await demonstrate_single_file_processing(indexer, directory)

                # Update overall progress
                overall_progress.update(overall_task, completed=run_num)

                if run_num < num_runs:
                    console.print("\n⏳ [dim]Waiting 3 seconds before next run...[/dim]")
                    await asyncio.sleep(3)

        console.print(f"\n✅ [bold green]Completed {num_runs} indexing runs[/bold green]")

        # Show change detection state
        await show_change_detection_state(change_detector, directory)

        console.print("\n🎉 [bold green]Incremental indexing demo completed successfully![/bold green]")

    except ImportError as e:
        console.print(f"❌ [red]Import error:[/red] {e}")
        console.print("This demo requires the incremental indexing components to be available.")
    except Exception as e:
        console.print(f"❌ [red]Demo failed:[/red] {e}")
        logger.error(f"Demo failed: {e}")
        raise


async def demonstrate_single_file_processing(indexer, directory: Path):
    """Demonstrate processing a single file."""
    console.print("\n🎯 [bold blue]Single File Processing Demo[/bold blue]")

    # Find a file to process
    markdown_files = list(directory.glob("*.md"))
    if not markdown_files:
        console.print("   [dim]No markdown files found for single file demo[/dim]")
        return

    test_file = markdown_files[0]
    console.print(f"   Processing single file: [cyan]{test_file.name}[/cyan]")

    # Process the file with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Processing {test_file.name}...", total=None)
        result = await indexer.update_single_file(test_file, operation='modified')
        progress.update(task, completed=True)

    # Display result in a small table
    result_table = Table(title="Single File Processing Result", show_header=True)
    result_table.add_column("Metric", style="cyan")
    result_table.add_column("Value", style="white")

    result_table.add_row("Result", result.get('status', 'Unknown'))
    result_table.add_row("Operation", result.get('operation', 'Unknown'))
    if 'sections_created' in result:
        result_table.add_row("Sections Created", str(result['sections_created']))
    if 'word_count' in result:
        result_table.add_row("Word Count", str(result['word_count']))

    console.print(result_table)


async def show_change_detection_state(change_detector, directory: Path):
    """Show the current state of change detection."""
    console.print("\n🔍 [bold blue]Change Detection State[/bold blue]")

    try:
        # Get index stats
        stats = change_detector.get_index_stats()

        # Display in a table
        state_table = Table(title="Change Detection Statistics", show_header=True)
        state_table.add_column("Metric", style="cyan")
        state_table.add_column("Value", style="white")

        state_table.add_row("Files in Index", str(stats.get('total_files', 0)))
        state_table.add_row("Total Size", str(stats.get('total_size', 0)) + " bytes")
        state_table.add_row("Last Updated", stats.get('last_updated', 'Never'))

        console.print(state_table)

        # Show some sample files if available
        if stats.get('total_files', 0) > 0:
            console.print("\n✅ [green]Change detection is tracking file states[/green]")
        else:
            console.print("\n⚠️  [yellow]No files currently tracked by change detector[/yellow]")

    except Exception as e:
        console.print(f"[red]Could not show change detection state: {e}[/red]")
        logger.debug(f"Could not show change detection state: {e}")


async def modify_test_files(directory: Path, run_num: int):
    """Modify some test files to demonstrate incremental updates."""
    console.print(f"✏️  [bold yellow]Modifying files for run {run_num}...[/bold yellow]")

    markdown_files = list(directory.glob("*.md"))
    modifications = []

    if run_num == 2 and len(markdown_files) >= 2:
        # Modify first file
        file1 = markdown_files[0]
        content = file1.read_text() + f"\n\n## Update from Run {run_num}\n\nThis content was added in run {run_num}."
        file1.write_text(content)
        modifications.append(("Modified", file1.name))

        # Create new file
        new_file = directory / f"new_file_run_{run_num}.md"
        new_file.write_text(f"# New File from Run {run_num}\n\nThis file was created in run {run_num}.")
        modifications.append(("Created", new_file.name))

    elif run_num == 3 and len(markdown_files) >= 3:
        # Modify different file
        file2 = markdown_files[1] if len(markdown_files) > 1 else markdown_files[0]
        content = file2.read_text() + f"\n\n### Additional Section (Run {run_num})\n\nMore content added."
        file2.write_text(content)
        modifications.append(("Modified", file2.name))

        # Delete a file (if we created one in run 2)
        delete_candidate = directory / "new_file_run_2.md"
        if delete_candidate.exists():
            delete_candidate.unlink()
            modifications.append(("Deleted", delete_candidate.name))

    # Display modifications in a table
    if modifications:
        mod_table = Table(title="File Modifications", show_header=True)
        mod_table.add_column("Operation", style="cyan")
        mod_table.add_column("File", style="white")

        for operation, filename in modifications:
            if operation == "Created":
                mod_table.add_row(f"➕ {operation}", filename)
            elif operation == "Modified":
                mod_table.add_row(f"✏️  {operation}", filename)
            elif operation == "Deleted":
                mod_table.add_row(f"🗑️  {operation}", filename)

        console.print(mod_table)


def create_test_documents(directory: Path):
    """Create test markdown documents with frontmatter."""
    directory.mkdir(parents=True, exist_ok=True)

    documents = {
        "introduction.md": """---
title: Introduction to the System
tags: [introduction, overview, getting-started]
topics: [system-overview, architecture]
summary: A comprehensive introduction to the Markdown RAG system
---

# Introduction

Welcome to our Markdown RAG system! This document provides an overview of the system's capabilities and architecture.

## Key Features

- Semantic search across markdown documents
- Automatic indexing and monitoring
- Frontmatter-enhanced search relevance
- Real-time incremental updates

## Architecture Overview

The system consists of several key components working together to provide efficient document search and retrieval.
""",
        "user-guide.md": """---
title: User Guide
tags: [documentation, guide, tutorial]
topics: [usage, examples, best-practices]
keywords: [search, query, index, monitor]
---

# User Guide

This guide explains how to use the Markdown RAG system effectively.

## Basic Usage

### Indexing Documents

To index your markdown documents:

1. Configure the system settings
2. Point to your document directory
3. Start the indexing process

### Searching

Use natural language queries to search through your documents:

- "How do I configure the system?"
- "What are the key features?"
- "Show me examples of usage"

## Advanced Features

### Frontmatter Enhancement

Documents with YAML frontmatter get enhanced search relevance through metadata integration.
""",
        "api-reference.md": """---
title: API Reference
tags: [api, reference, technical]
topics: [methods, functions, classes]
summary: Complete API reference for developers
---

# API Reference

## Core Classes

### RAGEngine
The main engine for semantic search operations.

### IncrementalIndexer
Handles automatic document indexing and updates.

### MonitoringCoordinator
Coordinates file monitoring with index updates.

## Methods

### search(query: str) -> List[SearchResult]
Performs semantic search across indexed documents.

### index_directory(path: Path) -> IndexResult
Indexes all supported documents in a directory.

### start_monitoring(path: Path) -> None
Starts real-time monitoring of a directory.
""",
        "changelog.md": """# Changelog

## Version 1.0.0

### Added
- Initial release of Markdown RAG system
- Semantic search functionality
- Frontmatter parsing and enhancement
- Real-time file monitoring
- Incremental index updates

### Features
- Support for markdown and text files
- YAML frontmatter parsing
- Debounced file change detection
- Automatic index synchronization
""",
    }

    console.print("📝 [bold blue]Creating Test Documents[/bold blue]")

    # Create files with progress tracking
    for filename, content in track(documents.items(), description="Creating documents..."):
        file_path = directory / filename
        file_path.write_text(content, encoding='utf-8')

    # Display created documents in a table
    docs_table = Table(title="📄 Created Test Documents", show_header=True)
    docs_table.add_column("File", style="cyan")
    docs_table.add_column("Size", style="white")
    docs_table.add_column("Has Frontmatter", style="dim")

    for filename in documents.keys():
        file_path = directory / filename
        size = file_path.stat().st_size
        has_frontmatter = documents[filename].startswith('---')
        docs_table.add_row(filename, f"{size} bytes", "✅ Yes" if has_frontmatter else "❌ No")

    console.print(docs_table)
    console.print(f"✅ [bold green]Created {len(documents)} test documents in {directory}[/bold green]")


@click.command()
@click.option(
    '--directory',
    '-d',
    type=click.Path(path_type=Path),
    default=Path('./test_markdown'),
    help='[cyan]Directory containing markdown files to index[/cyan]',
)
@click.option('--runs', '-r', type=int, default=3, help='[yellow]Number of indexing runs to perform[/yellow]')
@click.option('--setup', '-s', is_flag=True, help='[green]Create test documents in the directory[/green]')
@click.option('--verbose', '-v', is_flag=True, help='[blue]Enable verbose logging[/blue]')
def main(directory: Path, runs: int, setup: bool, verbose: bool):
    """
    [bold blue]Demonstrate incremental indexing functionality of the Markdown RAG system[/bold blue]

    [dim]This script shows how the system efficiently detects changes in markdown
    files and updates the search index incrementally, avoiding unnecessary
    reprocessing of unchanged documents.[/dim]

    [yellow]Features Demonstrated:[/yellow]
    • Content-based change detection using file hashing
    • Incremental processing of only modified files
    • Automatic handling of file create/update/delete operations
    • Performance optimization through selective reprocessing
    • Change detection state management and persistence
    • Batch vs. single file processing demonstrations

    [yellow]Demo Workflow:[/yellow]
    The demo performs multiple indexing runs, modifying files between runs
    to demonstrate how only changed files are reprocessed.

    [yellow]Example Usage:[/yellow]
    ```
    # Run basic demo with 3 indexing runs
    python examples/incremental_indexing_demo.py

    # Setup test documents and run 5 iterations
    python examples/incremental_indexing_demo.py -s -r 5

    # Use custom directory with verbose logging
    python examples/incremental_indexing_demo.py -d /path/to/docs -v
    ```
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(
        Panel.fit(
            "🎯 [bold blue]Incremental Indexing Demo[/bold blue]\n\n"
            "This demo demonstrates how the system efficiently detects\n"
            "file changes and processes only what has changed between\n"
            "indexing runs, improving performance and resource usage.",
            title="Welcome",
            border_style="blue",
        )
    )

    try:
        if setup:
            create_test_documents(directory)

        # Ensure directory exists
        if not directory.exists():
            console.print(f"❌ [red]Directory does not exist:[/red] {directory}")
            console.print("Use [cyan]--setup[/cyan] to create test documents, or specify an existing directory.")
            return 1

        # Run the incremental indexing demo
        asyncio.run(demonstrate_incremental_indexing(directory, runs))

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
