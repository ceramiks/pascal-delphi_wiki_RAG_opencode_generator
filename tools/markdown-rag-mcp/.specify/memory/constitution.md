<!--
Sync Impact Report:
- Version change: 0.0.0 → 1.0.0
- New constitution creation with 5 core principles for MCP server and RAG system development
- All templates align with library-first, CLI-based, test-driven development approach
- Follow-up: No immediate template updates required - templates already support this structure
-->

# Markdown RAG MCP Constitution

## Core Principles

### I. Library-First Architecture

Every feature starts as a standalone library with clear boundaries and minimal dependencies. Libraries must be self-contained, independently testable, and well-documented. Each library requires a clear, specific purpose - no organizational-only libraries that lack concrete functionality.

### II. CLI Interface Standard

Every library exposes functionality via a command-line interface following the text in/out protocol: stdin/arguments → stdout, with errors directed to stderr. All outputs must support both JSON and human-readable formats for maximum interoperability.

### III. Test-First Development (NON-NEGOTIABLE)

Test-Driven Development is mandatory: Tests must be written first, approved by stakeholders, and verified to fail before implementation begins. The Red-Green-Refactor cycle is strictly enforced with no exceptions.

### IV. MCP Protocol Compliance

All server implementations must strictly adhere to the Model Context Protocol specification. Server tools and resources must be properly declared, documented, and tested for compatibility with MCP clients. Breaking changes to MCP interfaces require major version increments.

### V. Documentation-Driven Design

Every feature requires comprehensive documentation including usage examples, API references, and integration guides. Documentation must be written before implementation and updated synchronously with code changes. Missing or outdated documentation blocks feature completion.

## Integration Standards

All MCP servers must provide standardized integration patterns:

- Server initialization and configuration management
- Error handling and logging following MCP conventions
- Resource discovery and capability advertisement
- Graceful shutdown and resource cleanup procedures

## Quality Assurance

Development workflow requires:

- Contract testing for all MCP tool and resource interfaces
- Integration testing with real MCP clients
- Performance benchmarking under realistic load conditions
- Security validation for data handling and access controls

## Governance

This constitution supersedes all other development practices. All code reviews and pull requests must verify compliance with these principles. Complexity that violates these principles must be explicitly justified with documented rationale. Amendments require team consensus, documentation updates, and migration plans.

**Version**: 1.0.0 | **Ratified**: 2025-10-08 | **Last Amended**: 2025-10-08
