# Quickstart Guide: Markdown RAG Core Library

**Date**: 2025-10-08
**Prerequisites**: Docker, Python 3.12+, Git
**Estimated Time**: 15 minutes

## Overview

This guide will walk you through setting up and using the Markdown RAG core library to index and search your markdown documentation using semantic similarity.

The library provides a clean Python interface that can be easily integrated into applications, scripts, or future server implementations.

## Prerequisites Check

Ensure you have the required tools installed:

```bash
# Check Python version (3.12+ required)
python --version

# Check Docker
docker --version
docker-compose --version

# Check uv package manager
uv --version || pip install uv
```

## Step 1: Environment Setup

### 1.1 Clone and Enter Project

```bash
git clone <repository-url>
cd markdown-rag-mcp
git checkout 001-markdown-rag-system
```

### 1.2 Create Environment Configuration

Create `.env` file in project root:

```bash
cat > .env << EOF
# Milvus Vector Database Configuration
MARKDOWN_RAG_MCP_MILVUS_HOST=localhost
MARKDOWN_RAG_MCP_MILVUS_PORT=19530

# Local Embedding Configuration
MARKDOWN_RAG_MCP_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MARKDOWN_RAG_MCP_EMBEDDING_DEVICE=auto  # "cpu", "cuda", "mps", or "auto"

# Optional: Custom configuration
MARKDOWN_RAG_MCP_SIMILARITY_THRESHOLD=0.7
MARKDOWN_RAG_MCP_CHUNK_SIZE_LIMIT=1000
EOF
```

### 1.3 Start Vector Database Services

```bash
# Start Milvus ecosystem (etcd, MinIO, Milvus)
docker-compose up -d

# Wait for all services to be ready (takes ~60 seconds)
docker-compose logs -f milvus
# Wait for "Milvus server is ready to serve!"
```

## Step 2: Install and Configure

### 2.1 Install Package Dependencies

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### 2.2 Initialize Vector Database and Embedding Model

```bash
# Initialize Milvus collections and download embedding model
markdown-rag-mcp config init

# Verify setup (this will download the embedding model on first run)
markdown-rag-mcp status --format json
```

Expected output:

```json
{
  "milvus": {
    "status": "connected",
    "total_documents": 0,
    "total_sections": 0,
    "collections": ["document_vectors", "document_metadata"]
  },
  "embedding_model": {
    "status": "loaded",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "device": "cpu",
    "dimensions": 384
  }
}
```

## Step 3: Prepare Sample Documentation

### 3.1 Create Sample Markdown Files

```bash
# Create documents directory
mkdir -p ./documents

# Create sample authentication guide
cat > ./documents/auth-guide.md << 'EOF'
---
title: Authentication Guide
tags: [auth, setup, security]
topics: [authentication, configuration]
summary: Complete guide for setting up authentication in your application
llm_hints: This document covers OAuth2, JWT tokens, and session management
---

# Authentication Guide

## OAuth2 Setup

To configure OAuth2 authentication:

1. Register your application with the OAuth provider
2. Set up redirect URIs in your application settings
3. Configure environment variables:

```bash
export OAUTH_CLIENT_ID=your_client_id
export OAUTH_CLIENT_SECRET=your_client_secret
```

## JWT Token Configuration

JWT tokens provide stateless authentication:

```python
import jwt

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

## Session Management

For traditional session-based authentication:

- Store sessions in Redis for scalability
- Set appropriate session timeouts
- Implement session cleanup mechanisms
EOF

# Create sample API documentation

cat > ./documents/api-docs.md << 'EOF'
---

title: API Documentation
tags: [api, endpoints, rest]
topics: [api-design, http-methods]
summary: REST API endpoints and usage examples
---

# API Documentation

## User Endpoints

### GET /api/users

Retrieve user information:

```http
GET /api/users/{user_id}
Authorization: Bearer {jwt_token}
```

Response:

```json
{
  "id": "123",
  "username": "john_doe",
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### POST /api/users

Create new user:

```http
POST /api/users
Content-Type: application/json

{
  "username": "new_user",
  "email": "user@example.com",
  "password": "secure_password"
}
```

## Error Handling

API returns standard HTTP status codes:

- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error
EOF

```

### 3.2 Verify File Structure

```bash
# Check created files
tree ./documents
```

Expected structure:

```plaintext
./documents/
├── auth-guide.md
└── api-docs.md
```

## Step 4: Index Your Documentation

### 4.1 Run Initial Indexing

```bash
# Index all markdown files in ./documents directory
markdown-rag-mcp index ./documents --format json
```

Expected output:

```json
{
  "status": "success",
  "indexed_files": 2,
  "failed_files": 0,
  "processing_time": "3.2s",
  "errors": []
}
```

### 4.2 Verify Indexing Results

```bash
# Check system status
markdown-rag-mcp status --detailed --format json
```

You should see:

- `total_documents: 2`
- `total_sections: 6-8` (depending on document structure)
- `total_embeddings: 6-8`

## Step 5: Search Your Documentation

### 5.1 Basic Search Examples

```bash
# Search for authentication information
markdown-rag-mcp search "how to set up OAuth2" --format human

# Search for API endpoints
markdown-rag-mcp search "user API endpoints" --limit 3

# Search with metadata included
markdown-rag-mcp search "JWT tokens" --include-metadata --format json
```

### 5.2 Advanced Search Examples

```bash
# Search with custom similarity threshold
markdown-rag-mcp search "error handling" --threshold 0.6

# Search and pipe to jq for processing
markdown-rag-mcp search "authentication" --format json | jq '.results[0].file_path'

# Multiple search terms
markdown-rag-mcp search "session management security" --limit 5
```

## Step 6: Enable File Monitoring (Optional)

### 6.1 Start Continuous Monitoring

```bash
# Start monitoring in background
markdown-rag-mcp index ./documents --watch &

# Monitor process ID for later stopping
MONITOR_PID=$!
echo "Monitoring process: $MONITOR_PID"
```

### 6.2 Test Live Updates

```bash
# Add new content to existing file
cat >> ./documents/auth-guide.md << 'EOF'

## Security Best Practices

1. Always use HTTPS in production
2. Implement rate limiting for auth endpoints
3. Use strong, unique secrets for JWT signing
4. Regularly rotate authentication keys
EOF

# Check that new content is indexed (wait ~30 seconds)
sleep 30
markdown-rag-mcp search "security best practices"
```

### 6.3 Stop Monitoring

```bash
# Stop background monitoring
kill $MONITOR_PID
```

## Step 7: Core Library Integration Examples

### 7.1 Basic Library Usage

Create `test_core_library.py`:

```python
import asyncio
from markdown_rag_mcp.core import RAGEngine
from markdown_rag_mcp.config import RAGConfig

async def test_core_library():
    # Method 1: Use configuration object
    config = RAGConfig()
    rag = RAGEngine(config=config)

    # Method 2: Direct initialization
    # rag = RAGEngine(
    #     milvus_host="localhost",
    #     milvus_port=19530,
    #     embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    #     similarity_threshold=0.7
    # )

    # Search programmatically
    results = await rag.search("JWT authentication", limit=3)

    print("Search Results:")
    for result in results:
        print(f"Score: {result.confidence_score:.3f}")
        print(f"File: {result.file_path}")
        print(f"Section: {result.section_heading}")
        print("---")

# Run the test
asyncio.run(test_core_library())
```

Run the integration test:

```bash
python test_core_library.py
```

### 7.2 Library Extension Pattern

Create `extended_usage.py` to demonstrate extensibility:

```python
import asyncio
from markdown_rag_mcp.core import RAGEngine, IRAGEngine
from typing import Dict, List, Any

class CustomRAGWrapper:
    """Example of extending RAG functionality for specific use cases."""

    def __init__(self, core_engine: IRAGEngine):
        self.core = core_engine

    async def search_with_summary(self, query: str) -> Dict[str, Any]:
        """Enhanced search with result summarization."""
        results = await self.core.search(query, limit=5)

        # Custom processing
        total_chars = sum(len(r.section_text) for r in results)
        avg_score = sum(r.confidence_score for r in results) / len(results) if results else 0

        return {
            "query": query,
            "summary": {
                "total_results": len(results),
                "average_score": round(avg_score, 3),
                "total_content_chars": total_chars
            },
            "results": [
                {
                    "content": result.section_text[:200] + "..." if len(result.section_text) > 200 else result.section_text,
                    "file": result.file_path.split("/")[-1],  # Just filename
                    "score": result.confidence_score,
                    "heading": result.section_heading
                }
                for result in results
            ]
        }

async def demo_extension():
    """Demonstrate library extension capabilities."""
    # Initialize core engine
    core_engine = RAGEngine()

    # Wrap with custom functionality
    extended_rag = CustomRAGWrapper(core_engine)

    # Use extended functionality
    enhanced_results = await extended_rag.search_with_summary("authentication patterns")
    print(f"Found {enhanced_results['summary']['total_results']} results")
    print(f"Average confidence: {enhanced_results['summary']['average_score']}")

# Run extension demo
asyncio.run(demo_extension())
```

This pattern shows how the core library can be extended for specific use cases without modifying the core implementation.

### 7.2 JSON Output Processing

```bash
# Extract all unique file paths from search results
markdown-rag-mcp search "API" --format json | \
  jq -r '.results[] | .file_path' | sort -u

# Get confidence scores above 0.8
markdown-rag-mcp search "authentication" --format json | \
  jq '.results[] | select(.confidence_score > 0.8) | {file: .file_path, score: .confidence_score}'

# Count results per file
markdown-rag-mcp search "configuration" --format json | \
  jq '.results | group_by(.file_path) | map({file: .[0].file_path, count: length})'
```

## Troubleshooting

### Common Issues

#### Milvus Connection Failed

```bash
# Check if all Milvus services are running
docker-compose ps

# Check Milvus logs
docker-compose logs milvus

# Check etcd and MinIO services
docker-compose logs etcd
docker-compose logs minio

# Restart all services
docker-compose restart
```

#### Embedding Model Errors

```bash
# Check if model directory exists
ls -la ~/.cache/huggingface/

# Clear model cache if corrupted
rm -rf ~/.cache/huggingface/transformers/

# Re-initialize to re-download model
markdown-rag-mcp config init --force
```

#### No Search Results

```bash
# Check if files are indexed
markdown-rag-mcp status --detailed

# Verify similarity threshold
markdown-rag-mcp search "your query" --threshold 0.5

# Re-index with force flag
markdown-rag-mcp index ./documents --force
```

#### Permission Errors

```bash
# Check file permissions
ls -la ./documents/

# Fix permissions if needed
chmod -R 755 ./documents/
```

### Getting Help

```bash
# Show command help
markdown-rag-mcp --help
markdown-rag-mcp search --help

# Show configuration
markdown-rag-mcp config show

# Validate configuration
markdown-rag-mcp validate ./documents
```

## Next Steps

1. **Scale Up**: Add your actual documentation to `./documents`
2. **Customize**: Adjust similarity thresholds and embedding models in configuration
3. **Integrate**: Use the Python library API in your applications
4. **Monitor**: Set up continuous file monitoring for live documentation
5. **Extend**: Build MCP server integration for Claude Code or other tools

## Performance Tips

- **Batch Indexing**: Use `--force` flag only when necessary to avoid re-processing unchanged files
- **Similarity Tuning**: Start with 0.7 threshold, lower to 0.5-0.6 for broader results
- **File Organization**: Use meaningful directory structure and frontmatter for better search results
- **Hardware Acceleration**: Set `MARKDOWN_RAG_MCP_EMBEDDING_DEVICE=cuda` if you have a GPU for faster embeddings
- **Resource Management**: Monitor Milvus memory usage and embedding model cache size
- **Index Optimization**: Tune Milvus index parameters (nlist, nprobe) for your dataset size

You now have a fully functional, completely local Markdown RAG system! The system will automatically chunk your documents using heading boundaries, generate embeddings locally, and provide fast semantic search capabilities without any external API dependencies.
