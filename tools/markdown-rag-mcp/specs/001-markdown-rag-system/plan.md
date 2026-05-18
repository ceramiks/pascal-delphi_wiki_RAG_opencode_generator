# Implementation Plan: Markdown RAG System

**Branch**: `001-markdown-rag-system` | **Date**: 2025-10-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-markdown-rag-system/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a modular Markdown RAG core library that processes and indexes markdown files locally, enabling semantic search through natural language queries.

The system uses local HuggingFace embeddings and Milvus vector database, providing clean Python interfaces and CLI tools.

Focus on library modularity to enable easy future integration with any external interface (MCP servers, APIs, etc.) without including those interfaces in this implementation.

## Technical Context

**Language/Version**: Python 3.12.0
**Primary Dependencies**: LangChain (RAG workflows), HuggingFaceEmbeddings (local embeddings), python-frontmatter (markdown parsing), Milvus (vector database), Docker & Docker Compose (containerization)
**Storage**: Milvus vector database with etcd/MinIO dependencies for vector embeddings and metadata
**Testing**: pytest for testing, Docker for containerized testing
**Target Platform**: Linux development environment with Docker support
**Project Type**: Single core library with CLI interface, designed for future extensibility
**Performance Goals**: <3s query response for 1000 files, <30s indexing for new/modified files
**Constraints**: >0.7 similarity threshold, 10GB collection support, local-only processing
**Scale/Scope**: Support up to 1000 markdown files, modular architecture for future interface integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Library-First Architecture

- **PASS**: Pure core library design with clear functional boundaries
- **PASS**: Self-contained with minimal, well-defined dependencies (LangChain, HuggingFaceEmbeddings, Milvus)
- **PASS**: Single, specific purpose: Markdown document RAG processing
- **PASS**: No server components - pure library with programmatic interfaces

### ✅ II. CLI Interface Standard

- **PASS**: CLI exposes library functionality following stdin/arguments → stdout protocol
- **PASS**: JSON and human-readable output formats planned
- **PASS**: CLI serves as reference implementation for library usage

### ✅ III. Test-First Development

- **PASS**: pytest framework specified for comprehensive testing
- **PASS**: Contract testing planned for library interfaces
- **PASS**: TDD workflow enforced during implementation

### ✅ IV. MCP Protocol Compliance (Future-Ready)

- **PASS**: Modular design enables future MCP server development
- **PASS**: Clean library interfaces designed for external consumption
- **PASS**: No MCP-specific code in core library (future extension point)

### ✅ V. Documentation-Driven Design

- **PASS**: Comprehensive library documentation and usage examples
- **PASS**: API contracts define clear interfaces
- **PASS**: Quickstart focuses on library integration patterns

**Gate Result**: ✅ **APPROVED** - Core library architecture satisfies all constitutional requirements

## Project Structure

### Documentation (this feature)

```plaintext
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```plaintext
src/
├── markdown_rag_mcp/               # Core library package
│   ├── __init__.py                 # Main library exports
│   ├── core/                       # Core RAG functionality
│   │   ├── __init__.py
│   │   ├── rag_engine.py           # Main RAG orchestration class
│   │   └── interfaces.py           # Abstract interfaces for extensibility
│   ├── models/                     # Data models and schemas
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── exceptions.py
│   │   └── query.py
│   ├── parsers/                     # Document parsing components
│   │   ├── __init__.py
│   │   ├── markdown_parser.py
│   │   └── frontmatter_parser.py
│   ├── indexing/                    # Document processing and chunking
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   ├── indexer.py
│   │   ├── incremental_indexer.py
│   │   ├── change_detector.py
│   │   └── metadata_enhancer.py
│   ├── embeddings/                  # Embedding generation components
│   │   ├── __init__.py
│   │   ├── embedder.py
│   │   └── langchain_adapter.py
│   ├── storage/                     # Vector database abstraction
│   │   ├── __init__.py
│   │   ├── milvus_store.py
│   ├── search/                      # Query processing and retrieval
│   │   ├── __init__.py
│   │   ├── query_processor.py
│   ├── monitoring/                  # File system monitoring
│   │   ├── __init__.py
│   │   ├── file_watcher.py
│   │   └── monitoring_coordinator.py
│   ├── cli/                         # Command-line interface
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   └── main.py
│   └── config/                      # Configuration management
│       ├── __init__.py
│       └── settings.py

tests/                         # Unit tests for library components
├── indexing/
├── embeddings/
├── models/
└── parsers/
└── config/
└── storage/
└── search/
└── monitoring/

docker/                             # Containerization setup
├── docker-compose.yml              # Milvus + dependencies
└── Dockerfile.dev                  # Development environment

examples/                           # Library usage examples (Comprehensive demos implemented)
├── milvus_embeddings_demo.py       # Full RAG system demonstration
├── markdown_parsing_demo.py        # Document parsing examples
├── incremental_indexing_demo.py    # Incremental update functionality
├── file_watcher_demo.py            # File monitoring capabilities
├── file_monitoring_demo.py              # System monitoring features
└── README.md                       # Examples documentation

pyproject.toml                      # Package configuration
README.md                           # Library documentation
```

**Structure Decision**: Pure library architecture with clear separation between core functionality, CLI interface, and future extension points.

The `core/interfaces.py` module defines abstract interfaces that future MCP servers or APIs can implement without modifying core library code.

CLI serves as both a user tool and reference implementation for library usage patterns.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
