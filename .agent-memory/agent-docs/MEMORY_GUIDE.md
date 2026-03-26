# Memory System Guide

This project relies on a tailored `.agent-memory` system to retain context across resets.
As an AI agent, you must always adhere to the context found in these specific memory files:
- `productContext.md`: Core product purpose and metrics.
- `activeContext.md`: Immediate next steps and recent changes.
- `systemPatterns.md`: Architectural rules and boundaries.
- `techContext.md`: Tech stack, setup commands, and constraints.
- `progress.md`: High-level feature completion tracker.

## Golden Rules for Memory
1. Read ALL of these files before making any complex changes.
2. Update `.agent-memory/activeContext.md` and `.agent-memory/progress.md` at the conclusion of every major feature or phase.
3. Treat these documents as your only bridge between sessions. Do not break their structure.
