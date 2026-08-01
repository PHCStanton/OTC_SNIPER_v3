# Effective Prompting Guide — Data Agent

## Best Practices for Prompting AI Coding Agents

1. **Reference Memory Files**: Mention `@.agent-memory/activeContext.md` or `@.agent-memory/systemPatterns.md` when initiating new development tasks.
2. **Be Specific About Constraints**: Mention execution environment details (e.g. `pythonpath=.`, Windows PowerShell compatibility, atomic file write rules).
3. **Structured Development Workflow**:
   - Step 1: Research and review relevant memory bank files.
   - Step 2: Formulate clear plan and design patterns.
   - Step 3: Implement code with defensive error handling.
   - Step 4: Execute automated tests (`pytest -o pythonpath=.`).
   - Step 5: Update `.agent-memory/` documentation.
4. **Constraint Stuffing for Code Quality**: Always require full, production-ready implementation without placeholders or truncated snippets.
