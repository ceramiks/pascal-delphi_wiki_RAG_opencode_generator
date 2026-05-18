# Markdown RAG MCP

A Retrieval-Augmented Generation (RAG) MCP server for markdown documentation with semantic search capabilities.

## 🎯 Core Capabilities

- **Document Indexing**: Process markdown files with YAML frontmatter support, automatic chunking, and metadata extraction
- **Semantic Search**: Find relevant content using natural language queries with configurable similarity thresholds
- **Incremental Updates**: Change detection and indexing for large document collections
- **Real-time Monitoring**: Automatic file system monitoring with live index updates
- **Advanced Embeddings**: HuggingFace sentence-transformers with local model execution
- **Vector Storage**: High-performance Milvus vector database with Docker Compose setup
- **CLI Interface**: Beautiful command-line tools with progress tracking and interactive demos

## 🤖 MCP Server Integration

This system is designed as an MCP server, providing a **`search` tool** with semantic search functionality accessible via MCP protocol.

## 🏗️ Architecture

For the full system architecture and components overview, check the [Architecture Guide](./ARCHITECTURE.md).

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose

### Installation

1. Clone and setup:

   ```bash
   git clone <repository-url>
   cd markdown-rag-mcp
   ```

2. Start Milvus database:

   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

3. Install dependencies using [uv](https://docs.astral.sh/uv/)

   ```bash
   uv sync
   ```

4. Install the package:

   ```bash
   pip install -e .
   ```

### Basic Usage

#### CLI Interface

```bash
# Index documents (with optional monitoring)
markdown-rag-mcp index ./documents --recursive --watch

# Semantic search with confidence scoring
markdown-rag-mcp search "authentication setup" --limit 5

# System health monitoring
markdown-rag-mcp status
```

For the full overview of the CLI interface, check the [CLI Guide](./CLI.md).

#### Demo Scripts

```bash
# Experience incremental indexing with performance metrics
python examples/incremental_indexing_demo.py --setup --runs 5

# Complete RAG pipeline demonstration
python examples/milvus_embeddings_demo.py
```

For the full list of demo scripts, check the [Examples Guide](./examples/README.md).

## 🔧 Configuration

Configure via environment variables or `.env` file, you can use `.env.example` for some defaults:

```bash
# Vector Database Configuration
MARKDOWN_RAG_MCP_MILVUS_HOST=localhost
MARKDOWN_RAG_MCP_MILVUS_PORT=19530
MARKDOWN_RAG_MCP_COLLECTION_NAME=markdown_docs

# Embedding Model Settings
MARKDOWN_RAG_MCP_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MARKDOWN_RAG_MCP_EMBEDDING_DEVICE=auto  # cpu, cuda, mps, auto
MARKDOWN_RAG_MCP_EMBEDDING_DIMENSIONS=384

# Search and Processing
MARKDOWN_RAG_MCP_SIMILARITY_THRESHOLD=0.7
MARKDOWN_RAG_MCP_CHUNK_SIZE_LIMIT=1000
MARKDOWN_RAG_MCP_CHUNK_OVERLAP=200
MARKDOWN_RAG_MCP_MAX_CONCURRENT_INDEXING=2

# File Monitoring
MARKDOWN_RAG_MCP_WATCH_DEBOUNCE_SECONDS=2
MARKDOWN_RAG_MCP_WATCH_PATTERNS="**/*.md,**/*.markdown"
```

## 📁 Project Structure

```plaintext
markdown-rag-mcp/
├── src/markdown_rag_mcp/         # Core library implementation
│   ├── cli/                      # Command-line interface
│   ├── config/                   # Configuration management
│   ├── core/                     # RAG engine and interfaces
│   ├── embeddings/               # Embedding providers
│   ├── indexing/                 # Document processing pipeline
│   ├── models/                   # Data models and schemas
│   ├── monitoring/               # File system monitoring
│   ├── parsers/                  # Markdown and frontmatter parsing
│   ├── search/                   # Query processing and search
│   └── storage/                  # Vector database integration
├── tests/                        # Comprehensive test suite
├── examples/                     # Demo scripts
├── docker/                       # Docker Compose configuration
├── specs/                        # Technical specifications
└── documents/                    # Markdown documents for indexing and searching
```

## 🧪 Testing

To run the test suite, use the following commands:

```bash
# Run complete test suite
uv sync --all-extras
pytest

# Run specific component tests
pytest tests/indexing/ -v
pytest tests/search/ -v
pytest tests/embeddings/ -v
```

## 📚 Documentation

- [Architecture Guide](./ARCHITECTURE.md): Detailed system architecture and components overview
- [CLI Guide](./CLI.md): Command-line interface guide
- [Examples Guide](./examples/README.md): Demo scripts

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

---

**Built with ❤️ for developers who need intelligent, markdown-based document search capabilities**
