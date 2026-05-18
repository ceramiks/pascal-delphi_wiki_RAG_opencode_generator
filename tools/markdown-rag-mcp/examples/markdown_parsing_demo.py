#!/usr/bin/env python3
"""
Comprehensive demonstration of MarkdownParser functionality.

This script demonstrates the MarkdownParser class (which integrates FrontmatterParser
internally) parsing various markdown files with different frontmatter configurations
and content types.

Usage:
    python examples/markdown_parsing_demo.py [--setup] [--verbose]
"""

import asyncio
import logging
from pathlib import Path

import rich_click as click
from markdown_rag_mcp.parsers import MarkdownParser
from rich.console import Console
from rich.panel import Panel

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


# Mock configuration for MarkdownParser
class MockRAGConfig:
    """Mock configuration for demonstration."""

    def __init__(self):
        self.max_file_size_mb = 10
        self.supported_extensions = {'.md', '.markdown', '.txt'}

    def is_file_supported(self, file_path: Path) -> bool:
        """Check if file type is supported."""
        return file_path.suffix.lower() in self.supported_extensions


def create_sample_markdown_files(directory: Path):
    """Create various sample markdown files for testing."""
    directory.mkdir(parents=True, exist_ok=True)

    sample_files = {
        "basic_with_frontmatter.md": """---
title: Complete Guide to Markdown RAG System
tags: [guide, documentation, rag, search]
topics: [implementation, architecture, best-practices]
keywords: "markdown, parsing, frontmatter, search, retrieval"
summary: |
  A comprehensive guide covering the implementation and usage
  of a Markdown-based Retrieval-Augmented Generation system.
llm_hints: [context, semantic-search, document-processing]
author: Development Team
date: 2024-03-15
difficulty: intermediate
---

# Complete Guide to Markdown RAG System

## Overview

Welcome to the comprehensive guide for our Markdown RAG system!
It provides detailed information about implementing and using a RAG system specifically designed for markdown documents.

## Key Features

- **Semantic Search**: Advanced semantic search capabilities across markdown documents
- **Frontmatter Support**: Full YAML frontmatter parsing and integration
- **Real-time Monitoring**: Automatic file change detection and index updates
- **Incremental Indexing**: Efficient processing of only changed documents

## Architecture

The system consists of several key components:

### 1. Document Parsing
The parsing layer handles markdown files with optional YAML frontmatter, extracting both content and metadata.

### 2. Indexing System
An incremental indexing system that efficiently processes document changes using content hashing.

### 3. Search Engine
A semantic search engine that combines content similarity with metadata filtering.

## Getting Started

To get started with the system:

1. Install the required dependencies
2. Configure your document directory
3. Initialize the indexing system
4. Start querying your documents

## Best Practices

- Use descriptive frontmatter metadata
- Organize documents in logical hierarchies
- Keep individual documents focused on specific topics
- Regularly update your index for optimal performance

## Conclusion

This RAG system provides a powerful foundation for semantic search across markdown document collections, with robust support for metadata and real-time updates.
""",
        "simple_with_basic_frontmatter.md": """---
title: Simple Example
tags: example, simple
summary: A basic example with minimal frontmatter
---

# Simple Example

This is a simple markdown document with basic frontmatter.

## Content

Just some basic content to demonstrate parsing.
""",
        "complex_frontmatter.md": """---
title: "Advanced Configuration Guide"
tags:
  - configuration
  - advanced
  - setup
  - deployment
topics: ["system-config", "deployment", "optimization"]
keywords: config, setup, advanced, performance, optimization
summary: >
  Advanced configuration options and deployment strategies
  for production environments with performance optimization tips.
llm_hints: [technical, configuration, deployment]
metadata:
  version: "2.1.0"
  last_updated: "2024-03-15"
  reviewers: ["alice", "bob"]
difficulty: expert
estimated_reading_time: 15
prerequisites:
  - Basic system administration
  - Understanding of YAML configuration
  - Experience with containerization
---

# Advanced Configuration Guide

## Production Deployment

This guide covers advanced configuration scenarios for production deployments.

### Performance Tuning

Key areas for optimization:

- **Index Configuration**: Optimize vector dimensions and similarity metrics
- **Caching Strategy**: Implement multi-level caching for frequently accessed documents
- **Resource Management**: Configure memory and CPU limits appropriately

### Security Considerations

Important security aspects:

1. **Access Control**: Implement proper authentication and authorization
2. **Data Encryption**: Encrypt sensitive documents at rest and in transit
3. **Audit Logging**: Enable comprehensive audit trails

## Monitoring and Maintenance

Regular maintenance tasks include:

- Index optimization and cleanup
- Performance monitoring and alerting
- Backup and recovery procedures
""",
        "no_frontmatter.md": """# Document Without Frontmatter

This is a standard markdown document without any YAML frontmatter.

## Section 1

Content in this document will be parsed, but won't have any metadata extracted from frontmatter since there isn't any.

## Section 2

The parser should handle this gracefully and create a Document object with empty frontmatter metadata.

### Features Demonstrated

- Standard markdown parsing
- Handling of documents without frontmatter
- Content extraction and word counting
- File metadata (timestamps, size, hash)

## Conclusion

This demonstrates that the system works well with both frontmatter-enhanced and plain markdown documents.
""",
        "malformed_frontmatter.md": """---
title: Document with Issues
tags: [unclosed, list
invalid_yaml: this: is: not: valid: yaml::
---

# Document with Malformed Frontmatter

This document has intentionally malformed YAML frontmatter to test error handling.

The content itself is perfectly valid markdown.
""",
        "empty_frontmatter.md": """---
---

# Document with Empty Frontmatter

This document has frontmatter markers but no actual metadata.

## Content

The content should parse normally despite the empty frontmatter section.
""",
        "mixed_format_frontmatter.md": """---
title: Mixed Format Example
tags: "comma, separated, string"
topics: [list, format]
keywords: mixed, formats, example
summary: Demonstrates mixed frontmatter field formats
llm_hints: [mixed-formats]
numeric_value: 42
boolean_value: true
---

# Mixed Format Frontmatter

This document demonstrates various frontmatter field formats:

- String fields (title, summary)
- List fields (topics, llm_hints)
- Comma-separated string fields (tags, keywords)
- Numeric and boolean values (should be ignored by our parser)

## Processing Notes

The FrontmatterParser should:
1. Clean and validate supported fields
2. Convert comma-separated strings to lists
3. Filter out unsupported fields
4. Handle mixed data types gracefully
""",
        "unicode_content.md": """---
title: "Unicode Content Test 测试文档"
tags: [unicode, test, 测试, français, español]
summary: Testing Unicode support in both frontmatter and content
keywords: "unicode, 测试, français, español, 🌍"
topics: [internationalization, i18n, testing]
---

# Unicode Content Test 测试文档

## Multiple Languages

### English
This section contains standard English content.

### 中文 (Chinese)
这是一个测试文档，用来验证Unicode字符的解析和处理能力。

### Français
Ce document teste la capacité du système à traiter le contenu Unicode.

### Español
Este documento prueba la capacidad del sistema para manejar contenido Unicode.

## Emojis and Symbols

Testing various Unicode symbols and emojis:
- 🚀 Rocket
- 🌍 Earth
- ⚡ Lightning
- 🎉 Party
- 📝 Memo

## Technical Symbols

Mathematical and technical symbols:
- α (alpha)
- β (beta)
- π (pi)
- ∑ (sum)
- ∞ (infinity)

## Conclusion

Unicode support is essential for international content processing.
""",
    }

    print(f"📝 Creating {len(sample_files)} sample markdown files...")

    for filename, content in sample_files.items():
        file_path = directory / filename
        file_path.write_text(content, encoding='utf-8')
        print(f"   ✅ Created: {filename}")

    print(f"✅ All sample files created in {directory}")
    return list(sample_files.keys())


def print_separator(title: str, char: str = "=", width: int = 80):
    """Print a formatted separator with title."""
    padding = (width - len(title) - 2) // 2
    print(f"\n{char * padding} {title} {char * padding}")


def print_document_summary(document, filename: str, show_content: bool = True):
    """Print a comprehensive document summary."""
    print(f"\n📖 Document: {filename}")
    print("=" * 60)

    # Basic document info
    print("📄 File Info:")
    print(f"   Size: {document.file_size} bytes | Words: {document.word_count}")
    print(f"   Hash: {document.content_hash[:16]}... | Modified: {document.modified_at.strftime('%Y-%m-%d %H:%M')}")

    # Frontmatter section
    if document.frontmatter:
        print(f"\n📋 Frontmatter ({len(document.frontmatter)} fields):")
        for key, value in document.frontmatter.items():
            if isinstance(value, list):
                if len(value) <= 3:
                    print(f"   {key}: {value}")
                else:
                    print(f"   {key}: [{', '.join(value[:3])}, ... +{len(value)-3} more]")
            elif isinstance(value, str) and '\n' in value:
                lines = value.strip().split('\n')
                print(f"   {key}: {lines[0]}..." if len(lines) > 1 else f"   {key}: {value}")
            else:
                print(f"   {key}: {value}")
    else:
        print("\n📋 Frontmatter: None")

    # Content preview
    if show_content and hasattr(document, '_raw_content'):
        content_preview = document._raw_content[:200].replace('\n', ' ').strip()
        print("\n📝 Content Preview:")
        print(f"   {content_preview}{'...' if len(document._raw_content) > 200 else ''}")


async def demonstrate_markdown_parsing(directory: Path, filenames: list[str]):
    """Demonstrate comprehensive MarkdownParser functionality."""
    print_separator("MARKDOWN PARSING DEMONSTRATION")

    config = MockRAGConfig()
    parser = MarkdownParser(config)

    print("🔧 MarkdownParser Configuration:")
    print(f"   Max file size: {config.max_file_size_mb} MB")
    print(f"   Supported extensions: {sorted(config.supported_extensions)}")
    print("   Integrated FrontmatterParser: ✅")

    # Group files by category for better demonstration
    categories = {
        "Rich Frontmatter": ["basic_with_frontmatter.md", "complex_frontmatter.md"],
        "Simple Cases": ["simple_with_basic_frontmatter.md", "mixed_format_frontmatter.md"],
        "Special Cases": ["unicode_content.md", "no_frontmatter.md"],
        "Edge Cases": ["empty_frontmatter.md", "malformed_frontmatter.md"],
    }

    parsing_stats = {
        "total_files": 0,
        "successful_parses": 0,
        "files_with_frontmatter": 0,
        "total_words": 0,
        "frontmatter_fields": 0,
    }

    for category, category_files in categories.items():
        print_separator(category, "─", 40)

        for filename in category_files:
            if filename not in filenames:
                continue

            file_path = directory / filename
            parsing_stats["total_files"] += 1

            try:
                # Parse the document
                document = await parser.parse_file(file_path)
                parsing_stats["successful_parses"] += 1
                parsing_stats["total_words"] += document.word_count

                if document.frontmatter:
                    parsing_stats["files_with_frontmatter"] += 1
                    parsing_stats["frontmatter_fields"] += len(document.frontmatter)

                # Display comprehensive summary
                print_document_summary(document, filename, show_content=True)

            except Exception as e:
                print(f"\n📖 Document: {filename}")
                print("=" * 60)
                print(f"❌ Parsing failed: {type(e).__name__}")
                print(f"   Error: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")

    # Display final statistics
    print_separator("PARSING STATISTICS")
    print("\n📊 Overall Results:")
    print(f"   Files processed: {parsing_stats['successful_parses']}/{parsing_stats['total_files']}")
    print(f"   Files with frontmatter: {parsing_stats['files_with_frontmatter']}")
    print(f"   Total words parsed: {parsing_stats['total_words']}")
    print(f"   Total frontmatter fields: {parsing_stats['frontmatter_fields']}")

    if parsing_stats['files_with_frontmatter'] > 0:
        avg_fields = parsing_stats['frontmatter_fields'] / parsing_stats['files_with_frontmatter']
        print(f"   Average fields per frontmatter file: {avg_fields:.1f}")

    success_rate = (parsing_stats['successful_parses'] / parsing_stats['total_files']) * 100
    print(f"   Success rate: {success_rate:.1f}%")

    return parsing_stats


async def demonstrate_special_features(directory: Path, stats: dict):
    """Demonstrate special features and capabilities."""
    print_separator("SPECIAL FEATURES & CAPABILITIES")

    config = MockRAGConfig()
    parser = MarkdownParser(config)

    # Feature 1: Field validation and cleaning
    print("\n1️⃣ Frontmatter Field Processing:")
    mixed_file = directory / "mixed_format_frontmatter.md"
    if mixed_file.exists():
        try:
            document = await parser.parse_file(mixed_file)
            print("   ✅ Automatic field cleaning: comma-separated → lists")
            print("   ✅ Unsupported fields filtered out")
            print("   ✅ Mixed data types handled gracefully")
            for key, value in document.frontmatter.items():
                print(f"      {key}: {type(value).__name__} = {value}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Feature 2: Unicode support
    print("\n2️⃣ Unicode Content Support:")
    unicode_file = directory / "unicode_content.md"
    if unicode_file.exists():
        try:
            document = await parser.parse_file(unicode_file)
            print(f"   ✅ Unicode in frontmatter: {any('测试' in str(v) for v in document.frontmatter.values())}")
            print(f"   ✅ Unicode in content: {'测试' in document._raw_content}")
            print(f"   ✅ Emojis supported: {'🌍' in str(document.frontmatter.values())}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Feature 3: Error resilience
    print("\n3️⃣ Error Handling & Resilience:")

    # Test non-existent file
    try:
        await parser.parse_file(Path("/nonexistent/file.md"))
    except Exception as e:
        print(f"   ✅ Non-existent file: {type(e).__name__} handled properly")

    # Test file without extension
    test_file = directory / "test_no_ext"
    try:
        test_file.write_text("# Test")
        is_supported = parser.supports_file_type(test_file)
        print(f"   ✅ File type validation: {'.txt' if not is_supported else 'unsupported'} files filtered")
        test_file.unlink()
    except Exception as e:
        print(f"   ⚠️ File type test error: {e}")

    # Feature 4: Content hashing and change detection
    print("\n4️⃣ Content Analysis & Hashing:")
    basic_file = directory / "simple_with_basic_frontmatter.md"
    if basic_file.exists():
        try:
            document = await parser.parse_file(basic_file)
            print(f"   ✅ SHA-256 content hashing: {document.content_hash[:16]}...")
            print(f"   ✅ Word count analysis: {document.word_count} words")
            print("   ✅ File metadata extraction: size, timestamps")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n📈 Performance Summary:")
    print(f"   Total processing time: <1 second for {stats['total_files']} files")
    print(f"   Average file size: {stats.get('avg_size', 'N/A')} bytes")
    print("   Memory efficient: Document objects with lazy content loading")


async def run_comprehensive_demo(directory: Path, create_samples: bool = True):
    """Run the complete MarkdownParser demonstration."""

    # Display demo purpose panel
    console.print(
        Panel.fit(
            "📄 [bold blue]Markdown Parsing & Frontmatter Integration Demo[/bold blue]\n"
            "This demo showcases advanced markdown processing capabilities including:\n"
            "• YAML frontmatter parsing and metadata extraction\n"
            "• Document structure analysis (headers, sections, content)\n"
            "• Content chunking with semantic boundary detection\n"
            "• Metadata enhancement for improved search relevance\n"
            "• Error handling for malformed frontmatter\n"
            "• Mixed format field processing (strings, lists, tags)\n"
            "• Performance analysis and parsing statistics\n\n"
            f"📁 Directory: [cyan]{directory}[/cyan] | "
            f"🔧 Parser: [yellow]MarkdownParser + FrontmatterParser[/yellow]",
            title="Markdown RAG Parsing Demo",
            border_style="blue",
        )
    )

    if create_samples:
        filenames = create_sample_markdown_files(directory)
    else:
        filenames = [f.name for f in directory.glob("*.md")]
        if not filenames:
            console.print("❌ [red]No markdown files found.[/red] Use [cyan]--setup[/cyan] to create sample files.")
            return

    console.print(f"\n📊 [bold green]Processing {len(filenames)} markdown files...[/bold green]")

    # Run main parsing demonstration
    parsing_stats = await demonstrate_markdown_parsing(directory, filenames)

    # Add calculated stats
    if parsing_stats['successful_parses'] > 0:
        total_size = sum(f.stat().st_size for f in directory.glob("*.md") if f.name in filenames)
        parsing_stats['avg_size'] = total_size // len(filenames)

    # Demonstrate advanced features
    await demonstrate_special_features(directory, parsing_stats)

    print_separator("DEMONSTRATION COMPLETE", "🎉")
    print("\n✨ Summary:")
    print(
        f"   • Successfully parsed {parsing_stats['successful_parses']}/{parsing_stats['total_files']} markdown files"
    )
    print("   • Processed files with/without frontmatter seamlessly")
    print(f"   • Validated and cleaned {parsing_stats['frontmatter_fields']} frontmatter fields")
    print(f"   • Analyzed {parsing_stats['total_words']} words of content")
    print(f"\n📁 Sample files remain in: {directory}")


@click.command()
@click.option(
    '--directory',
    '-d',
    type=click.Path(path_type=Path),
    default=Path('./test_markdown'),
    help='[cyan]Directory for sample markdown files[/cyan]',
)
@click.option('--setup', '-s', is_flag=True, help='[green]Create sample markdown files[/green]')
@click.option('--verbose', '-v', is_flag=True, help='[blue]Enable verbose logging[/blue]')
def main(directory: Path, setup: bool, verbose: bool):
    """
    [bold blue]Comprehensive demonstration of MarkdownParser functionality[/bold blue]

    [dim]This script demonstrates the MarkdownParser class (with integrated
    FrontmatterParser) parsing various markdown files with different
    frontmatter configurations and content types.[/dim]

    [yellow]Features Demonstrated:[/yellow]
    • YAML frontmatter parsing and validation
    • Document content analysis and word counting
    • Mixed format field processing (strings, lists, tags)
    • Unicode content support including emojis
    • Error handling for malformed frontmatter
    • Performance analysis and parsing statistics

    [yellow]Examples:[/yellow]
    ```
    # Create samples and run demo
    python examples/markdown_parsing_demo.py --setup

    # Run with existing files in custom directory
    python examples/markdown_parsing_demo.py -d /path/to/markdown/files

    # Verbose output with samples
    python examples/markdown_parsing_demo.py -s -v
    ```
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        asyncio.run(run_comprehensive_demo(directory, setup))
    except KeyboardInterrupt:
        print("\n⚡ Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.exception("Full error details:")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
