# Architecture Guide

This document provides an overview of the Markdown RAG MCP system architecture, component relationships, data flows, and system interactions.

## 🏗️ System Overview

The architecture is organized into five distinct layers:

- **Input Layer**: Handles raw markdown files and YAML frontmatter extraction
- **Processing Pipeline**: Transforms documents through parsing, chunking, enhancement, and embedding
- **Storage Layer**: Manages vector embeddings and change tracking in Milvus database
- **Search Layer**: Provides semantic search capabilities with query processing and ranking
- **Interface Layer**: Exposes functionality through CLI, Python library, and MCP server interfaces

```mermaid
graph TB
    subgraph "Input Layer"
        MD[Markdown Files]
        YML[YAML Frontmatter]
    end

    subgraph "Processing Pipeline"
        PARSER[Markdown Parser]
        CHUNK[Document Chunker]
        ENHANCE[Metadata Enhancer]
        EMBED[HuggingFace Embedder]
    end

    subgraph "Storage Layer"
        MILVUS[(Milvus Vector DB)]
        INDEX[Change Index]
    end

    subgraph "Search Layer"
        QP[Query Processor]
        SEARCH[Semantic Search]
    end

    subgraph "Interface Layer"
        CLI[CLI Interface]
        LIB[Python Library]
        MCP[MCP Server]
    end

    MD --> PARSER
    YML --> PARSER
    PARSER --> CHUNK
    CHUNK --> ENHANCE
    ENHANCE --> EMBED
    EMBED --> MILVUS

    QP --> SEARCH
    SEARCH --> MILVUS

    CLI --> QP
    LIB --> QP
    MCP --> QP

    PARSER --> INDEX
    INDEX --> CHUNK
```

## 📊 Component Architecture

### 1. Core Components

The [`RAGEngine`](src/markdown_rag_mcp/core/rag_engine.py) class orchestrates all system operations.

- **Component Initialization**: Starts up all required services in the correct order
- **Operation Coordination**: Routes indexing and search requests to appropriate components
- **Resource Management**: Handles connection pooling, memory usage, and cleanup
- **Error Orchestration**: Coordinates error handling across all components
- **Status Monitoring**: Provides system health and performance metrics

#### Document Indexing Pipeline

The indexing pipeline transforms markdown documents into searchable vector embeddings through a multi-stage process:

1. **Document Indexer**: Coordinates the entire indexing workflow
2. **Incremental Indexer**: Optimizes performance by only processing changed files
3. **Change Detection**: Tracks file modifications using content hashes and timestamps

**Processing Flow:**

- Files are scanned for changes using hash comparison
- Changed files are parsed to extract content and frontmatter metadata
- Documents are chunked into semantically meaningful sections
- Metadata enhancement enriches chunks with contextual information
- Embeddings are generated using HuggingFace transformer models
- Results are stored in Milvus vector database with metadata indexing

#### Query Processing System

The search system provides semantic search capabilities that go beyond simple keyword matching:

1. **Query Preprocessing**: Cleans and normalizes user queries
2. **Embedding Generation**: Converts queries to vector representations
3. **Similarity Search**: Performs vector similarity search in Milvus
4. **Result Ranking**: Applies confidence thresholds and metadata boosting
5. **Response Formatting**: Structures results with highlights and context

```mermaid
classDiagram
    class RAGEngine {
        -config: RAGConfig
        -indexer: IDocumentIndexer
        -searcher: IQueryProcessor
        -embedder: IEmbeddingProvider
        -monitor: IMonitoringCoordinator
        +initialize() Promise~void~
        +index_directory(path: str) Promise~IndexResult~
        +search(query: str, options: SearchOptions) Promise~SearchResult[]~
        +start_monitoring(path: str) Promise~void~
        +get_status() SystemStatus
    }

    class IDocumentIndexer {
        <<interface>>
        +index_file(path: Path) Promise~IndexResult~
        +index_directory(path: Path, recursive: bool) Promise~IndexResult~
        +get_indexed_count() int
    }

    class DocumentIndexer {
        -parser: IMarkdownParser
        -chunker: IDocumentChunker
        -enhancer: IMetadataEnhancer
        -store: IVectorStore
        -change_detector: IChangeDetector
        +index_file(path: Path) Promise~IndexResult~
        +index_directory(path: Path, recursive: bool) Promise~IndexResult~
    }

    class IncrementalIndexer {
        -base_indexer: IDocumentIndexer
        -change_detector: IChangeDetector
        +index_with_changes(path: Path) Promise~IndexResult~
        +detect_changes(path: Path) List~FileChange~
    }

    class IQueryProcessor {
        <<interface>>
        +search(query: str, options: SearchOptions) Promise~SearchResult[]~
        +preprocess_query(query: str) str
        +rank_results(results: List~SearchResult~) List~SearchResult~
    }

    class QueryProcessor {
        -embedder: IEmbeddingProvider
        -store: IVectorStore
        -config: SearchConfig
        +search(query: str, options: SearchOptions) Promise~SearchResult[]~
        +semantic_search(embedding: List~float~) Promise~SearchResult[]~
    }

    RAGEngine --> IDocumentIndexer
    RAGEngine --> IQueryProcessor
    IDocumentIndexer <|.. DocumentIndexer
    IDocumentIndexer <|.. IncrementalIndexer
    IQueryProcessor <|.. QueryProcessor
    DocumentIndexer --> IncrementalIndexer : composition
```

### 2. Document Processing Pipeline

The document processing pipeline transforms raw markdown files into semantically enriched, searchable content.

#### Markdown Parser

The [`MarkdownParser`](src/markdown_rag_mcp/parsers/markdown_parser.py) is responsible for extracting and structuring content from markdown files.

- **File Validation**: Ensures files are readable and within size limits
- **Content Parsing**: Extracts plain text while preserving structural elements
- **Hash Calculation**: Generates content hashes for change detection
- **Metadata Extraction**: Coordinates frontmatter parsing and enrichment

**Frontmatter Processing:**
The integrated [`FrontmatterParser`](src/markdown_rag_mcp/parsers/frontmatter_parser.py) handles YAML frontmatter extraction.

- Supports standard fields: title, tags, description, author, date
- Cleans and normalizes field values

#### Document Chunker

The [`DocumentChunker`](src/markdown_rag_mcp/indexing/chunker.py) intelligently segments documents into semantically coherent chunks.

**Chunking Strategy:**

1. **Header-Based Splitting**: Respects markdown heading hierarchy (#, ##, ###)
2. **Size Management**: Ensures chunks stay within embedding model limits
3. **Context Preservation**: Maintains section relationships and hierarchy
4. **Overlap Handling**: Provides configurable overlap between chunks for context

#### Metadata Enhancer

The [`MetadataEnhancer`](src/markdown_rag_mcp/indexing/metadata_enhancer.py) augments document chunks with contextual metadata to improve search quality.

**Enhancement Techniques:**

1. **Frontmatter Integration**: Blends YAML metadata into chunk content
2. **Field Weighting**: Applies configurable weights to different metadata fields
3. **Content Boosting**: Increases relevance of content with rich metadata
4. **Semantic Context**: Adds document-level context to individual chunks

```mermaid
classDiagram
    class IMarkdownParser {
        <<interface>>
        +parse_file(path: Path) Promise~Document~
        +parse_content(content: str) Document
        +validate_file(path: Path) bool
    }

    class MarkdownParser {
        -frontmatter_parser: IFrontmatterParser
        -config: ParserConfig
        +parse_file(path: Path) Promise~Document~
        +extract_metadata(path: Path) Metadata
        +calculate_hash(content: str) str
    }

    class IFrontmatterParser {
        <<interface>>
        +extract_frontmatter(content: str) Dict~str, Any~
        +validate_fields(frontmatter: Dict) Dict~str, Any~
        +clean_field_values(value: Any) Any
    }

    class FrontmatterParser {
        -supported_fields: Set~str~
        +extract_frontmatter(content: str) Dict~str, Any~
        +parse_yaml_block(yaml_str: str) Dict~str, Any~
    }

    class IDocumentChunker {
        <<interface>>
        +chunk_document(document: Document) List~DocumentSection~
        +chunk_content(content: str, metadata: Metadata) List~DocumentSection~
        +calculate_chunk_size(content: str) int
    }

    class DocumentChunker {
        -config: ChunkConfig
        -splitter_strategy: ISplitterStrategy
        +chunk_document(document: Document) List~DocumentSection~
        +split_by_headers(content: str) List~str~
        +ensure_size_limits(chunks: List~str~) List~str~
    }

    class IMetadataEnhancer {
        <<interface>>
        +enhance_chunks(chunks: List~DocumentSection~, metadata: Metadata) List~DocumentSection~
        +create_enhanced_content(chunk: DocumentSection, metadata: Metadata) str
        +weight_metadata_fields(metadata: Metadata) Dict~str, float~
    }

    class MetadataEnhancer {
        -config: EnhancementConfig
        -field_weights: Dict~str, float~
        +enhance_chunks(chunks: List~DocumentSection~, metadata: Metadata) List~DocumentSection~
        +apply_frontmatter_boost(content: str, frontmatter: Dict) str
    }

    IMarkdownParser <|.. MarkdownParser
    IFrontmatterParser <|.. FrontmatterParser
    IDocumentChunker <|.. DocumentChunker
    IMetadataEnhancer <|.. MetadataEnhancer

    MarkdownParser --> IFrontmatterParser
    DocumentIndexer --> IMarkdownParser
    DocumentIndexer --> IDocumentChunker
    DocumentIndexer --> IMetadataEnhancer
```

### 3. Monitoring and Change Detection

The monitoring system provides real-time change detection of file system changes, enabling automatic index updates and maintaining data freshness without manual intervention.

#### File Watcher

The [`FileWatcher`](src/markdown_rag_mcp/monitoring/file_watcher.py) component provides low-level file system monitoring.

**Event Processing:**

1. **File System Events**: Captures create, modify, delete, and move operations
2. **Debounce Logic**: Waits for file operations to stabilize before processing
3. **Pattern Matching**: Applies inclusion/exclusion rules to filter relevant files
4. **Error Recovery**: Handles file system errors gracefully with automatic retry

#### Monitoring Coordinator

The [`MonitoringCoordinator`](src/markdown_rag_mcp/monitoring/monitoring_coordinator.py) manages the overall monitoring workflow.

**Operational Modes:**

- **Active Monitoring**: Real-time processing of file changes
- **Batch Mode**: Periodic scanning for environments with limited resources
- **Hybrid Mode**: Combines real-time events with periodic validation scans

#### Change Detector

The [`DocumentChangeDetector`](src/markdown_rag_mcp/indexing/change_detector.py) provides change detection.

**Change Detection Methods:**

1. **Content Hash Comparison**: Fast detection using SHA-256 file hashes
2. **Timestamp Analysis**: Secondary validation using file modification times
3. **Size Comparison**: Quick elimination of obviously unchanged files
4. **Deep Content Analysis**: Detailed comparison when heuristics are inconclusive

**Index Management:**
The system maintains a persistent index of file states:

- File path, content hash, size, and modification timestamps
- Processing status and error information
- Statistics on processing time and success rates
- Automatic cleanup of stale entries for deleted files

```mermaid
classDiagram
    class IFileWatcher {
        <<interface>>
        +start_watching(path: Path, callback: Callable) Promise~void~
        +stop_watching() Promise~void~
        +add_path(path: Path) void
        +remove_path(path: Path) void
    }

    class FileWatcher {
        -observer: Observer
        -event_handler: FileSystemEventHandler
        -debounce_timer: Dict~str, Timer~
        -config: WatchConfig
        +start_watching(path: Path, callback: Callable) Promise~void~
        +handle_file_event(event: FileSystemEvent) void
        +debounce_event(path: str, callback: Callable) void
    }

    class IMonitoringCoordinator {
        <<interface>>
        +start_monitoring(paths: List~Path~) Promise~void~
        +stop_monitoring() Promise~void~
        +get_monitoring_status() MonitoringStatus
    }

    class MonitoringCoordinator {
        -file_watcher: IFileWatcher
        -incremental_indexer: IIncrementalIndexer
        -active_paths: Set~Path~
        -stats: MonitoringStats
        +handle_file_change(path: Path, event_type: str) Promise~void~
        +process_batch_changes(changes: List~FileChange~) Promise~void~
    }

    class IChangeDetector {
        <<interface>>
        +scan_directory(path: Path) List~FileChange~
        +detect_file_changes(path: Path) FileChange | None
        +update_file_index(path: Path, hash: str, modified_at: datetime) void
        +get_change_summary() ChangeSummary
    }

    class DocumentChangeDetector {
        -file_index: Dict~str, FileInfo~
        -config: ChangeDetectionConfig
        +scan_directory(path: Path) List~FileChange~
        +calculate_file_hash(path: Path) str
        +load_file_index() Dict~str, FileInfo~
        +save_file_index() void
    }

    IFileWatcher <|.. FileWatcher
    IMonitoringCoordinator <|.. MonitoringCoordinator
    IChangeDetector <|.. DocumentChangeDetector

    MonitoringCoordinator --> IFileWatcher
    MonitoringCoordinator --> IIncrementalIndexer
    IncrementalIndexer --> IChangeDetector
```

## 🔄 Data Flow Architecture

The data flow architecture illustrates how information moves through the system during key operations.

### 1. Document Indexing Flow

The document indexing process involves multiple components working in coordination to transform raw markdown files into searchable vector embeddings.

#### Processing Loop

For each file requiring indexing, the system executes a pipeline:

1. **Content Extraction**: The markdown parser extracts text content and YAML frontmatter
2. **Document Chunking**: Content is segmented into semantically coherent sections
3. **Metadata Enhancement**: Chunks are enriched with frontmatter and contextual information
4. **Embedding Generation**: HuggingFace models generate vector embeddings for each enhanced chunk
5. **Vector Storage**: Embeddings and metadata are stored in Milvus with appropriate indexing
6. **Change Tracking**: File hashes and processing timestamps are recorded for future change detection

```mermaid
sequenceDiagram
    participant CLI as CLI/Library
    participant RAG as RAG Engine
    participant IDX as Document Indexer
    participant PARSER as Markdown Parser
    participant CHUNK as Document Chunker
    participant ENHANCE as Metadata Enhancer
    participant EMBED as Embedding Provider
    participant STORE as Vector Store
    participant DETECT as Change Detector

    CLI->>RAG: index_directory(path, options)
    RAG->>IDX: index_directory(path, recursive=True)

    IDX->>DETECT: scan_directory(path)
    DETECT-->>IDX: List[FileChange]

    loop For each changed file
        IDX->>PARSER: parse_file(file_path)
        PARSER->>PARSER: extract_frontmatter()
        PARSER->>PARSER: calculate_content_hash()
        PARSER-->>IDX: Document(content, metadata, hash)

        IDX->>CHUNK: chunk_document(document)
        CHUNK->>CHUNK: split_by_headers()
        CHUNK->>CHUNK: ensure_size_limits()
        CHUNK-->>IDX: List[DocumentSection]

        IDX->>ENHANCE: enhance_chunks(chunks, metadata)
        ENHANCE->>ENHANCE: apply_frontmatter_boost()
        ENHANCE->>ENHANCE: weight_metadata_fields()
        ENHANCE-->>IDX: List[EnhancedDocumentSection]

        IDX->>EMBED: generate_embeddings(enhanced_chunks)
        EMBED->>EMBED: load_model() [if first call]
        EMBED->>EMBED: encode_batch(content_list)
        EMBED-->>IDX: List[List[float]]

        IDX->>STORE: store_documents(sections_with_embeddings)
        STORE->>STORE: upsert_vectors()
        STORE-->>IDX: StorageResult

        IDX->>DETECT: update_file_index(file_path, hash, modified_at)
    end

    IDX-->>RAG: IndexResult(total_files, processed_files, stats)
    RAG-->>CLI: IndexResult
```

### 2. Semantic Search Flow

The semantic search flow transforms user queries into meaningful results through vector similarity matching and intelligent ranking.

**Query Preparation:**
The search process begins with query preprocessing to optimize embedding quality:

- **Text Normalization**: Removes extraneous whitespace, standardizes encoding
- **Query Enhancement**: Expands abbreviations, corrects common typos
- **Context Addition**: Optionally adds search context based on user history

**Vector Similarity Search:**
The core search operation uses advanced vector mathematics:

1. **Query Embedding**: The preprocessed query is converted to a high-dimensional vector using the same model used for document indexing
2. **Vector Search**: Milvus performs efficient similarity search using cosine similarity or other configured distance metrics
3. **Initial Filtering**: Results are filtered based on minimum similarity thresholds
4. **Metadata Matching**: Additional filtering based on document metadata if specified

**Result Processing and Ranking:**
Raw similarity results are enhanced through intelligent ranking:

- **Confidence Scoring**: Converts similarity scores to confidence percentages
- **Metadata Boosting**: Increases scores for results with rich metadata or specific tags
- **Diversity Filtering**: Ensures result diversity by avoiding over-representation from single documents
- **Context Highlighting**: Identifies and formats relevant text passages for display

```mermaid
sequenceDiagram
    participant CLI as CLI/Library
    participant RAG as RAG Engine
    participant QP as Query Processor
    participant EMBED as Embedding Provider
    participant STORE as Vector Store
    participant RANK as Result Ranker

    CLI->>RAG: search(query, options)
    RAG->>QP: search(query, search_options)

    QP->>QP: preprocess_query(query)
    QP->>EMBED: generate_embedding(preprocessed_query)
    EMBED->>EMBED: encode_single(query_text)
    EMBED-->>QP: List[float] (query_embedding)

    QP->>STORE: similarity_search(query_embedding, options)
    STORE->>STORE: search_vectors(embedding, top_k, filters)
    STORE-->>QP: List[VectorSearchResult]

    QP->>RANK: rank_results(search_results, options)
    RANK->>RANK: apply_confidence_threshold()
    RANK->>RANK: sort_by_relevance()
    RANK->>RANK: apply_metadata_boost()
    RANK-->>QP: List[SearchResult]

    QP-->>RAG: List[SearchResult]
    RAG-->>CLI: SearchResponse(results, stats, query_info)
```

### 3. File System Monitoring Flow

The file system monitoring system ensures that the document index stays synchronized with the file system.

**Event Detection:**

- **File System Watchers**: Low-level OS integration captures file system events immediately
- **Event Filtering**: Only processes events for supported file types and paths
- **Debounce Processing**: Prevents processing of temporary or rapidly changing files

**Change Processing:**

1. **Event Validation**: Confirms that detected changes represent actual content modifications
2. **Priority Assignment**: Important files (frequently accessed, recently modified) receive higher processing priority
3. **Resource Management**: Limits concurrent processing to prevent system overload
4. **Error Recovery**: Implements retry logic for transient failures

#### Efficiency Optimizations

The monitoring system includes several performance optimizations:

**Event Debouncing:**

- Multiple rapid changes to the same file are consolidated into a single processing operation
- Configurable debounce windows (typically 2-5 seconds) balance responsiveness with efficiency
- Different debounce strategies for different file types and sizes

**Batching:**

- Related file changes (e.g., multiple files in the same directory) are processed together
- Batch processing reduces embedding model loading overhead
- Optimal batch sizes are determined based on available system resources

**False Positive Filtering:**
The system employs multiple techniques to avoid unnecessary processing:

- **Hash Comparison**: Quick elimination of files that haven't actually changed
- **Temporary File Detection**: Ignores editor temporary files and backup files
- **Size-Based Filtering**: Skips processing of very large or very small files
- **Extension Validation**: Only processes supported markdown file types

```mermaid
sequenceDiagram
    participant FS as File System
    participant WATCHER as File Watcher
    participant COORD as Monitoring Coordinator
    participant INCREMENTAL as Incremental Indexer
    participant DETECT as Change Detector
    participant INDEX as Document Indexer

    FS->>WATCHER: file_modified(path)
    WATCHER->>WATCHER: debounce_event(path, 2s)

    alt After debounce period
        WATCHER->>COORD: handle_file_change(path, "modified")
        COORD->>INCREMENTAL: process_file_change(path)

        INCREMENTAL->>DETECT: detect_file_changes(path)
        DETECT->>DETECT: calculate_file_hash(path)
        DETECT->>DETECT: compare_with_stored_hash()
        DETECT-->>INCREMENTAL: FileChange(path, "modified", old_hash, new_hash)

        alt File actually changed
            INCREMENTAL->>INDEX: index_file(path)
            INDEX-->>INCREMENTAL: IndexResult
            INCREMENTAL->>DETECT: update_file_index(path, new_hash, timestamp)
            INCREMENTAL-->>COORD: ProcessingResult(success=True)
        else File unchanged (false positive)
            INCREMENTAL-->>COORD: ProcessingResult(success=True, skipped=True)
        end

        COORD->>COORD: update_monitoring_stats()
    end
```

## 🔌 Data Models and Schemas

**Document Model:**
Represents the complete metadata and content information for a single markdown file:

- **Identity Fields**: Unique identifiers and file path references
- **Content Metadata**: Hash, size, word count, and timestamps for change tracking
- **Processing Status**: Tracks indexing status, error conditions, and processing statistics
- **Rich Metadata**: Stores extracted frontmatter and computed document properties

**DocumentSection Model:**
Represents individual chunks of documents created during the chunking process:

- **Hierarchy Information**: Section index, parent document, and structural relationships
- **Content Storage**: Original content, enhanced content with metadata integration
- **Vector Data**: High-dimensional embeddings and associated metadata
- **Positioning**: Character-level start/end positions within the source document

**Search and Query Models:**
**SearchResult**: Encapsulates search match information with confidence scoring and content highlighting
**QueryInfo**: Tracks query processing metadata, execution timing, and result statistics for analytics

**FileChange Model:**
Tracks file system modifications for incremental indexing:

- **Change Detection**: Captures change types (create, modify, delete, move)
- **Hash Comparison**: Stores old and new content hashes for validation
- **Processing Tracking**: Records processing status and error information
- **Temporal Data**: Timestamps for change detection and processing completion

**System Metrics Model:**
Provides comprehensive system monitoring and performance tracking:

- **Component Metrics**: Per-component performance and health statistics
- **Resource Usage**: Memory, CPU, and storage utilization measurements
- **Operation Timing**: Detailed timing information for all major operations
- **Error Analytics**: Error rates, types, and resolution statistics

### Data Relationships

The data model includes relationships:

- **Document-to-Section**: One-to-many relationship enabling efficient section retrieval
- **Query-to-Results**: Tracking relationship for search analytics and caching
- **File-to-Changes**: Historical change tracking for audit and rollback capabilities

```mermaid
erDiagram
    Document {
        string id PK
        string file_path
        string content_hash
        datetime created_at
        datetime modified_at
        int word_count
        int size_bytes
        string content
        json frontmatter
        json metadata
    }

    DocumentSection {
        string id PK
        string document_id FK
        int section_index
        string content
        string enhanced_content
        json metadata
        float[] embedding
        int start_char
        int end_char
        string section_type
    }

    FileChange {
        string file_path PK
        string change_type
        string old_hash
        string new_hash
        datetime detected_at
        datetime processed_at
        string status
    }

    SearchResult {
        string document_id FK
        string section_id FK
        float similarity_score
        float confidence_score
        string matched_content
        json metadata
        json highlights
    }

    QueryInfo {
        string query_id PK
        string query_text
        string processed_query
        float[] query_embedding
        datetime executed_at
        int result_count
        float execution_time_ms
    }

    SystemMetrics {
        string metric_id PK
        string component_name
        string metric_name
        float metric_value
        string metric_unit
        datetime recorded_at
        json additional_data
    }

    Document ||--o{ DocumentSection : "contains"
    Document ||--o{ SearchResult : "referenced_in"
    DocumentSection ||--o{ SearchResult : "matched_in"
    QueryInfo ||--o{ SearchResult : "produced"
```
