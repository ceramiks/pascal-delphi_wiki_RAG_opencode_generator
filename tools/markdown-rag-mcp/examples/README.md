# Markdown RAG Examples

This directory contains comprehensive demonstration scripts showcasing all features of the Markdown RAG system. Each demo is a fully interactive command-line application with rich output, detailed help, and educational value.

## Available Demos

### 1. File Monitoring Demo (`file_monitoring_demo.py`)

**Real-time file monitoring and automatic index updates**

Demonstrates the complete monitoring system with live file change detection and automatic index synchronization.

- Real-time file change detection (create, modify, delete)
- Automatic index synchronization with debounced event processing
- Live statistics and performance monitoring with rich terminal UI
- Manual scan capabilities for on-demand updates
- Interactive testing with sample file generation

**Usage:**

```bash
# Run with default settings (60 seconds, ./test_markdown directory)
python examples/file_monitoring_demo.py

# Monitor specific directory for 2 minutes with sample creation
python examples/file_monitoring_demo.py -d /path/to/docs -t 120 -s

# Create samples and run with verbose output
python examples/file_monitoring_demo.py -s -v -t 30
```

**Expected Output:**

```plaintext
🎯 Markdown RAG Monitoring System Demo

🔍 File Monitoring & Automatic Index Updates Demo
This demo showcases the monitoring system capabilities including:
• Real-time file change detection (create, modify, delete)
• Automatic index synchronization
• Debounced event processing to avoid duplicate work
• Live statistics and performance monitoring
• Manual scan capabilities for on-demand updates

📁 Watching: ./test_markdown | ⏱️  Duration: 60s

🚀 Initializing Markdown RAG Components
✅ All components initialized successfully!

📝 Creating Sample Files
Creating files... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
✅ Created 3 sample markdown files in ./test_markdown

🔍 Starting monitoring with initial directory scan...
📁 Initial directory scan: found 3 markdown files
✅ Monitoring started successfully!

📝 How to Test
Testing Instructions:

1. Create a new .md file in ./test_markdown
2. Modify an existing .md file in ./test_markdown
3. Delete a .md file from ./test_markdown
4. Watch the live statistics update below!

⏱️  Monitoring active (15/60s) ━━━━━━━━━━━━░░░░░░░░░░░░░░░░░░ 25% 0:00:15

✅ Processed modified operation for: ./test_markdown/sample1.md
✅ Processed created operation for: ./test_markdown/new_file.md

📊 Real-time Monitoring Statistics
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric             ┃ Value         ┃ Details                      ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 📁 Files Processed │ 5             │ Total indexed files          │
│ ➕ Created          │ 1             │ New files indexed            │
│ ✏️  Modified        │ 1             │ Updated files                │
│ 🗑️  Deleted         │ 0             │ Removed from index           │
│ ⚠️  Failed          │ 0             │ Processing errors            │
│ ⏳ Pending Events   │ 0             │ Queued file changes          │
└────────────────────┴───────────────┴──────────────────────────────┘

🛑 Stopping monitoring...
✅ Monitoring stopped successfully!
🎉 Demo completed successfully!
```

### 2. Markdown Parsing Demo (`markdown_parsing_demo.py`)

**Comprehensive markdown processing with frontmatter integration**

Showcases advanced document processing capabilities including YAML frontmatter parsing and content analysis.

- YAML frontmatter parsing and metadata extraction
- Document structure analysis (headers, sections, content)
- Mixed format field processing (strings, lists, tags)
- Unicode content support including emojis
- Error handling for malformed frontmatter and edge cases
- Performance analysis with detailed parsing statistics

**Usage:**

```bash
# Create samples and run comprehensive demo
python examples/markdown_parsing_demo.py --setup

# Run with existing files in custom directory
python examples/markdown_parsing_demo.py -d /path/to/markdown/files

# Verbose output with samples
python examples/markdown_parsing_demo.py -s -v
```

**Expected Output:**

```plaintext
📄 Markdown Parsing & Frontmatter Integration Demo
This demo showcases advanced markdown processing capabilities including:
• YAML frontmatter parsing and metadata extraction
• Document structure analysis (headers, sections, content)
• Content chunking with semantic boundary detection
• Metadata enhancement for improved search relevance
• Error handling for malformed frontmatter
• Mixed format field processing (strings, lists, tags)
• Performance analysis and parsing statistics

📁 Directory: ./test_markdown | 🔧 Parser: MarkdownParser + FrontmatterParser

📝 Creating 8 sample markdown files...
   ✅ Created: basic_with_frontmatter.md
   ✅ Created: simple_with_basic_frontmatter.md
   ✅ Created: complex_frontmatter.md
   ✅ Created: no_frontmatter.md
   ✅ Created: malformed_frontmatter.md
   ✅ Created: empty_frontmatter.md
   ✅ Created: mixed_format_frontmatter.md
   ✅ Created: unicode_content.md
✅ All sample files created in ./test_markdown

📊 Processing 8 markdown files...

═══════════════ Rich Frontmatter ═══════════════

📖 Document: basic_with_frontmatter.md
============================================================
📄 File Info:
   Size: 2847 bytes | Words: 389 | Modified: 2024-10-19 15:23
   Hash: 7f4a6b2c8e9d...

📋 Frontmatter (8 fields):
   title: Complete Guide to Markdown RAG System
   tags: ['guide', 'documentation', 'rag', 'search']
   topics: ['implementation', 'architecture', 'best-practices']
   keywords: ['markdown', 'parsing', 'frontmatter', 'search', 'retrieval']
   summary: A comprehensive guide covering the implementation and usage...
   llm_hints: ['context', 'semantic-search', 'document-processing']
   author: Development Team
   difficulty: intermediate

📝 Content Preview:
   # Complete Guide to Markdown RAG System  ## Overview  Welcome to the comprehensive guide for our Markdown RAG system! It provides detailed information...

═══════════════ Simple Cases ═══════════════

📖 Document: mixed_format_frontmatter.md
============================================================
📄 File Info:
   Size: 1256 bytes | Words: 142 | Modified: 2024-10-19 15:23

📋 Frontmatter (5 fields):
   title: Mixed Format Example
   tags: ['mixed', 'formats', 'example']
   topics: ['list', 'format']
   keywords: ['mixed', 'formats', 'example']
   summary: Demonstrates mixed frontmatter field formats

═══════════════ Special Cases ═══════════════

📖 Document: unicode_content.md
============================================================
📄 File Info:
   Size: 1892 bytes | Words: 178 | Modified: 2024-10-19 15:23

📋 Frontmatter (5 fields):
   title: Unicode Content Test 测试文档
   tags: ['unicode', 'test', '测试', 'français', 'español']
   summary: Testing Unicode support in both frontmatter and content
   keywords: ['unicode', '测试', 'français', 'español', '🌍']
   topics: ['internationalization', 'i18n', 'testing']

═══════════════ Edge Cases ═══════════════

📖 Document: malformed_frontmatter.md
============================================================
❌ Parsing failed: YAMLError
   Error: mapping values are not allowed here in "<unicode string>", line 3, column 18...

═══════════════ PARSING STATISTICS ═══════════════

📊 Overall Results:
   Files processed: 7/8
   Files with frontmatter: 6
   Total words parsed: 1,847
   Total frontmatter fields: 42
   Average fields per frontmatter file: 7.0
   Success rate: 87.5%

═══════════════ SPECIAL FEATURES & CAPABILITIES ═══════════════

1️⃣ Frontmatter Field Processing:
   ✅ Automatic field cleaning: comma-separated → lists
   ✅ Unsupported fields filtered out
   ✅ Mixed data types handled gracefully

2️⃣ Unicode Content Support:
   ✅ Unicode in frontmatter: True
   ✅ Unicode in content: True
   ✅ Emojis supported: True

3️⃣ Error Handling & Resilience:
   ✅ Non-existent file: FileNotFoundError handled properly
   ✅ File type validation: unsupported files filtered

4️⃣ Content Analysis & Hashing:
   ✅ SHA-256 content hashing: 7f4a6b2c8e9d...
   ✅ Word count analysis: 389 words
   ✅ File metadata extraction: size, timestamps

🎉 ══════════ DEMONSTRATION COMPLETE ══════════

✨ Summary:
   • Successfully parsed 7/8 markdown files
   • Processed files with/without frontmatter seamlessly
   • Validated and cleaned 42 frontmatter fields
   • Analyzed 1,847 words of content

📁 Sample files remain in: ./test_markdown
```

### 3. Incremental Indexing Demo (`incremental_indexing_demo.py`)

**Intelligent incremental indexing with change detection**

Demonstrates smart change detection and selective processing across multiple indexing runs.

- Content-based change detection using SHA-256 file hashing
- Incremental processing of only modified files
- Automatic handling of file create/update/delete operations
- Performance optimization through selective reprocessing
- Change detection state management and persistence
- Batch vs. single file processing demonstrations

**Usage:**

```bash
# Run basic demo with 3 indexing runs
python examples/incremental_indexing_demo.py

# Setup test documents and run 5 iterations
python examples/incremental_indexing_demo.py -s -r 5

# Use custom directory with verbose logging
python examples/incremental_indexing_demo.py -d /path/to/docs -v
```

**Expected Output:**

```plaintext
🔄 Demonstrate incremental indexing functionality of the Markdown RAG system

This script shows how the system efficiently detects changes in markdown files and
updates the search index incrementally, avoiding unnecessary reprocessing of unchanged documents.

🔧 Setting up demonstration environment...
Creating test documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00

📂 Test Files Created
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ File                                 ┃ Size                ┃ Hash    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ introduction.md                      │ 847 bytes           │ a4b9c7... │
│ getting_started.md                   │ 1,234 bytes         │ e8f2a1... │
│ advanced_topics.md                   │ 1,567 bytes         │ 3d7e9f... │
│ api_reference.md                     │ 2,134 bytes         │ b6c8d4... │
└──────────────────────────────────────┴─────────────────────┴─────────┘

🚀 ======================== INDEXING RUN 1 ========================

🔍 Scanning directory: ./test_incremental
📊 Change Detection Summary:
   • Files scanned: 4
   • New files: 4
   • Modified files: 0
   • Deleted files: 0
   • Unchanged files: 0

⚙️ Processing Documents:
Indexing documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:02
✅ Indexed: introduction.md (0.485s)
✅ Indexed: getting_started.md (0.521s)
✅ Indexed: advanced_topics.md (0.672s)
✅ Indexed: api_reference.md (0.843s)

📈 Indexing Results for Run 1
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value         ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Status              │ success       │
│ Files Scanned       │ 4             │
│ Changes Detected    │ 4             │
│ Files Processed     │ 4             │
│ Processing Time     │ 2.521s        │
│ Sections Generated  │ 12            │
└─────────────────────┴───────────────┘

🚀 ======================== INDEXING RUN 2 ========================

✏️ Simulating file modifications...
   Modified: introduction.md (updated timestamp: 2024-10-19 15:24:15)
   Created: new_document_run_2.md (948 bytes)

🔍 Scanning directory: ./test_incremental
📊 Change Detection Summary:
   • Files scanned: 5
   • New files: 1
   • Modified files: 1
   • Deleted files: 0
   • Unchanged files: 3

⚙️ Processing Documents:
Indexing documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
✅ Indexed: introduction.md (0.312s) [MODIFIED]
✅ Indexed: new_document_run_2.md (0.398s) [NEW]
⏭️ Skipped: getting_started.md (unchanged)
⏭️ Skipped: advanced_topics.md (unchanged)
⏭️ Skipped: api_reference.md (unchanged)

📈 Indexing Results for Run 2
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value         ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Status              │ success       │
│ Files Scanned       │ 5             │
│ Changes Detected    │ 2             │
│ Files Processed     │ 2             │
│ Processing Time     │ 0.710s        │
│ Sections Generated  │ 5             │
│ Time Saved          │ 72% faster    │
└─────────────────────┴───────────────┘

🚀 ======================== INDEXING RUN 3 ========================

✏️ Simulating file modifications...
   Deleted: getting_started.md
   Created: final_document_run_3.md (1,156 bytes)

🔍 Scanning directory: ./test_incremental
📊 Change Detection Summary:
   • Files scanned: 5
   • New files: 1
   • Modified files: 0
   • Deleted files: 1
   • Unchanged files: 3

⚙️ Processing Documents:
Indexing documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
✅ Indexed: final_document_run_3.md (0.445s) [NEW]
🗑️ Removed: getting_started.md (deleted)
⏭️ Skipped: introduction.md (unchanged)
⏭️ Skipped: advanced_topics.md (unchanged)
⏭️ Skipped: api_reference.md (unchanged)
⏭️ Skipped: new_document_run_2.md (unchanged)

📊 Final Performance Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Run                     ┃ Files     ┃ Processed ┃ Time      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 1 (Initial)             │ 4         │ 4 (100%)  │ 2.521s    │
│ 2 (Incremental)         │ 5         │ 2 (40%)   │ 0.710s    │
│ 3 (Incremental)         │ 5         │ 1 (20%)   │ 0.445s    │
└─────────────────────────┴───────────┴───────────┴───────────┘

💡 Efficiency Gained: Incremental indexing processed only 25% of files across
   runs 2-3, resulting in 78% average time savings compared to full reprocessing.

🎉 Incremental Indexing Demo completed successfully!
```

### 4. Milvus Embeddings Demo (`milvus_embeddings_demo.py`)

**Complete RAG pipeline with real-world document processing**

Comprehensive demonstration of the full RAG system including embeddings, vector storage, and semantic search.

- Document indexing with markdown parsing and frontmatter processing
- Embedding generation with HuggingFace transformers
- Vector storage and retrieval with Milvus database
- Semantic search across document collections with confidence scoring
- Performance monitoring and detailed error handling
- Real-world scenarios: technical docs, knowledge base search, content similarity

**Usage:**

```bash
# Run complete RAG system demonstration (requires Milvus)
python examples/milvus_embeddings_demo.py
```

**Prerequisites:**

```bash
# Start Milvus server
docker-compose up -d
```

**Expected Output:**

```plaintext
🚀 Milvus Store & Embeddings Provider Integration Demo
This demo showcases real-world RAG system capabilities including:
• Document parsing and indexing
• Embedding generation and storage
• Semantic search and retrieval
• Performance monitoring

🚀 Initializing Markdown RAG Components
⠋ Initializing HuggingFace embedder...
✅ Initialized HuggingFace embedder
⠋ Setting up LangChain adapter...
✅ Set up LangChain adapter
⠋ Connecting to Milvus vector store...
✅ Connected to Milvus vector store
⠋ Setting up markdown parser...
✅ Set up markdown parser
⠋ Initializing document indexer...
✅ Initialized document indexer
⠋ Setting up query processor...
✅ Set up query processor
✅ All components initialized successfully!

Component Information
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Component           ┃ Model/Configuration                   ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ HuggingFace Embedder│ sentence-transformers/all-MiniLM-L6-v2 (cpu) │ ✅ Ready │
│ Vector Store        │ Milvus (localhost:19530)             │ ✅ Connected │
│ Embedding Dimension │ 384                                   │ ✅ Configured │
└─────────────────────┴───────────────────────────────────────┴───────────┘

📝 Creating Sample Documents
Creating documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
✅ Created 5 sample documents in /tmp/rag_demo_8x9k2l

🧠 Demonstrating Embedding Generation
Testing single text embedding...
✅ Generated embedding: dimension=384, time=0.143s
Testing batch embedding generation...
✅ Generated 4 embeddings in 0.287s
Average time per embedding: 0.072s
Testing LangChain adapter compatibility...
✅ LangChain adapter working: sync/async difference=0.000000

Embedding Analysis
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric                             ┃ Value         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Embedding Dimension                │ 384           │
│ Single Embedding Avg Magnitude    │ 0.0847        │
│ Batch Embeddings Avg Magnitude    │ 0.0823        │
│ Batch Size                         │ 4             │
└────────────────────────────────────┴───────────────┘

📚 Demonstrating Document Indexing
Indexing documents... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:03
✅ Indexed: python_best_practices.md (0.842s)
✅ Indexed: microservices_architecture.md (0.731s)
✅ Indexed: machine_learning_deployment.md (0.945s)
✅ Indexed: database_optimization.md (0.673s)
✅ Indexed: api_design_principles.md (0.589s)
📊 Indexing completed: 5 documents in 3.780s

🔍 Demonstrating Semantic Search

🔍 Database optimization query
Query: How to optimize database performance?
Found 3 relevant results (0.234s)
  1. Database Performance Optimization (score: 0.847)
     # Database Performance Optimization  ## Indexing Strategies  ### B-Tree Indexes - Default index type for most databases - Excellent for equality and range queries...
  2. Machine Learning Model Deployment (score: 0.623)
     # Machine Learning Model Deployment  ## Deployment Strategies  ### Blue-Green Deployment - Maintain two identical production environments - Switch traffic between...
  3. RESTful API Design Principles (score: 0.578)
     # RESTful API Design Principles  ## Resource-Oriented Design  ### URL Structure - Use nouns for resources, not verbs - Maintain consistent naming conventions...

🔍 Programming best practices query
Query: Best practices for Python development
Found 3 relevant results (0.198s)
  1. Python Development Best Practices (score: 0.892)
     # Python Development Best Practices  ## Code Organization  ### Project Structure - Use clear, descriptive package and module names - Separate business logic from...
  2. Machine Learning Model Deployment (score: 0.634)
     # Machine Learning Model Deployment  ## Deployment Strategies  ### Blue-Green Deployment - Maintain two identical production environments - Switch traffic between...
  3. Microservices Architecture Guide (score: 0.601)
     # Microservices Architecture  ## Core Principles  ### Single Responsibility Each service should have one business capability and own its data...

🔍 MLOps deployment query
Query: Deploying machine learning models to production
Found 3 relevant results (0.187s)
  1. Machine Learning Model Deployment (score: 0.924)
     # Machine Learning Model Deployment  ## Deployment Strategies  ### Blue-Green Deployment - Maintain two identical production environments - Switch traffic between...
  2. Microservices Architecture Guide (score: 0.687)
     # Microservices Architecture  ## Core Principles  ### Single Responsibility Each service should have one business capability and own its data...
  3. Database Performance Optimization (score: 0.543)
     # Database Performance Optimization  ## Indexing Strategies  ### B-Tree Indexes - Default index type for most databases - Excellent for equality and range queries...

🔍 Architecture design query
Query: Microservices communication patterns
Found 3 relevant results (0.176s)
  1. Microservices Architecture Guide (score: 0.873)
     # Microservices Architecture  ## Core Principles  ### Single Responsibility Each service should have one business capability and own its data...
  2. RESTful API Design Principles (score: 0.729)
     # RESTful API Design Principles  ## Resource-Oriented Design  ### URL Structure - Use nouns for resources, not verbs - Maintain consistent naming conventions...
  3. Python Development Best Practices (score: 0.567)
     # Python Development Best Practices  ## Code Organization  ### Project Structure - Use clear, descriptive package and module names - Separate business logic from...

🔍 API security query
Query: RESTful API authentication and security
Found 3 relevant results (0.203s)
  1. RESTful API Design Principles (score: 0.891)
     # RESTful API Design Principles  ## Resource-Oriented Design  ### URL Structure - Use nouns for resources, not verbs - Maintain consistent naming conventions...
  2. Microservices Architecture Guide (score: 0.632)
     # Microservices Architecture  ## Core Principles  ### Single Responsibility Each service should have one business capability and own its data...
  3. Database Performance Optimization (score: 0.498)
     # Database Performance Optimization  ## Indexing Strategies  ### B-Tree Indexes - Default index type for most databases - Excellent for equality and range queries...

🎯 Completed 5 semantic searches

📈 Performance Analysis

RAG System Performance Metrics
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric                 ┃ Value         ┃ Unit      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Documents Created      │ 5             │ files     │
│ Documents Indexed      │ 5             │ files     │
│ Embeddings Generated   │ 12            │ vectors   │
│ Searches Performed     │ 5             │ queries   │
│                        │               │           │
│ Avg Embedding Time     │ 0.076         │ seconds   │
│ Avg Indexing Time     │ 0.756         │ seconds   │
│ Avg Search Time       │ 0.200         │ seconds   │
│ Total Processing Time  │ 4.567         │ seconds   │
└────────────────────────┴───────────────┴───────────┘

💡 Performance Insights
✅ Embedding generation is highly optimized
✅ Search performance is excellent

🧹 Cleaned up temporary directory: /tmp/rag_demo_8x9k2l

🎉 Demo completed successfully!
```

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -e .
   ```

2. **Start Milvus (for vector store demos):**

   ```bash
   docker-compose up -d
   ```

3. **Run any demo with help:**

   ```bash
   python examples/<demo_name>.py --help
   ```

4. **Try the monitoring demo (interactive):**

   ```bash
   python examples/file_monitoring_demo.py -s -t 60
   ```

### Troubleshooting

**Import Errors:**

```bash
# Ensure you're in the project root
ls src/  # Should show markdown_rag_mcp

# Install in development mode
pip install -e .
```

**Milvus Connection:**

```bash
# Check Milvus is running
docker ps | grep milvus

# Start if needed
docker-compose up -d
```
