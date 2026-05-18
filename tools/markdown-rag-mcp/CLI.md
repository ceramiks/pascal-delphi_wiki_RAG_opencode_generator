# CLI Reference Guide

This document provides a reference guide for all CLI commands in the Markdown RAG system including usage examples and options.

## 🚀 Quick Start

```bash
# Install and setup
pip install -e .
docker-compose -f docker/docker-compose.yml up -d

# Generate sample documents
markdown-rag-mcp generate-docs

# Index the documents
markdown-rag-mcp index ./documents

# Search your content
markdown-rag-mcp search "python best practices"
```

## 📋 Command Overview

| Command                           | Purpose                          | Usage                   |
|-----------------------------------|----------------------------------|-------------------------|
| [`generate-docs`](#generate-docs) | Create test markdown files       | Development and testing |
| [`index`](#index)                 | Process and index markdown files | Document ingestion      |
| [`search`](#search)               | Semantic search across documents | Content discovery       |
| [`status`](#status)               | System health and statistics     | Monitoring              |
| [`config`](#config)               | View configuration settings      | System administration   |

## 🏗️ File Structure

The CLI is built with a modular structure where each command is implemented in its own module for better maintainability and organization:

```plaintext
src/markdown_rag_mcp/cli/
├── main.py                   # Entry point and CLI group setup
├── commands/                 # Command modules directory
│   ├── __init__.py           # Exports all commands
│   ├── index_cmd.py          # Index command implementation
│   ├── search_cmd.py         # Search command implementation
│   ├── status_cmd.py         # Status command implementation
│   ├── config_cmd.py         # Config command implementation
│   └── generate_docs_cmd.py  # Generate docs command implementation
```

---

## 📚 generate-docs

Generate test markdown documents for development and testing purposes.

### Syntax

```bash
markdown-rag-mcp generate-docs [OPTIONS]
```

### Options

| Option               | Type    | Default       | Description                           |
|----------------------|---------|---------------|---------------------------------------|
| `--output-dir`       | PATH    | `./documents` | Directory to create files in          |
| `--count`            | INTEGER | `15`          | Number of files to generate           |
| `--with-frontmatter` | FLOAT   | `0.7`         | Proportion with frontmatter (0.0-1.0) |
| `--force`            | FLAG    | `False`       | Overwrite existing files              |
| `--help`             | FLAG    | -             | Show help message                     |

### Examples

#### Basic Usage

Generate 15 documents in the default `./documents` directory:

```bash
markdown-rag-mcp generate-docs
```

#### Custom Configuration

Generate 25 documents with 80% having frontmatter:

```bash
markdown-rag-mcp generate-docs --count 25 --with-frontmatter 0.8 --output-dir ./test-docs
```

#### Quick Testing Setup

Generate minimal set for rapid testing:

```bash
markdown-rag-mcp generate-docs --count 5 --output-dir ./quick-test --force
```

### Generated Content

The command creates programming and software engineering documents covering:

- **Python fundamentals** - Variables, functions, best practices
- **JavaScript async patterns** - Promises, async/await, error handling
- **Docker best practices** - Production optimization, security
- **Database optimization** - Query tuning, indexing strategies
- **API design principles** - RESTful patterns, documentation
- **Additional topics** - Git workflows, testing, DevOps, architecture

### Frontmatter Fields

Documents with frontmatter include these standardized fields:

```yaml
---
title: "Document Title"
tags:
  - programming
  - python
  - best-practices
topics:
  - software-development
  - programming-languages
keywords:
  - python
  - functions
  - modules
summary: "Brief description of the document content"
llm_hints:
  - explain concepts
  - code examples
created: "2024-10-21"
author: "System Generated"
---
```

---

## 🔍 index

Process and index markdown files for semantic search.

### Syntax

```bash
markdown-rag-mcp index DIRECTORY [OPTIONS]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `DIRECTORY` | PATH | Yes | Directory containing markdown files |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--recursive/--no-recursive` | FLAG | `True` | Search subdirectories |
| `--force` | FLAG | `False` | Force re-index existing files |
| `--watch` | FLAG | `False` | Monitor for file changes |
| `--format` | CHOICE | `human` | Output format (`json` or `human`) |
| `--help` | FLAG | - | Show help message |

### Examples

#### Basic Indexing

Index all markdown files recursively:

```bash
markdown-rag-mcp index ./documents
```

#### Force Re-indexing

Force complete re-indexing of all files:

```bash
markdown-rag-mcp index ./documents --force
```

#### Real-time Monitoring

Index files and start monitoring for changes:

```bash
markdown-rag-mcp index ./documents --watch
```

#### Non-recursive Processing

Index only top-level files:

```bash
markdown-rag-mcp index ./documents --no-recursive
```

#### JSON Output

Get indexing results in JSON format:

```bash
markdown-rag-mcp index ./documents --format json
```

### Processing Details

The indexing process includes:

1. **File Discovery** - Scan for `.md` and `.markdown` files
2. **Frontmatter Parsing** - Extract YAML metadata if present
3. **Content Chunking** - Split large documents into sections
4. **Embedding Generation** - Create vector representations
5. **Vector Storage** - Store in Milvus database
6. **Change Detection** - Track file modifications for incremental updates

### Performance Considerations

- **Incremental Processing** - Only processes changed files by default
- **Concurrent Operations** - Parallel processing for faster indexing
- **Memory Management** - Efficient handling of large document sets
- **Progress Tracking** - Real-time feedback on processing status

---

## 🔍 search

Perform semantic search across indexed documents.

### Syntax

```bash
markdown-rag-mcp search QUERY [OPTIONS]
```

### Arguments

| Argument | Type | Required | Description                   |
|----------|------|----------|-------------------------------|
| `QUERY`  | TEXT | Yes      | Natural language search query |

### Options

| Option               | Type    | Default | Description                       |
|----------------------|---------|---------|-----------------------------------|
| `--limit`            | INTEGER | `10`    | Maximum results to return         |
| `--threshold`        | FLOAT   | `0.7`   | Minimum similarity threshold      |
| `--include-metadata` | FLAG    | `False` | Include document metadata         |
| `--format`           | CHOICE  | `human` | Output format (`json` or `human`) |
| `--help`             | FLAG    | -       | Show help message                 |

### Examples

#### Basic Search

Search for Python-related content:

```bash
markdown-rag-mcp search "python best practices"
```

#### Broad Search

Lower threshold for more results:

```bash
markdown-rag-mcp search "API design" --threshold 0.4 --limit 20
```

#### Detailed Results

Include metadata in search results:

```bash
markdown-rag-mcp search "docker containers" --include-metadata
```

#### JSON Output

Get search results in JSON format:

```bash
markdown-rag-mcp search "database optimization" --format json
```

#### Specific Search

High threshold for precise matches:

```bash
markdown-rag-mcp search "async await patterns" --threshold 0.8 --limit 5
```

### Search Tips

1. **Use natural language** - Write queries as you would ask a colleague
2. **Be specific when needed** - Include technology names for precise results
3. **Adjust threshold** - Lower for broader results, higher for precision
4. **Include metadata** - Helpful for understanding document context
5. **Experiment with queries** - Try different phrasings for better results

---

## 📊 status

Display system status, health, and statistics.

### Syntax

```bash
markdown-rag-mcp status [OPTIONS]
```

### Options

| Option     | Type   | Default | Description                       |
|------------|--------|---------|-----------------------------------|
| `--format` | CHOICE | `human` | Output format (`json` or `human`) |
| `--help`   | FLAG   | -       | Show help message                 |

### Examples

#### System Health Check

View comprehensive system status:

```bash
markdown-rag-mcp status
```

#### JSON Status Export

Get status information in JSON format:

```bash
markdown-rag-mcp status --format json
```

### Status Information

The status command reports on:

#### System Health

- **Overall status** - System operational state
- **Component health** - Individual component status
- **Error conditions** - Any system issues

#### Document Statistics

- **Total documents** - Number of indexed documents
- **Total sections** - Number of document sections
- **Index freshness** - Last update timestamps

#### Database Connection

- **Milvus status** - Vector database connectivity
- **Connection details** - Host, port, collection info
- **Performance metrics** - Query response times

#### Embedding Model

- **Model information** - Current embedding model
- **Device usage** - CPU/GPU utilization
- **Model status** - Loading and initialization state

#### File Monitoring

- **Monitoring status** - Active/inactive state
- **Watched directories** - Currently monitored paths
- **Change statistics** - Recent file changes

### Troubleshooting

Use status output to diagnose issues:

```bash
# Check if Milvus is running
markdown-rag-mcp status | grep "Vector Database"

# Verify document indexing
markdown-rag-mcp status | grep "documents"

# Monitor system health
watch -n 5 "markdown-rag-mcp status --format json | jq '.status'"
```

---

## ⚙️ config

Display current configuration settings.

### Syntax

```bash
markdown-rag-mcp config [OPTIONS]
```

### Options

| Option     | Type   | Default | Description                       |
|------------|--------|---------|-----------------------------------|
| `--format` | CHOICE | `human` | Output format (`json` or `human`) |
| `--help`   | FLAG   | -       | Show help message                 |

### Examples

#### View Configuration

Display all current settings:

```bash
markdown-rag-mcp config
```

#### Export Configuration

Get configuration in JSON format:

```bash
markdown-rag-mcp config --format json
```

### Configuration Categories

#### Database Settings

- **Milvus Host** - Vector database server address
- **Milvus Port** - Database connection port
- **Collection Name** - Milvus collection identifier

#### Embedding Model

- **Model Name** - HuggingFace model identifier
- **Device** - Computation device (CPU/CUDA/MPS)
- **Dimensions** - Vector embedding dimensions

#### Processing Settings

- **Similarity Threshold** - Default search threshold
- **Chunk Size Limit** - Maximum document chunk size
- **Monitoring** - File monitoring enabled/disabled

### Configuration Management

#### Environment Variables

Override settings using environment variables:

```bash
export MARKDOWN_RAG_MCP_MILVUS_HOST=remote-server
export MARKDOWN_RAG_MCP_SIMILARITY_THRESHOLD=0.6
export MARKDOWN_RAG_MCP_EMBEDDING_DEVICE=cuda

markdown-rag-mcp config
```

#### Configuration Files

Use `.env` file for persistent settings:

```env
# .env file
MARKDOWN_RAG_MCP_MILVUS_HOST=localhost
MARKDOWN_RAG_MCP_MILVUS_PORT=19530
MARKDOWN_RAG_MCP_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MARKDOWN_RAG_MCP_SIMILARITY_THRESHOLD=0.7
```

---

## 🔧 Global Options

All commands support these global options:

### Logging Options

| Option        | Type   | Default | Description                                         |
|---------------|--------|---------|-----------------------------------------------------|
| `--log-level` | CHOICE | `INFO`  | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `--log-file`  | PATH   | -       | Log file path (stdout if not specified)             |

### Examples

#### Debug Logging

Enable verbose debug output:

```bash
markdown-rag-mcp --log-level DEBUG index ./documents
```

#### Log to File

Redirect logs to a file:

```bash
markdown-rag-mcp --log-file system.log search "query"
```

#### Production Logging

Minimal logging for production use:

```bash
markdown-rag-mcp --log-level ERROR status
```

---

## 🚀 Workflows

### Development Workflow

1. **Generate Test Data**

   ```bash
   markdown-rag-mcp generate-docs --count 20 --output-dir ./dev-docs
   ```

2. **Index Documents**

   ```bash
   markdown-rag-mcp index ./dev-docs --watch
   ```

3. **Test Search Functionality**

   ```bash
   markdown-rag-mcp search "python functions" --include-metadata
   ```

4. **Monitor System Health**

   ```bash
   markdown-rag-mcp status
   ```

### Performance Tuning

#### For Large Document Collections

```bash
# Use appropriate chunk sizes
export MARKDOWN_RAG_MCP_CHUNK_SIZE_LIMIT=1500

# Force re-index with optimized settings
markdown-rag-mcp index ./large-docs --force
```

#### For High-Accuracy Search

```bash
# Use higher similarity thresholds
markdown-rag-mcp search "specific query" --threshold 0.85 --limit 5
```

#### For Broad Discovery

```bash
# Use lower thresholds and more results
markdown-rag-mcp search "general topic" --threshold 0.4 --limit 25
```

### Error Handling

#### Common Issues and Solutions

**Milvus Connection Errors:**

```bash
# Check Milvus status
docker-compose -f docker/docker-compose.yml ps

# Restart if needed
docker-compose -f docker/docker-compose.yml restart
```

**Index Corruption:**

```bash
# Force complete re-indexing
markdown-rag-mcp index ./documents --force
```

**Memory Issues:**

```bash
# Reduce concurrent processing
export MARKDOWN_RAG_MCP_MAX_CONCURRENT_INDEXING=5
markdown-rag-mcp index ./documents
```

---

## 🆘 Help

### Getting Help

Each command provides detailed help:

```bash
# General help
markdown-rag-mcp --help

# Command-specific help
markdown-rag-mcp generate-docs --help
markdown-rag-mcp search --help
markdown-rag-mcp index --help
```

### Debugging

Enable debug logging for troubleshooting:

```bash
markdown-rag-mcp --log-level DEBUG --log-file debug.log command
```

### Configuration Issues

Check current configuration:

```bash
markdown-rag-mcp config --format json | jq
```

### Performance Monitoring

Monitor system performance:

```bash
# Real-time status monitoring
watch -n 2 'markdown-rag-mcp status'

# Log analysis
tail -f system.log | grep ERROR
```

This CLI provides an interface for managing your markdown document collection with semantic search capabilities.
