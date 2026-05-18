# Feature Specification: Markdown RAG System

**Feature Branch**: `001-markdown-rag-system`
**Created**: 2025-10-08
**Status**: Draft
**Input**: User description: "Build a Markdown-based Retrieval-Augmented Generation (RAG) system that processes and indexes a collection of Markdown files locally on the `./documents` directory.

The system should:

- Parse Markdown files, including headings, body text, and code blocks.
- Generate embeddings for semantic similarity search.
- Store document vectors in a local vector database using Milvus.
- Support query-based retrieval — given a natural language query, return the most relevant Markdown sections or files.
- Each Markdown file may include a frontmatter section that provides metadata to improve content understanding and retrieval. The frontmatter can contain fields such as:
  - `title`, `tags`, `topics`, `keywords`, and `summary`
  - `llm_hints` — additional metadata that helps large language models retrieve and reason about the file more effectively

The output should be a fully functional local retrieval pipeline that other components (such as MCP servers or LLM tools) can interface with."

## Clarifications

### Session 2025-10-08

- Q: What chunking strategy should the system use for dividing documents into searchable sections? → A: Hybrid approach (headings + size limits)
- Q: How should the system handle files that fail to process? → A: Skip failed files, log errors, continue processing others
- Q: What format should query results use when returned to external components? → A: JSON with section text, file path, confidence score, and section heading
- Q: How should the system behave when the vector database is unavailable? → A: Fail fast with clear error message to external components
- Q: How should the system determine which search results are relevant enough to return? → A: Use fixed similarity threshold >0.7 and return all matches above it

## User Scenarios & Testing

### User Story 1 - Query Relevant Documentation (Priority: P1)

As a developer or content creator, I want to search through my collection of Markdown documentation using natural language queries to find the most relevant information quickly and accurately.

**Why this priority**: This is the core value proposition - enabling semantic search across markdown content. Without this, the system provides no user value.

**Independent Test**: Can be fully tested by loading sample markdown files, running a natural language query like "how to configure authentication", and verifying that relevant sections are returned with confidence scores.

**Acceptance Scenarios**:

1. **Given** a collection of markdown files exists in `./documents` directory, **When** I query "authentication setup", **Then** the system returns all sections with similarity scores >0.7 ranked by semantic similarity
2. **Given** markdown files contain code blocks and explanations, **When** I search for "error handling patterns", **Then** the system returns both code examples and explanatory text that match the query
3. **Given** multiple files discuss similar topics, **When** I query a specific concept, **Then** results include the source file path and section location for each match

---

### User Story 2 - Frontmatter-Enhanced Search (Priority: P2)

As a content creator, I want the system to utilize optional frontmatter metadata in my markdown files to improve search accuracy and relevance, so that documents with structured metadata are more discoverable and contextually understood.

**Why this priority**: This enhances search quality by leveraging user-provided structured metadata, making the RAG system more intelligent when metadata is available while still functioning without it.

**Independent Test**: Can be tested by creating markdown files with frontmatter containing `title`, `tags`, `summary`, `topics`, `keywords`, and `llm_hints`, then verifying that queries return more relevant results for those files compared to files without frontmatter.

**Acceptance Scenarios**:

1. **Given** a markdown file with frontmatter containing `title` and `tags`, **When** I query related topics, **Then** the system returns this file with higher relevance scoring than files without metadata
2. **Given** a markdown file with `llm_hints` in frontmatter, **When** the system processes queries, **Then** it uses these hints to improve context understanding and result ranking
3. **Given** markdown files both with and without frontmatter, **When** the system indexes them, **Then** it processes both types successfully without requiring frontmatter to be present

---

### User Story 3 - Incremental Index Updates (Priority: P3)

As a user with a growing collection of documentation, I want the system to automatically detect when markdown files are added, modified, or deleted and update the search index accordingly without requiring full re-indexing.

**Why this priority**: This improves user experience by keeping the index current, but the system can function with manual indexing initially.

**Independent Test**: Can be tested by adding a new markdown file to the directory and verifying that subsequent searches can find content from the new file without manually triggering re-indexing.

**Acceptance Scenarios**:

1. **Given** the system is monitoring the `./documents` directory, **When** a new file is added, **Then** the file is automatically parsed and indexed for search
2. **Given** an existing indexed file is modified, **When** the file content changes, **Then** the system updates the corresponding vector embeddings and metadata
3. **Given** a file is deleted from the directory, **When** the system detects the change, **Then** the corresponding vectors and metadata are removed from the index

---

### Edge Cases

- When a markdown file has malformed syntax or cannot be parsed, the system skips the file, logs the error with file path and reason, and continues processing other files
- How does the system handle very large markdown files (>10MB)?
- When the vector database is unavailable or corrupted, the system returns clear error messages to external components without attempting complex recovery mechanisms
- How are duplicate or near-duplicate files handled in the index?
- What happens when embedding generation fails for specific content?

## Requirements

### Functional Requirements

- **FR-001**: System MUST parse markdown files in `./documents` directory including headings, body text, code blocks, and existing frontmatter
- **FR-002**: System MUST generate semantic embeddings for markdown content using a local embedding model, chunking documents by markdown headings with maximum chunk size of 1000 tokens (using sentence-transformers tokenizer) to ensure compatibility with embedding model context windows
- **FR-003**: System MUST store document vectors and metadata in a local vector database with similarity search capabilities
- **FR-004**: System MUST accept natural language queries and return results as JSON objects containing section text, file path, confidence score, and section heading, ranked by relevance, including only matches with similarity scores >0.7
- **FR-005**: System MUST parse and utilize existing YAML frontmatter when present, including `title`, `tags`, `summary`, `topics`, `keywords`, and `llm_hints` fields
- **FR-006**: System MUST function correctly with markdown files that have no frontmatter
- **FR-007**: System MUST provide a modular interface that can be consumed by external components (MCP servers, APIs)
- **FR-008**: System MUST maintain an index of processed files with timestamps for incremental updates
- **FR-009**: System MUST handle file system monitoring to detect changes in the `./documents` directory
- **FR-010**: System MUST skip files that cannot be processed, log detailed error information, and continue processing remaining files without halting the entire indexing operation
- **FR-011**: System implementation MUST follow Test-Driven Development (TDD) workflow with tests written first, verified to fail, then implementation written to pass tests per constitutional requirement III

### Key Entities

- **Markdown Document**: Represents a single `.md` file with its content, metadata, file path, and processing status
- **Document Section**: Represents a chunk of content created using heading boundaries with size limits, containing related paragraphs, code blocks, and text that can be independently indexed and retrieved
- **Vector Embedding**: Numerical representation of document sections used for semantic similarity search
- **Metadata Record**: Structured information about documents including parsed frontmatter fields (when present) and processing timestamps
- **Query Result**: JSON object containing section text, file path, confidence score, and section heading for each matching document section

## Success Criteria

### Measurable Outcomes

- **SC-001**: Files with frontmatter metadata show measurable improvement in search relevance compared to files without metadata (minimum 15% higher average confidence scores)
- **SC-002**: Query interface returns results with consistent relevance ranking across multiple similar queries (maximum 0.1 variance in confidence scores for semantically equivalent queries)
- **SC-003**: All implementation tasks have corresponding test tasks that are completed first and verified to fail before implementation begins

## Assumptions

- Users will primarily query in English language
- Markdown files follow standard CommonMark specification
- Local vector database (Milvus with Docker Compose) can be installed and configured
- Embedding model will be downloaded and run locally (no external API dependencies)
- File system has read/write permissions for the ./documents directory
- System will run on a development machine with sufficient resources for vector operations
