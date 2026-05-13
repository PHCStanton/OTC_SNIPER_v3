---
name: architecture-review-quflx
description: Reviews OTC_SNIPER architecture boundaries, module responsibilities, and simplification opportunities before or after implementation. Use when assessing Level 3 work, streaming/session architecture, frontend state boundaries, broker adapters, or possible refactors.
---

# Architecture Review QuFLX

Use this skill to understand or improve structure without creating accidental cross-domain coupling.

## Context Sources

Read these first:

- `.agent-memory/activeContext.md`
- `.agent-memory/progress.md`
- relevant `Dev_Docs/*Plan*.md`
- `.clinerules/PHASE_REVIEW_PROTOCOL.md`
- `.clinerules/agent-investigation-workflow.md`

## Specialist Delegation

- Use `@Architect` for cross-cutting structural decisions.
- Use `@Code_Simplifier` for unnecessary complexity or duplication.
- Use `@Reviewer` for phase-gate quality checks.
- Use `@Coder` only when physical file edits are approved.

## Review Checklist

1. **Domain boundaries** — backend service, broker adapter, session, streaming, frontend store, and UI responsibilities remain separate.
2. **Data contracts** — payload fields are explicit and backward compatible.
3. **Fail-fast validation** — invalid states are caught early.
4. **Error handling** — failures are surfaced, not swallowed.
5. **Incremental testability** — changes can be validated with focused tests.
6. **Functional simplicity** — fewer moving parts where possible.
7. **Plan alignment** — work matches the active `Dev_Docs/` plan and phase status.

## Output Format

- **Executive Summary**
- **Current Architecture Map** — table of paths and responsibilities.
- **Boundary Risks** — severity and evidence.
- **Simplification Opportunities** — smallest safe changes first.
- **Testing / Review Requirements**
- **Recommended Next Step**

Do not implement fixes during an architecture review unless the user explicitly approves Act Mode implementation.
