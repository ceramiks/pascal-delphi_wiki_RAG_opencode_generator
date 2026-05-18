#!/usr/bin/env python3
"""
Milvus Store and Embeddings Provider Integration Demo

This demo showcases real-world usage of the Markdown RAG system, demonstrating:
1. Document indexing with markdown parsing and frontmatter
2. Embedding generation with HuggingFace transformers
3. Vector storage and retrieval with Milvus
4. Semantic search across document collections
5. Performance monitoring and error handling

Real-world scenarios covered:
- Technical documentation indexing
- Knowledge base search
- Content similarity analysis
- Batch document processing
- Incremental updates
"""

import asyncio
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from markdown_rag_mcp.config import get_config
from markdown_rag_mcp.embeddings import HuggingFaceEmbedder, LangChainEmbeddingAdapter
from markdown_rag_mcp.indexing import DocumentIndexer
from markdown_rag_mcp.models import SearchRequest
from markdown_rag_mcp.parsers import MarkdownParser
from markdown_rag_mcp.search import QueryProcessor
from markdown_rag_mcp.storage import MilvusVectorStore
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, track
from rich.table import Table

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()


class MilvusEmbeddingsDemo:
    """Comprehensive demo of Milvus store and embeddings integration."""

    def __init__(self):
        """Initialize demo with configuration."""
        self.config = get_config()
        self.temp_dir = None

        # Components (will be initialized)
        self.embedder = None
        self.embedding_adapter = None
        self.vector_store = None
        self.document_parser = None
        self.document_indexer = None
        self.query_processor = None

        # Demo statistics
        self.stats = {
            'documents_created': 0,
            'documents_indexed': 0,
            'embeddings_generated': 0,
            'searches_performed': 0,
            'total_processing_time': 0,
            'embedding_time': 0,
            'storage_time': 0,
            'search_time': 0,
        }

    async def initialize_components(self):
        """Initialize all RAG components."""
        console.print("🚀 [bold blue]Initializing Markdown RAG Components[/bold blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Initialize embedder
            task1 = progress.add_task("Initializing HuggingFace embedder...", total=None)
            self.embedder = HuggingFaceEmbedder(self.config)
            await self.embedder.initialize()
            progress.update(task1, completed=True)

            # Initialize LangChain adapter
            task2 = progress.add_task("Setting up LangChain adapter...", total=None)
            self.embedding_adapter = LangChainEmbeddingAdapter(self.config)
            await self.embedding_adapter.initialize()
            progress.update(task2, completed=True)

            # Initialize vector store
            task3 = progress.add_task("Connecting to Milvus vector store...", total=None)
            self.vector_store = MilvusVectorStore(self.config, self.embedding_adapter)
            await self.vector_store.initialize_collections()
            progress.update(task3, completed=True)

            # Initialize document parser
            task4 = progress.add_task("Setting up markdown parser...", total=None)
            self.document_parser = MarkdownParser(self.config)
            progress.update(task4, completed=True)

            # Initialize document indexer
            task5 = progress.add_task("Initializing document indexer...", total=None)
            self.document_indexer = DocumentIndexer(self.config, self.document_parser, self.embedder, self.vector_store)
            progress.update(task5, completed=True)

            # Initialize query processor
            task6 = progress.add_task("Setting up query processor...", total=None)
            self.query_processor = QueryProcessor(self.config, self.embedder, self.vector_store)
            progress.update(task6, completed=True)

        console.print("✅ [bold green]All components initialized successfully![/bold green]")

        # Display component information
        self._display_component_info()

    def _display_component_info(self):
        """Display information about initialized components."""
        table = Table(title="Component Information", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Model/Configuration", style="white")
        table.add_column("Status", style="green")

        table.add_row("HuggingFace Embedder", f"{self.embedder.model_name} ({self.embedder._device})", "✅ Ready")
        table.add_row("Vector Store", f"Milvus ({self.config.milvus_host}:{self.config.milvus_port})", "✅ Connected")
        table.add_row("Embedding Dimension", str(self.embedder.embedding_dimension), "✅ Configured")

        console.print(table)

    async def create_sample_documents(self):
        """Create sample markdown documents for testing."""
        console.print("📝 [bold blue]Creating Sample Documents[/bold blue]")

        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="rag_demo_"))

        # Sample documents representing real-world scenarios
        documents = [
            {
                "filename": "python_best_practices.md",
                "content": """---
title: Python Development Best Practices
tags: [python, development, best-practices, coding]
topics: [software-engineering, clean-code]
summary: Essential guidelines for writing maintainable Python code
llm_hints: [programming, standards, guidelines]
---

# Python Development Best Practices

## Code Organization

### Project Structure
- Use clear, descriptive package and module names
- Separate business logic from presentation layer
- Implement proper dependency injection

### Virtual Environments
Always use virtual environments to isolate dependencies:
```bash
python -m venv myproject_env
source myproject_env/bin/activate  # Linux/Mac
myproject_env\\Scripts\\activate     # Windows
```

## Error Handling

### Exception Strategies
- Use specific exception types
- Implement proper logging
- Follow the EAFP principle (Easier to Ask for Forgiveness than Permission)

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    handle_error(e)
```

## Testing

Write comprehensive tests using pytest:
- Unit tests for individual functions
- Integration tests for component interactions
- Mock external dependencies appropriately
""",
            },
            {
                "filename": "microservices_architecture.md",
                "content": """---
title: Microservices Architecture Guide
tags: [microservices, architecture, distributed-systems]
topics: [system-design, scalability, containers]
summary: Comprehensive guide to designing and implementing microservices
keywords: [docker, kubernetes, api-gateway, service-mesh]
---

# Microservices Architecture

## Core Principles

### Single Responsibility
Each service should have one business capability and own its data.

### Autonomous Deployment
Services must be deployable independently without affecting others.

### Decentralized Governance
Teams should choose their own technology stacks based on requirements.

## Communication Patterns

### Synchronous Communication
- REST APIs for request-response patterns
- GraphQL for complex data fetching
- Use circuit breakers for resilience

### Asynchronous Communication
- Event-driven architecture with message queues
- Publish-subscribe patterns for loose coupling
- Event sourcing for audit trails

## Data Management

### Database per Service
- Each microservice owns its database
- No shared database access between services
- Use saga pattern for distributed transactions

### Data Consistency
- Eventual consistency is acceptable for most cases
- Use distributed locks sparingly
- Implement compensation transactions for failures
""",
            },
            {
                "filename": "machine_learning_deployment.md",
                "content": """---
title: Machine Learning Model Deployment
tags: [machine-learning, mlops, deployment, production]
topics: [ai, model-serving, monitoring]
summary: Best practices for deploying ML models to production
llm_hints: [tensorflow, pytorch, model-monitoring]
---

# Machine Learning Model Deployment

## Deployment Strategies

### Blue-Green Deployment
- Maintain two identical production environments
- Switch traffic between environments for zero-downtime deployment
- Easy rollback capability

### Canary Releases
- Gradually shift traffic to new model version
- Monitor performance metrics during rollout
- Automatic rollback on performance degradation

## Model Serving

### REST API Deployment
```python
from flask import Flask, request, jsonify
import joblib

app = Flask(__name__)
model = joblib.load('trained_model.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    prediction = model.predict(data['features'])
    return jsonify({'prediction': prediction.tolist()})
```

### Batch Processing
- Use Apache Spark for large-scale batch inference
- Implement data validation and preprocessing pipelines
- Monitor data drift and model performance

## Monitoring and Observability

### Performance Metrics
- Latency percentiles (P50, P95, P99)
- Throughput and error rates
- Resource utilization (CPU, memory, GPU)

### Model Quality Metrics
- Accuracy, precision, recall for classification
- RMSE, MAE for regression tasks
- Business-specific KPIs and A/B testing results
""",
            },
            {
                "filename": "database_optimization.md",
                "content": """---
title: Database Performance Optimization
tags: [database, performance, sql, optimization]
topics: [indexing, query-tuning, scaling]
summary: Techniques for optimizing database performance and scalability
keywords: [postgresql, mysql, nosql, sharding]
---

# Database Performance Optimization

## Indexing Strategies

### B-Tree Indexes
- Default index type for most databases
- Excellent for equality and range queries
- Consider composite indexes for multi-column queries

### Specialized Indexes
- Hash indexes for equality-only queries
- GIN/GiST for full-text search and JSON data
- Partial indexes for filtered datasets

## Query Optimization

### Query Analysis
```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2023-01-01'
GROUP BY u.id, u.name
ORDER BY order_count DESC;
```

### Common Anti-Patterns
- N+1 query problems
- Unnecessary subqueries
- Missing WHERE clause indexes
- Over-normalization leading to complex joins

## Scaling Strategies

### Vertical Scaling
- Increase CPU, memory, and storage
- Upgrade to SSD storage for better I/O
- Limited by hardware constraints

### Horizontal Scaling
- Read replicas for read-heavy workloads
- Sharding for write scaling
- Connection pooling to reduce overhead
""",
            },
            {
                "filename": "api_design_principles.md",
                "content": """---
title: RESTful API Design Principles
tags: [api, rest, web-services, design]
topics: [http, json, authentication, versioning]
summary: Guidelines for designing maintainable and scalable REST APIs
llm_hints: [openapi, swagger, rest-api]
---

# RESTful API Design Principles

## Resource-Oriented Design

### URL Structure
- Use nouns for resources, not verbs
- Maintain consistent naming conventions
- Implement proper nesting for related resources

```
GET /api/v1/users           # List users
GET /api/v1/users/123       # Get specific user
POST /api/v1/users          # Create user
PUT /api/v1/users/123       # Update user
DELETE /api/v1/users/123    # Delete user
```

## HTTP Methods and Status Codes

### Proper Method Usage
- GET: Retrieve data (idempotent)
- POST: Create new resources
- PUT: Update entire resource (idempotent)
- PATCH: Partial updates
- DELETE: Remove resources (idempotent)

### Status Code Guidelines
- 200: Successful GET, PUT, PATCH
- 201: Successful POST (created)
- 204: Successful DELETE (no content)
- 400: Bad request (client error)
- 401: Unauthorized
- 403: Forbidden
- 404: Not found
- 500: Internal server error

## Security Considerations

### Authentication & Authorization
- Use JWT tokens for stateless authentication
- Implement role-based access control (RBAC)
- Rate limiting to prevent abuse

### Data Validation
- Validate all input parameters
- Sanitize user input to prevent injection attacks
- Use HTTPS for all API endpoints
""",
            },
        ]

        # Write documents to temporary directory
        for doc in track(documents, description="Creating documents..."):
            file_path = self.temp_dir / doc["filename"]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(doc["content"])
            self.stats['documents_created'] += 1

        console.print(f"✅ Created {len(documents)} sample documents in {self.temp_dir}")
        return list(self.temp_dir.glob("*.md"))

    async def demonstrate_embedding_generation(self, files: list[Path]):
        """Demonstrate embedding generation capabilities."""
        console.print("🧠 [bold blue]Demonstrating Embedding Generation[/bold blue]")

        # Test single embedding
        console.print("Testing single text embedding...")
        sample_text = "Python is a versatile programming language used for web development"

        embedding_start = time.time()
        single_embedding = await self.embedder.generate_embedding(sample_text)
        embedding_time = time.time() - embedding_start

        console.print(f"✅ Generated embedding: dimension={len(single_embedding)}, time={embedding_time:.3f}s")

        # Test batch embeddings
        console.print("Testing batch embedding generation...")
        test_texts = [
            "Machine learning models require careful deployment strategies",
            "Database indexing improves query performance significantly",
            "Microservices architecture enables scalable system design",
            "API design principles ensure maintainable web services",
        ]

        batch_start = time.time()
        batch_embeddings = await self.embedder.generate_batch_embeddings(test_texts)
        batch_time = time.time() - batch_start

        console.print(f"✅ Generated {len(batch_embeddings)} embeddings in {batch_time:.3f}s")
        console.print(f"Average time per embedding: {batch_time/len(batch_embeddings):.3f}s")

        # Test LangChain adapter compatibility
        console.print("Testing LangChain adapter compatibility...")

        langchain_start = time.time()
        # Sync interface
        sync_embedding = self.embedding_adapter.embed_query(sample_text)
        # Async interface
        async_embedding = await self.embedding_adapter.aembed_query(sample_text)
        langchain_time = time.time() - langchain_start

        # Verify consistency
        embedding_diff = sum(abs(a - b) for a, b in zip(sync_embedding, async_embedding, strict=False))
        console.print(f"✅ LangChain adapter working: sync/async difference={embedding_diff:.6f}")

        self.stats['embeddings_generated'] += len(batch_embeddings) + 3
        self.stats['embedding_time'] += embedding_time + batch_time + langchain_time

        # Display embedding statistics
        self._display_embedding_stats(single_embedding, batch_embeddings)

    def _display_embedding_stats(self, single_embedding: list[float], batch_embeddings: list[list[float]]):
        """Display embedding statistics."""
        table = Table(title="Embedding Analysis", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        # Calculate statistics
        dimensions = len(single_embedding)
        avg_magnitude = sum(abs(x) for x in single_embedding) / dimensions

        batch_magnitudes = [sum(abs(x) for x in emb) / len(emb) for emb in batch_embeddings]
        avg_batch_magnitude = sum(batch_magnitudes) / len(batch_magnitudes)

        table.add_row("Embedding Dimension", str(dimensions))
        table.add_row("Single Embedding Avg Magnitude", f"{avg_magnitude:.4f}")
        table.add_row("Batch Embeddings Avg Magnitude", f"{avg_batch_magnitude:.4f}")
        table.add_row("Batch Size", str(len(batch_embeddings)))

        console.print(table)

    async def demonstrate_document_indexing(self, files: list[Path]):
        """Demonstrate document indexing workflow."""
        console.print("📚 [bold blue]Demonstrating Document Indexing[/bold blue]")

        start_time = time.time()

        # Index documents
        for file_path in track(files, description="Indexing documents..."):
            try:
                index_start = time.time()
                await self.document_indexer.index_document(file_path)
                index_time = time.time() - index_start

                self.stats['documents_indexed'] += 1
                self.stats['storage_time'] += index_time

                console.print(f"✅ Indexed: {file_path.name} ({index_time:.3f}s)")

            except Exception as e:
                console.print(f"❌ Failed to index {file_path.name}: {e}")

        total_time = time.time() - start_time
        self.stats['total_processing_time'] += total_time

        console.print(f"📊 Indexing completed: {self.stats['documents_indexed']} documents in {total_time:.3f}s")

    async def demonstrate_semantic_search(self):
        """Demonstrate semantic search capabilities."""
        console.print("🔍 [bold blue]Demonstrating Semantic Search[/bold blue]")

        # Test queries representing different use cases
        test_queries = [
            {
                "query": "How to optimize database performance?",
                "description": "Database optimization query",
                "expected_topics": ["indexing", "query optimization"],
            },
            {
                "query": "Best practices for Python development",
                "description": "Programming best practices query",
                "expected_topics": ["coding standards", "testing"],
            },
            {
                "query": "Deploying machine learning models to production",
                "description": "MLOps deployment query",
                "expected_topics": ["model serving", "monitoring"],
            },
            {
                "query": "Microservices communication patterns",
                "description": "Architecture design query",
                "expected_topics": ["distributed systems", "APIs"],
            },
            {
                "query": "RESTful API authentication and security",
                "description": "API security query",
                "expected_topics": ["JWT", "authorization"],
            },
        ]

        # Perform searches
        for query_data in test_queries:
            await self._perform_search_demo(query_data)

        console.print(f"🎯 Completed {len(test_queries)} semantic searches")

    async def _perform_search_demo(self, query_data: dict[str, Any]):
        """Perform a single search demonstration."""
        query = query_data["query"]
        description = query_data["description"]

        console.print(f"\n🔍 [cyan]{description}[/cyan]")
        console.print(f"Query: [italic]{query}[/italic]")

        search_start = time.time()

        try:

            search_request = SearchRequest(query=query, limit=3, similarity_threshold=0.4)

            search_results = await self.query_processor.search(search_request)
            search_time = time.time() - search_start

            self.stats['searches_performed'] += 1
            self.stats['search_time'] += search_time

            # Display results
            if search_results:
                console.print(f"Found {len(search_results)} relevant results ({search_time:.3f}s)")

                for i, result in enumerate(search_results[:3], 1):
                    console.print(
                        f"  {i}. [green]{result.title or 'Untitled'}[/green] (score: {result.confidence_score:.3f})"
                    )
                    if result.section_text:
                        # Show snippet
                        snippet = (
                            result.section_text[:150] + "..." if len(result.section_text) > 150 else result.section_text
                        )
                        console.print(f"     {snippet}")
            else:
                console.print("No relevant results found")

        except Exception as e:
            console.print(f"❌ Search failed: {e}")

    async def demonstrate_performance_analysis(self):
        """Demonstrate performance monitoring and analysis."""
        console.print("📈 [bold blue]Performance Analysis[/bold blue]")

        # Create performance summary table
        table = Table(title="RAG System Performance Metrics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Unit", style="dim")

        # Calculate averages
        avg_embedding_time = self.stats['embedding_time'] / max(self.stats['embeddings_generated'], 1)
        avg_indexing_time = self.stats['storage_time'] / max(self.stats['documents_indexed'], 1)
        avg_search_time = self.stats['search_time'] / max(self.stats['searches_performed'], 1)

        # Add performance metrics
        table.add_row("Documents Created", str(self.stats['documents_created']), "files")
        table.add_row("Documents Indexed", str(self.stats['documents_indexed']), "files")
        table.add_row("Embeddings Generated", str(self.stats['embeddings_generated']), "vectors")
        table.add_row("Searches Performed", str(self.stats['searches_performed']), "queries")
        table.add_row("", "", "")  # Separator
        table.add_row("Avg Embedding Time", f"{avg_embedding_time:.3f}", "seconds")
        table.add_row("Avg Indexing Time", f"{avg_indexing_time:.3f}", "seconds")
        table.add_row("Avg Search Time", f"{avg_search_time:.3f}", "seconds")
        table.add_row("Total Processing Time", f"{self.stats['total_processing_time']:.3f}", "seconds")

        console.print(table)

        # Performance insights
        console.print("\n💡 [bold yellow]Performance Insights[/bold yellow]")

        if avg_embedding_time < 0.1:
            console.print("✅ Embedding generation is highly optimized")
        elif avg_embedding_time < 0.5:
            console.print("⚠️  Embedding generation is acceptable but could be improved")
        else:
            console.print("🔴 Embedding generation may need optimization")

        if avg_search_time < 0.2:
            console.print("✅ Search performance is excellent")
        elif avg_search_time < 1.0:
            console.print("⚠️  Search performance is acceptable")
        else:
            console.print("🔴 Search performance may need optimization")

    def cleanup(self):
        """Clean up temporary resources."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            console.print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")

    async def run_demo(self):
        """Run the complete demo workflow."""
        console.print(
            Panel.fit(
                "🚀 [bold blue]Milvus Store & Embeddings Provider Integration Demo[/bold blue]\n"
                "This demo showcases real-world RAG system capabilities including:\n"
                "• Document parsing and indexing\n"
                "• Embedding generation and storage\n"
                "• Semantic search and retrieval\n"
                "• Performance monitoring",
                title="Markdown RAG System Demo",
                border_style="blue",
            )
        )

        try:
            # Initialize all components
            await self.initialize_components()

            # Create sample documents
            files = await self.create_sample_documents()

            # Demonstrate embedding capabilities
            await self.demonstrate_embedding_generation(files)

            # Index documents
            await self.demonstrate_document_indexing(files)

            # Perform semantic searches
            await self.demonstrate_semantic_search()

            # Show performance analysis
            await self.demonstrate_performance_analysis()

            console.print("\n🎉 [bold green]Demo completed successfully![/bold green]")

        except Exception as e:
            console.print(f"❌ RAG system error: {e}")
            logger.error("RAG error during demo", exc_info=e)

        finally:
            self.cleanup()


async def main():
    """Main demo entry point."""
    demo = MilvusEmbeddingsDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
