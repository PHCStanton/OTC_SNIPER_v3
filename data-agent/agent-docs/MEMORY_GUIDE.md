# Memory System Guide — Data Agent

This guide documents the memory architecture and best practices for managing context in the `data-agent` project.

## Memory System Components

1. **`.agent-memory/productContext.md`**: High-level purpose, user value, problem statement, core capabilities, and success metrics.
2. **`.agent-memory/activeContext.md`**: Active development focus, recent changes, immediate next steps, and blockers.
3. **`.agent-memory/systemPatterns.md`**: System architecture, layer diagrams, design patterns, data flow, and key decisions.
4. **`.agent-memory/techContext.md`**: Technologies, dependencies, development setup, constraints, and execution flags.
5. **`.agent-memory/progress.md`**: Completed milestone tracking, in-progress items, planned features, and test suite health.

## Core Rules for Memory Maintenance

- **Update Regularly**: Whenever completing a major task or introducing new features, update `.agent-memory/activeContext.md` and `.agent-memory/progress.md`.
- **Atomic State Updates**: Ensure system patterns and tech context accurately reflect current codebase structure.
- **Fail-Fast & Zero Assumptions**: Verify files and tests empirical outcomes before marking context items as complete.
