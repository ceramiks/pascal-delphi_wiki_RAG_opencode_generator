# Technology Research: Markdown RAG System

**Date**: 2025-10-09
**Feature**: Markdown RAG System
**Purpose**: Research findings for technology decisions and implementation patterns

## 1. LangChain Integration for Embeddings & Vector Storage

**Decision**: Use LangChain's unified interface with HuggingFace embeddings and Milvus vector store

**Rationale**:

- Provides abstraction layer for embedding models and vector stores
- Built-in vector store integrations including Milvus
- Standardized document loading and text splitting pipelines
- Local embeddings eliminate external API dependencies
- Simplified model switching without code changes

**Implementation Considerations**:

- Use `langchain_milvus.Milvus` for vector database integration
- Leverage `langchain_huggingface.HuggingFaceEmbeddings` for local embeddings
- Implement `langchain.text_splitter.MarkdownHeaderTextSplitter` for chunk boundaries
- Use `langchain.schema.Document` for consistent document representation

**Alternatives Considered**:

- Direct Milvus integration: Rejected due to lack of embedding provider abstraction
- OpenAI embeddings: Rejected to maintain local-only requirement

## 2. Milvus Vector Database Configuration

**Decision**: Milvus 2.3+ with etcd and MinIO dependencies in Docker container

**Rationale**:

- Purpose-built vector database with high-performance similarity search
- Built-in support for various vector index types (IVF, HNSW)
- Automatic scaling and collection management
- Native Python SDK with LangChain integration
- Docker Compose deployment with all dependencies

**Implementation Considerations**:

- Use collection schema with 384 dimensions (HuggingFace sentence-transformers standard)
- Configure IVF_FLAT index for balanced performance/accuracy
- Set up etcd for metadata storage and MinIO for object storage
- Implement automatic collection creation and schema validation
- Use connection pooling for concurrent operations

**Alternatives Considered**:

- Chroma: Rejected due to less mature ecosystem and fewer indexing options
- FAISS: Rejected due to lack of distributed capabilities and metadata management

## 3. Markdown & Frontmatter Parsing

**Decision**: Use `python-frontmatter` + `markdown-it-py` for parsing

**Rationale**:

- `python-frontmatter`: Robust YAML frontmatter extraction with error handling
- `markdown-it-py`: Fast CommonMark parser with extensive plugin ecosystem
- Both libraries handle edge cases (malformed frontmatter, syntax errors)
- Active maintenance and good performance characteristics

**Implementation Considerations**:

- Parse frontmatter first with `frontmatter.load()`
- Use `markdown-it-py` with heading extraction for chunk boundaries
- Handle encoding detection with `chardet` for various file sources
- Implement graceful degradation for malformed files

**Alternatives Considered**:

- `mistune`: Rejected due to less flexible frontmatter handling
- `markdown` (Python-Markdown): Rejected due to slower performance on large documents

## 4. Document Chunking Strategy

**Decision**: Hybrid approach using markdown headings with size limits

**Rationale**:

- Preserves semantic document structure via headings
- Size limits prevent chunks from exceeding embedding model context windows
- Maintains context relationships between headings and content
- Aligns with specification requirement for hybrid chunking

**Implementation Considerations**:

- Split on H1, H2, H3 headers as primary boundaries
- Maximum chunk size: 1000 tokens (safe for most embedding models)
- Include heading hierarchy in chunk metadata for context
- Handle code blocks as atomic units to preserve syntax

**Alternatives Considered**:

- Fixed-size chunking: Rejected due to loss of semantic structure
- Paragraph-only chunking: Rejected due to inconsistent chunk sizes

## 5. Local Embedding Model Selection

**Decision**: HuggingFace sentence-transformers with 'all-MiniLM-L6-v2' model

**Rationale**:

- Fully local execution without external API dependencies
- 384-dimensional embeddings optimized for semantic similarity
- Fast inference suitable for real-time document processing
- Excellent performance on English text and technical content
- LangChain has native HuggingFaceEmbeddings integration

**Implementation Considerations**:

- Use `sentence-transformers/all-MiniLM-L6-v2` model for balanced performance/size
- Implement model caching to avoid repeated downloads
- Configure batch processing for multiple documents
- Enable GPU acceleration if available (CUDA/MPS)
- Set up automatic model downloading during first run

**Alternatives Considered**:

- OpenAI embeddings: Rejected to maintain local-only requirement
- Larger models (all-mpnet-base-v2): Rejected due to slower inference
- BERT-based models: Rejected due to inferior performance on similarity tasks

## 6. Docker Containerization Pattern

**Decision**: Docker Compose with Milvus ecosystem containers

**Rationale**:

- Consistent development environment across machines
- Complete Milvus setup with etcd and MinIO dependencies
- Volume mounting for development code changes
- Simple scaling for future multi-service architecture
- Automatic service orchestration and health checking

**Implementation Considerations**:

- Use official Milvus image with etcd and MinIO services
- Python 3.12 slim image for application container
- Persistent volumes for vector data and model cache
- Health checks and dependency management between services
- Network configuration for inter-service communication

**Container Architecture**:

```yaml
# docker-compose.yml structure
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment: ETCD configuration for Milvus metadata
    ports: 2379:2379

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment: MinIO configuration for Milvus object storage
    ports: 9001:9001

  milvus:
    image: milvusdb/milvus:v2.3-latest
    depends_on: [etcd, minio]
    ports: 19530:19530
    volumes: ./milvus:/var/lib/milvus

  app:
    build: ./docker/Dockerfile.dev
    depends_on: [milvus]
    volumes:
      - ./src:/app/src
      - ./models:/app/models  # HuggingFace model cache
```

**Alternatives Considered**:

- Single container: Rejected due to complexity of managing Milvus dependencies
- Local installation: Rejected due to Milvus setup complexity
- Milvus Standalone: Chosen over cluster mode for development simplicity

## 7. Modular Architecture Design

**Decision**: Core library with abstract interfaces for future extensibility

**Rationale**:

- Clean separation between core RAG functionality and external interfaces
- Abstract base classes enable future MCP server, API, or other interface development
- Library-first approach allows multiple interface implementations
- Dependency inversion principle ensures core logic remains interface-agnostic
- Easy testing and validation of core functionality independent of interfaces

**Implementation Considerations**:

- Define `IRAGEngine` interface in `core/interfaces.py` for main orchestration
- Abstract `IVectorStore`, `IEmbeddingProvider`, `IDocumentParser` interfaces
- Core `RAGEngine` class implements business logic using dependency injection
- CLI implementation serves as reference for future interface developers
- Clear separation between library exports and internal implementation details

**Interface Design Pattern**:

```python
# Abstract interfaces for extensibility
class IRAGEngine(ABC):
    @abstractmethod
    async def index_directory(self, path: str) -> IndexResult: ...

    @abstractmethod
    async def search(self, query: str, limit: int) -> List[SearchResult]: ...

# Core implementation
class RAGEngine(IRAGEngine):
    def __init__(self, vector_store: IVectorStore, embedder: IEmbeddingProvider):
        # Dependency injection for testability and extensibility
```

**Alternatives Considered**:

- Monolithic design with embedded interfaces: Rejected due to tight coupling
- Plugin architecture: Rejected as unnecessarily complex for initial scope
- Framework-specific design: Rejected to maintain technology agnosticism

## Summary

The updated technology stack provides a fully local, self-contained foundation for the Markdown RAG system. Using HuggingFace embeddings eliminates external API dependencies, while Milvus offers superior vector search performance compared to traditional databases.

The modular architecture with abstract interfaces enables future extension to MCP servers or APIs without modifying core library code.

The Docker Compose setup ensures consistent development environments and simplified deployment.

All decisions align with the constitutional requirements for library-first design and external integration capabilities.
