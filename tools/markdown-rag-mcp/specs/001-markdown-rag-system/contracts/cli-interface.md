# CLI Interface Contract

**Version**: 1.0.0
**Date**: 2025-10-08
**Protocol**: stdin/arguments → stdout (Constitutional Requirement II)

## Command Structure

All commands follow the pattern: `markdown-rag-mcp [COMMAND] [OPTIONS]`

### Global Options

- `--format {json,human}`: Output format (default: human)
- `--config PATH`: Configuration file path
- `--verbose`: Enable verbose logging
- `--help`: Show help information

## Commands

### 1. index - Index Markdown Files

**Purpose**: Process and index markdown files from the configured directory

**Usage**:

```bash
markdown-rag-mcp index [OPTIONS] [PATH]
```

**Arguments**:

- `PATH`: Directory path containing markdown files (default: ./documents)

**Options**:

- `--force`: Re-index all files, ignoring existing indices
- `--watch`: Monitor directory for changes and auto-index

**Output (JSON)**:

```json
{
  "status": "success",
  "indexed_files": 42,
  "failed_files": 1,
  "processing_time": "15.2s",
  "errors": [
    {
      "file": "./documents/broken.md",
      "error": "Invalid frontmatter syntax"
    }
  ]
}
```

**Output (Human)**:

```plaintext
✓ Indexed 42 files successfully
✗ Failed to process 1 file
⏱ Completed in 15.2s

Errors:
  ./documents/broken.md: Invalid frontmatter syntax
```

**Exit Codes**:

- `0`: Success (all files processed or only skippable errors)
- `1`: Configuration error or database connection failure
- `2`: Invalid arguments or file permissions

### 2. search - Query Indexed Content

**Purpose**: Search for relevant content using natural language queries

**Usage**:

```bash
markdown-rag-mcp search [OPTIONS] "QUERY"
```

**Arguments**:

- `QUERY`: Natural language search query (required)

**Options**:

- `--limit N`: Maximum number of results (default: 10)
- `--threshold FLOAT`: Similarity threshold 0.0-1.0 (default: 0.7)
- `--include-metadata`: Include frontmatter metadata in results

**Input (stdin alternative)**:

```bash
echo "authentication setup" | markdown-rag-mcp search --format json
```

**Output (JSON)**:

```json
{
  "query": "authentication setup",
  "results": [
    {
      "section_text": "## Authentication Setup\n\nTo configure authentication...",
      "file_path": "./documents/auth-guide.md",
      "confidence_score": 0.89,
      "section_heading": "Authentication Setup",
      "heading_level": 2,
      "metadata": {
        "title": "Authentication Guide",
        "tags": ["auth", "setup", "security"],
        "topics": ["authentication", "configuration"]
      },
      "chunk_index": 3
    }
  ],
  "total_results": 1,
  "processing_time": "0.15s"
}
```

**Output (Human)**:

```plaintext
🔍 Query: "authentication setup"

┌─ Result 1/1 (Score: 0.89) ─────────────────────────────────────────────┐
│ File: ./documents/auth-guide.md                                         │
│ Section: Authentication Setup (H2)                                     │
├────────────────────────────────────────────────────────────────────────┤
│ ## Authentication Setup                                                │
│                                                                        │
│ To configure authentication...                                         │
└────────────────────────────────────────────────────────────────────────┘

⏱ Found 1 result in 0.15s
```

**Exit Codes**:

- `0`: Success (results found or no matches)
- `1`: Database connection error
- `2`: Invalid query or arguments

### 3. status - System Status

**Purpose**: Display system status and statistics

**Usage**:

```bash
markdown-rag-mcp status [OPTIONS]
```

**Options**:

- `--detailed`: Show per-file processing status

**Output (JSON)**:

```json
{
  "database": {
    "status": "connected",
    "total_documents": 42,
    "total_sections": 387,
    "total_embeddings": 387
  },
  "directory": {
    "path": "./documents",
    "total_files": 42,
    "indexed_files": 41,
    "failed_files": 1,
    "last_scan": "2025-10-08T14:30:00Z"
  },
  "performance": {
    "avg_query_time": "0.12s",
    "last_index_time": "15.2s"
  }
}
```

**Exit Codes**:

- `0`: Success
- `1`: System error or database unavailable

### 4. config - Configuration Management

**Purpose**: Manage system configuration

**Usage**:

```bash
markdown-rag-mcp config [SUBCOMMAND] [OPTIONS]
```

**Subcommands**:

- `show`: Display current configuration
- `set KEY VALUE`: Set configuration value
- `reset`: Reset to default configuration

**Examples**:

```bash
markdown-rag-mcp config show --format json
markdown-rag-mcp config set embedding.model "text-embedding-3-small"
markdown-rag-mcp config set similarity.threshold 0.8
```

### 5. validate - Validate Files

**Purpose**: Check markdown files for parsing issues without indexing

**Usage**:

```bash
markdown-rag-mcp validate [OPTIONS] [PATH]
```

**Options**:

- `--fix-frontmatter`: Attempt to fix common frontmatter issues

**Output**: List of validation errors and warnings per file

## Error Handling

### Standard Error Format (JSON)

```json
{
  "error": {
    "code": "MILVUS_CONNECTION_FAILED",
    "message": "Unable to connect to Milvus database",
    "details": {
      "host": "localhost",
      "database": "markdown_rag_mcp",
      "suggestion": "Check if Milvus is running"
    }
  }
}
```

### Standard Error Format (Human)

```
Error: Unable to connect to Milvus database

Details:
  Host: localhost
  Database: markdown_rag_mcp

Suggestion: Check if Milvus is running

For more help, run: markdown-rag-mcp --help
```

### Common Error Codes

- `INVALID_CONFIG`: Configuration file is invalid or missing required fields
- `MILVUS_CONNECTION_FAILED`: Cannot connect to Milvus vector database
- `EMBEDDING_MODEL_ERROR`: Local embedding model loading or inference failed
- `PERMISSION_DENIED`: Insufficient file system permissions
- `INVALID_MARKDOWN_DIRECTORY`: Specified directory doesn't exist or isn't readable

## Configuration File

**Default Location**: `~/.config/markdown-rag-mcp/config.toml`

**Format**:

```toml
[milvus]
host = "localhost"
port = 19530
collection_prefix = "markdown_rag_mcp"

[embedding]
model = "sentence-transformers/all-MiniLM-L6-v2"
device = "auto"  # "cpu", "cuda", "mps", or "auto"
batch_size = 32

[processing]
chunk_size_limit = 1000
similarity_threshold = 0.7
max_file_size_mb = 50

[directories]
markdown_path = "./documents"
cache_path = "~/.cache/markdown-rag-mcp"

[monitoring]
watch_enabled = false
scan_interval_seconds = 60
```

## Integration Patterns

### Pipeline Usage

```bash
# Index files and then search
markdown-rag-mcp index ./docs && markdown-rag-mcp search "API documentation"

# Continuous monitoring
markdown-rag-mcp index --watch &
```

### JSON Output Processing

```bash
# Extract file paths from search results
markdown-rag-mcp search "example" --format json | jq -r '.results[].file_path'

# Check if indexing succeeded
if markdown-rag-mcp index --format json | jq -e '.status == "success"'; then
    echo "Indexing completed successfully"
fi
```

### Environment Integration

```bash
# Configuration via environment variables
export MARKDOWN_RAG_MCP_MILVUS_HOST="localhost"
export MARKDOWN_RAG_MCP_MILVUS_PORT="19530"
export MARKDOWN_RAG_MCP_EMBEDDING_DEVICE="cuda"  # Optional: use GPU if available
export MARKDOWN_RAG_MCP_CONFIG="/path/to/config.toml"

markdown-rag-mcp search "query"
```

This CLI interface contract ensures constitutional compliance with text in/out protocol and provides both JSON and human-readable formats for maximum interoperability.
