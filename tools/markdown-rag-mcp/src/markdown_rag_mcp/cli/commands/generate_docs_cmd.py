"""
Generate docs command implementation for the Markdown RAG MCP CLI.

Creates test markdown documents for development and testing.
"""

import random
import sys
from datetime import datetime
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from markdown_rag_mcp.config import get_config

console = Console()


@click.command()
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path),
    default=None,
    help='Directory to create test markdown files in (uses config default if not specified)',
)
@click.option('--count', type=int, default=15, help='Number of markdown files to generate')
@click.option(
    '--with-frontmatter',
    type=float,
    default=0.7,
    help='Proportion of files to include frontmatter (0.0-1.0)',
)
@click.option('--force', is_flag=True, help='Overwrite existing files')
def generate_docs(output_dir, count, with_frontmatter, force):
    """
    Generate test markdown documents for development and testing

    Creates a collection of programming and software engineering related markdown
    documents with realistic content and optional frontmatter metadata. Perfect for
    testing the RAG system with diverse technical content. Uses default documents
    directory from config if no output directory is specified.

    Examples:
    ```
    # Generate 15 files in default documents directory
    markdown-rag-mcp generate-docs

    # Generate 25 files in custom directory, 80% with frontmatter
    markdown-rag-mcp generate-docs --output-dir ./test-docs --count 25 --with-frontmatter 0.8

    # Generate minimal set for quick testing
    markdown-rag-mcp generate-docs --count 5 --output-dir ./quick-test
    ```
    """

    # Get config to resolve default output directory
    config = get_config()
    target_output_dir = output_dir if output_dir is not None else config.default_documents_dir

    # Validate parameters
    if count < 1:
        console.print("[red]❌ Error:[/red] Count must be at least 1")
        sys.exit(1)

    if not 0.0 <= with_frontmatter <= 1.0:
        console.print("[red]❌ Error:[/red] with-frontmatter must be between 0.0 and 1.0")
        sys.exit(1)

    # Show generation configuration
    config_panel = Panel.fit(
        f"📁 [bold cyan]Output Directory:[/bold cyan] {target_output_dir}\n"
        f"📄 [bold yellow]File Count:[/bold yellow] {count} documents\n"
        f"📝 [bold yellow]Frontmatter:[/bold yellow] {with_frontmatter:.0%} of files\n"
        f"⚡ [bold yellow]Force Overwrite:[/bold yellow] {'Yes' if force else 'No'}",
        title="📚 Document Generation Configuration",
        border_style="blue",
    )
    console.print(config_panel)

    try:
        # Create output directory
        target_output_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing files
        if not force and any(target_output_dir.glob("*.md")):
            console.print(f"[yellow]⚠️  Warning:[/yellow] Directory {target_output_dir} contains .md files")
            if not click.confirm("Continue anyway? (use --force to skip this prompt)"):
                console.print("[yellow]⚡ Operation cancelled[/yellow]")
                return

        # Generate documents with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:

            gen_task = progress.add_task("Generating markdown documents...", total=count)

            files_created = []
            frontmatter_count = 0

            for i in range(count):
                # Determine if this file should have frontmatter
                include_frontmatter = random.random() < with_frontmatter

                # Generate document content
                doc_content = _generate_document_content(i, include_frontmatter)
                filename = _generate_filename(i)
                file_path = target_output_dir / filename

                # Write file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(doc_content)

                files_created.append(filename)
                if include_frontmatter:
                    frontmatter_count += 1

                progress.advance(gen_task)

        # Show results
        results_table = Table(title="📊 Generation Results", show_header=True)
        results_table.add_column("Metric", style="cyan", width=20)
        results_table.add_column("Value", style="white", width=15)
        results_table.add_column("Details", style="dim", width=30)

        results_table.add_row("Files Created", str(len(files_created)), f"In {target_output_dir}")
        # Calculate percentages safely
        with_frontmatter_pct = f"{frontmatter_count/count:.0%}" if count > 0 else "0%"
        without_frontmatter_pct = f"{(count-frontmatter_count)/count:.0%}" if count > 0 else "0%"

        results_table.add_row("With Frontmatter", str(frontmatter_count), f"{with_frontmatter_pct} of total")
        results_table.add_row(
            "Without Frontmatter", str(count - frontmatter_count), f"{without_frontmatter_pct} of total"
        )
        results_table.add_row("Directory", str(target_output_dir), "Output location")

        console.print(results_table)

        # Show sample files
        if files_created:
            sample_files = random.sample(files_created, min(3, len(files_created)))
            sample_panel = Panel(
                "\n".join(f"• {filename}" for filename in sample_files),
                title="📋 Sample Files Created",
                border_style="green",
            )
            console.print(sample_panel)

        # Success message
        success_panel = Panel.fit(
            f"[green]✅ Successfully generated {count} markdown documents![/green]\n\n"
            f"[dim]Next steps:[/dim]\n"
            f"• Index the documents: [cyan]markdown-rag-mcp index {target_output_dir}[/cyan]\n"
            f"• Search the content: [cyan]markdown-rag-mcp search \"your query\"[/cyan]",
            title="🎉 Generation Complete",
            border_style="green",
        )
        console.print(success_panel)

    except Exception as e:
        click.echo(f"[red]❌ Error generating documents:[/red] {e}", err=True)
        sys.exit(1)


def _generate_filename(index: int) -> str:
    """Generate a descriptive filename for the document."""
    topics = [
        "python-fundamentals",
        "javascript-async-patterns",
        "docker-best-practices",
        "database-optimization",
        "api-design-principles",
        "microservices-architecture",
        "git-workflow-guide",
        "testing-strategies",
        "code-review-checklist",
        "performance-tuning",
        "security-guidelines",
        "deployment-automation",
        "monitoring-logging",
        "clean-code-practices",
        "design-patterns",
        "data-structures",
        "algorithm-analysis",
        "web-development",
        "mobile-development",
        "devops-practices",
        "agile-methodology",
        "system-design",
        "cloud-computing",
        "machine-learning-basics",
        "software-architecture",
    ]

    if index < len(topics):
        return f"{topics[index]}.md"
    else:
        # Generate additional topic names
        extra_topics = [
            "advanced-debugging",
            "memory-management",
            "concurrency-patterns",
            "caching-strategies",
            "message-queues",
            "service-mesh",
            "container-orchestration",
            "ci-cd-pipelines",
            "infrastructure-as-code",
        ]
        topic_index = (index - len(topics)) % len(extra_topics)
        return f"{extra_topics[topic_index]}-{index:02d}.md"


def _generate_document_content(index: int, include_frontmatter: bool) -> str:
    """Generate realistic programming-related markdown content."""

    # Document templates with programming content
    templates = [
        {
            "title": "Python Fundamentals and Best Practices",
            "tags": ["python", "fundamentals", "best-practices", "programming"],
            "topics": ["programming-languages", "python", "software-development"],
            "keywords": ["python", "functions", "classes", "modules", "best-practices"],
            "summary": "Comprehensive guide to Python programming fundamentals covering syntax, data structures, and coding best practices.",
            "llm_hints": ["explain python concepts", "code examples", "best practices"],
            "content": """# Python Fundamentals and Best Practices

Python is a versatile, high-level programming language known for its readability and simplicity. This guide covers essential concepts for effective Python development.

## Core Concepts

### Variables and Data Types

Python supports various data types including integers, floats, strings, lists, dictionaries, and sets. Understanding these is crucial for effective programming.

```python
# Basic data types
name = "Alice"
age = 30
skills = ["Python", "JavaScript", "SQL"]
profile = {"name": name, "age": age, "skills": skills}
```

### Functions and Modules

Functions promote code reusability and organization. Use descriptive names and docstrings for better maintainability.

```python
def calculate_experience_score(years: int, skills: list) -> float:
    \"\"\"Calculate experience score based on years and skill count.\"\"\"
    base_score = years * 10
    skill_bonus = len(skills) * 5
    return base_score + skill_bonus
```

## Best Practices

1. **Follow PEP 8**: Use consistent coding style and naming conventions
2. **Write Tests**: Implement unit tests for critical functionality
3. **Handle Exceptions**: Use try-catch blocks for error handling
4. **Document Code**: Write clear docstrings and comments
5. **Use Virtual Environments**: Isolate project dependencies

## Advanced Features

### List Comprehensions
List comprehensions provide concise ways to create lists:

```python
# Filter and transform data
active_users = [user for user in users if user.is_active]
squared_numbers = [x**2 for x in range(10)]
```

### Context Managers
Use context managers for resource management:

```python
with open('data.txt', 'r') as file:
    content = file.read()
    # File automatically closed
```

This foundation enables building robust, maintainable Python applications.""",
        },
        {
            "title": "Modern JavaScript Async Patterns",
            "tags": ["javascript", "async", "promises", "async-await"],
            "topics": ["web-development", "javascript", "asynchronous-programming"],
            "keywords": ["javascript", "promises", "async", "await", "callbacks"],
            "summary": "Comprehensive guide to handling asynchronous operations in modern JavaScript using promises and async/await.",
            "llm_hints": ["javascript async patterns", "promise chains", "error handling"],
            "content": """# Modern JavaScript Async Patterns

Asynchronous programming is fundamental to JavaScript development. This guide explores modern patterns for handling async operations effectively.

## Evolution of Async JavaScript

### Callbacks (Legacy Pattern)
```javascript
function fetchUserData(userId, callback) {
    setTimeout(() => {
        const userData = { id: userId, name: 'John Doe' };
        callback(null, userData);
    }, 1000);
}

fetchUserData(123, (error, data) => {
    if (error) {
        console.error('Error:', error);
    } else {
        console.log('User data:', data);
    }
});
```

### Promises (ES6)
Promises provide better error handling and composition:

```javascript
function fetchUserData(userId) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            const userData = { id: userId, name: 'John Doe' };
            resolve(userData);
        }, 1000);
    });
}

fetchUserData(123)
    .then(data => console.log('User data:', data))
    .catch(error => console.error('Error:', error));
```

### Async/Await (ES2017)
The most modern and readable approach:

```javascript
async function getUserProfile(userId) {
    try {
        const userData = await fetchUserData(userId);
        const userPosts = await fetchUserPosts(userId);

        return {
            user: userData,
            posts: userPosts
        };
    } catch (error) {
        console.error('Failed to fetch user profile:', error);
        throw error;
    }
}
```

## Best Practices

1. **Always Handle Errors**: Use try-catch with async/await or .catch() with promises
2. **Avoid Callback Hell**: Prefer promises or async/await over nested callbacks
3. **Parallel When Possible**: Use Promise.all for independent async operations
4. **Timeout Long Operations**: Implement timeouts for network requests
5. **Cancel When Appropriate**: Use AbortController for cancellable requests

Modern async patterns make JavaScript code more readable, maintainable, and robust.""",
        },
        {
            "title": "Docker Best Practices for Production",
            "tags": ["docker", "containers", "devops", "production"],
            "topics": ["containerization", "devops", "deployment"],
            "keywords": ["docker", "containers", "dockerfile", "production", "optimization"],
            "summary": "Production-ready Docker practices covering image optimization, security, and deployment strategies.",
            "llm_hints": ["docker optimization", "container security", "production deployment"],
            "content": """# Docker Best Practices for Production

Docker containerization requires careful consideration for production deployments. This guide covers essential practices for building, securing, and deploying containers at scale.

## Dockerfile Optimization

### Multi-Stage Builds
Reduce image size by separating build and runtime environments:

```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Runtime stage
FROM node:18-alpine AS runtime
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

## Security Best Practices

### Non-Root User
Always run containers as non-root users:

```dockerfile
FROM alpine:latest

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \\
    adduser -u 1001 -S appuser -G appgroup

USER appuser
WORKDIR /home/appuser

COPY --chown=appuser:appgroup . .
CMD ["./app"]
```

Following these practices ensures reliable, secure, and performant container deployments in production environments.""",
        },
    ]

    # Add more templates for variety
    additional_templates = [
        {
            "title": "Database Query Optimization Techniques",
            "tags": ["database", "sql", "optimization", "performance"],
            "topics": ["database-design", "performance-optimization"],
            "keywords": ["database", "sql", "indexing", "performance", "optimization"],
            "summary": "Techniques for optimizing database queries and improving application performance.",
            "llm_hints": ["database optimization", "sql performance", "indexing strategies"],
            "content": """# Database Query Optimization Techniques

Efficient database queries are crucial for application performance. This guide covers optimization strategies for better query performance.

## Indexing Strategies

### Primary Indexes
Create indexes on frequently queried columns:

```sql
-- Index on commonly searched columns
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_order_date ON orders(order_date);

-- Composite index for multi-column queries
CREATE INDEX idx_user_status_created ON users(status, created_at);
```

## Query Analysis

### Execution Plans
Always analyze query execution plans:

```sql
-- PostgreSQL
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;

-- MySQL
EXPLAIN FORMAT=JSON SELECT * FROM orders WHERE user_id = 123;
```

## Performance Best Practices

1. **Use Appropriate Indexes**: Index frequently queried and joined columns
2. **Avoid SELECT ***: Only select needed columns
3. **Optimize JOINs**: Use proper join types and conditions
4. **Limit Result Sets**: Use LIMIT and pagination
5. **Update Statistics**: Keep database statistics current

Proper optimization can dramatically improve application response times.""",
        },
        {
            "title": "API Design Principles and RESTful Best Practices",
            "tags": ["api", "rest", "web-services", "design"],
            "topics": ["api-design", "web-development", "software-architecture"],
            "keywords": ["api", "rest", "http", "web-services", "design-principles"],
            "summary": "Principles for creating maintainable, scalable RESTful APIs with proper design patterns.",
            "llm_hints": ["api design", "rest principles", "web services"],
            "content": """# API Design Principles and RESTful Best Practices

Well-designed APIs are crucial for modern software architecture. This guide covers principles for creating maintainable, scalable APIs.

## RESTful Design Principles

### Resource-Based URLs
Design URLs around resources, not actions:

```
Good:
GET    /api/users          # Get all users
GET    /api/users/123      # Get specific user
POST   /api/users          # Create user
PUT    /api/users/123      # Update user
DELETE /api/users/123      # Delete user

Avoid:
POST   /api/getUser
POST   /api/createUser
POST   /api/deleteUser
```

### HTTP Status Codes
Use appropriate HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

## Security Considerations

1. **Authentication**: Use JWT or OAuth for authentication
2. **Authorization**: Implement proper access controls
3. **Rate Limiting**: Prevent abuse with rate limiting
4. **Input Validation**: Validate and sanitize all inputs
5. **HTTPS**: Always use HTTPS in production

Good API design ensures long-term maintainability and developer satisfaction.""",
        },
    ]

    # Combine all templates
    all_templates = templates + additional_templates

    # Select template based on index, cycling through available templates
    template = all_templates[index % len(all_templates)]

    # Generate frontmatter if requested
    frontmatter_content = ""
    if include_frontmatter:
        frontmatter_parts = ["---"]

        # Add title
        if "title" in template:
            frontmatter_parts.append(f'title: "{template["title"]}"')

        # Add tags (list format)
        if "tags" in template and template["tags"]:
            frontmatter_parts.append("tags:")
            for tag in template["tags"]:
                frontmatter_parts.append(f"  - {tag}")

        # Add topics (list format)
        if "topics" in template and template["topics"]:
            frontmatter_parts.append("topics:")
            for topic in template["topics"]:
                frontmatter_parts.append(f"  - {topic}")

        # Add keywords (list format)
        if "keywords" in template and template["keywords"]:
            frontmatter_parts.append("keywords:")
            for keyword in template["keywords"]:
                frontmatter_parts.append(f"  - {keyword}")

        # Add summary
        if "summary" in template:
            frontmatter_parts.append(f'summary: "{template["summary"]}"')

        # Add llm_hints (list format)
        if "llm_hints" in template and template["llm_hints"]:
            frontmatter_parts.append("llm_hints:")
            for hint in template["llm_hints"]:
                frontmatter_parts.append(f"  - {hint}")

        # Add metadata
        frontmatter_parts.append(f'created: "{datetime.now().strftime("%Y-%m-%d")}"')
        frontmatter_parts.append('author: "System Generated"')
        frontmatter_parts.append("---")

        frontmatter_content = "\n".join(frontmatter_parts) + "\n\n"

    return frontmatter_content + template["content"]


def calculate_experience_score(years: int, skills: list) -> float:
    """Calculate experience score based on years and skill count."""
    base_score = years * 10
    skill_bonus = len(skills) * 5
    return base_score + skill_bonus
