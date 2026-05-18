# Data Model: Markdown RAG System

**Date**: 2025-10-09
**Version**: 1.0.0
**Storage**: Milvus vector database + File system

## Overview

The Markdown RAG system uses Milvus vector database for storing document embeddings and metadata, with the filesystem serving as the source of truth for markdown content. The data model supports semantic similarity search through 384-dimensional vectors while maintaining document structure and metadata relationships.

## Core Entities

### Document

Represents a single markdown file in the system.

**Attributes**:

- `file_path`: Absolute path to the markdown file (primary identifier)
- `content_hash`: SHA-256 hash of file content for change detection
- `file_size`: Size in bytes
- `created_at`: File creation timestamp
- `modified_at`: File last modification timestamp
- `indexed_at`: When the file was last processed for indexing
- `processing_status`: Current processing state
- `error_message`: Error details if processing failed
- `frontmatter`: Parsed YAML frontmatter (optional)
- `word_count`: Total word count in document
- `section_count`: Number of sections created from document

**States**: `pending` → `processing` → `indexed` | `failed`

### 2. DocumentSection

**Purpose**: Represents a chunk of content created using heading boundaries with size limits, containing related paragraphs, code blocks, and text that can be independently indexed and retrieved

**Attributes**:

- `id`: UUID (primary key)
- `document_id`: UUID (foreign key to MarkdownDocument)
- `section_text`: str (processed text content)
- `heading`: str (section heading, nullable)
- `heading_level`: int (H1=1, H2=2, etc., nullable)
- `chunk_index`: int (order within document, starting at 0)
- `token_count`: int (approximate token count for the section)
- `start_position`: int (character position in original document)
- `end_position`: int (character position in original document)
- `section_type`: enum (heading, paragraph, code_block, list, table)
- `created_at`: timestamp

**Validation Rules**:

- `token_count` must be ≤ 1000 tokens (chunking limit)
- `chunk_index` must be unique per document
- `start_position` < `end_position`
- `heading_level` must be 1-6 if not null

**Relationships**:

- Many-to-one with MarkdownDocument
- One-to-one with VectorEmbedding

### 3. VectorEmbedding

**Purpose**: Numerical representation of document sections used for semantic similarity search

**Attributes**:

- `id`: UUID (primary key)
- `section_id`: UUID (foreign key to DocumentSection)
- `embedding`: vector (384 dimensions for HuggingFace sentence-transformers)
- `embedding_model`: str (model identifier, e.g., "all-MiniLM-L6-v2")
- `similarity_threshold`: float (0.7 as per specification)
- `created_at`: timestamp

**Validation Rules**:

- `embedding` must have exactly 384 dimensions
- `similarity_threshold` must be between 0.0 and 1.0
- `embedding_model` must be from approved list of HuggingFace models

**Relationships**:

- One-to-one with DocumentSection

### 4. MetadataRecord

**Purpose**: Structured information about documents including parsed frontmatter fields (when present) and processing timestamps

**Attributes**:

- `id`: UUID (primary key)
- `document_id`: UUID (foreign key to MarkdownDocument)
- `title`: str (from frontmatter or auto-generated, nullable)
- `tags`: list[str] (from frontmatter, nullable)
- `summary`: str (from frontmatter, nullable)
- `topics`: list[str] (from frontmatter, nullable)
- `keywords`: list[str] (from frontmatter, nullable)
- `llm_hints`: str (from frontmatter, nullable)
- `language`: str (detected/specified language, default "en")
- `word_count`: int (total words in document)
- `section_count`: int (number of sections created)
- `has_frontmatter`: bool (whether document contains frontmatter)
- `created_at`: timestamp
- `updated_at`: timestamp

**Validation Rules**:

- `title` length ≤ 255 characters if present
- `summary` length ≤ 1000 characters if present
- `tags`, `topics`, `keywords` arrays ≤ 50 items each
- `word_count` and `section_count` must be ≥ 0

**Relationships**:

- Many-to-one with MarkdownDocument

### 5. QueryResult

**Purpose**: JSON object containing section text, file path, confidence score, and section heading for each matching document section

**Attributes**:

- `section_text`: str (matching section content)
- `file_path`: str (absolute path to source file)
- `confidence_score`: float (similarity score, 0.0-1.0)
- `section_heading`: str (heading context, nullable)
- `heading_level`: int (H1-H6 level, nullable)
- `metadata`: dict (relevant frontmatter fields)
- `chunk_index`: int (position within document)

**Validation Rules**:

- `confidence_score` must be > 0.7 (similarity threshold)
- Results must be ordered by `confidence_score` descending
- `section_text` must not be empty

**Note**: QueryResult is a response object, not persisted in database

## Milvus Collections Schema

### Collection: `document_vectors`

Stores semantic embeddings and core section metadata.

```python
from pymilvus import CollectionSchema, FieldSchema, DataType

fields = [
    FieldSchema(name="section_id", dtype=DataType.VARCHAR, max_length=255, is_primary=True),
    FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1000),
    FieldSchema(name="section_heading", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="heading_level", dtype=DataType.INT8),
    FieldSchema(name="chunk_index", dtype=DataType.INT32),
    FieldSchema(name="token_count", dtype=DataType.INT32),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
]

schema = CollectionSchema(
    fields=fields,
    description="Document section embeddings for semantic search"
)

# Index configuration
index_params = {
    "metric_type": "IP",  # Inner product for normalized embeddings
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}
```

### Collection: document_metadata

**Purpose**: Supplementary collection storing document-level metadata and processing information

**Schema Definition**:

```python
metadata_fields = [
    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
    FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
    FieldSchema(name="file_hash", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="file_size", dtype=DataType.INT64),
    FieldSchema(name="processing_status", dtype=DataType.VARCHAR, max_length=20),
    FieldSchema(name="frontmatter", dtype=DataType.JSON),  # YAML frontmatter as JSON
    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=255),
    FieldSchema(name="tags", dtype=DataType.JSON),  # Array of strings
    FieldSchema(name="summary", dtype=DataType.VARCHAR, max_length=1000),
    FieldSchema(name="topics", dtype=DataType.JSON),  # Array of strings
    FieldSchema(name="keywords", dtype=DataType.JSON),  # Array of strings
    FieldSchema(name="llm_hints", dtype=DataType.VARCHAR, max_length=1000),
    FieldSchema(name="language", dtype=DataType.VARCHAR, max_length=10),
    FieldSchema(name="word_count", dtype=DataType.INT32),
    FieldSchema(name="section_count", dtype=DataType.INT32),
    FieldSchema(name="has_frontmatter", dtype=DataType.BOOL),
    FieldSchema(name="created_at", dtype=DataType.INT64),
    FieldSchema(name="updated_at", dtype=DataType.INT64),
    FieldSchema(name="indexed_at", dtype=DataType.INT64),
    FieldSchema(name="error_message", dtype=DataType.VARCHAR, max_length=1000)
]

metadata_schema = CollectionSchema(
    fields=metadata_fields,
    description="Document metadata and processing status"
)
```

### Connection and Collection Management

**Milvus Connection Configuration**:

```python
from pymilvus import connections, Collection

# Connection setup
connections.connect(
    alias="default",
    host="localhost",
    port="19530"
)

# Collection initialization
def initialize_collections():
    """Create collections if they don't exist"""

    # Document vectors collection
    if not utility.has_collection("document_vectors"):
        document_vectors = Collection(
            name="document_vectors",
            schema=schema
        )
        document_vectors.create_index(
            field_name="embedding",
            index_params=index_params
        )

    # Document metadata collection
    if not utility.has_collection("document_metadata"):
        document_metadata = Collection(
            name="document_metadata",
            schema=metadata_schema
        )

    return document_vectors, document_metadata
```

## State Transitions

### Document Processing Lifecycle

```plaintext
pending → processing → indexed (success)
          ↓
          failed (error)
```

### File Change Detection

```plaintext
File Added/Modified → Hash Comparison → Reprocessing (if changed)
File Deleted → Cascade Delete (sections, embeddings, metadata)
```

## Indexes and Performance

### Primary Indexes

- `document_vectors.embedding` (IVF_FLAT index for cosine similarity search)
- `document_metadata.file_path` (automatic indexing for file lookups)
- `document_metadata.file_hash` (for change detection)

### Query Patterns

- **Similarity search**:

  ```python
  search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
  results = collection.search(
      data=[query_vector],
      anns_field="embedding",
      param=search_params,
      limit=10
  )
  ```

- **File monitoring**:

  ```python
  results = metadata_collection.query(
      expr=f'file_hash != "{calculated_hash}"',
      output_fields=["document_id", "file_path"]
  )
  ```

- **Metadata filtering**:

  ```python
  results = metadata_collection.query(
      expr='JSON_CONTAINS_ANY(tags, ["tag1", "tag2"])',
      output_fields=["document_id", "title"]
  )
  ```

## Error Handling

### Data Integrity

- Milvus schema validation ensures data type compliance
- Application-level validation for data ranges and formats
- Transactional operations for atomic updates
- Manual cleanup procedures for orphaned data

### Processing Failures

- Failed documents retain error messages in metadata collection
- Partial processing uses transaction rollback when possible
- Failed files are skipped without blocking other processing
- Collection recovery procedures for corrupted data

### Milvus-Specific Error Handling

- Connection timeout and retry mechanisms
- Collection loading state management
- Index building failure recovery
- Memory management for large batch operations
