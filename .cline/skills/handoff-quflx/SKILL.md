---
name: handoff-quflx
description: Produces an OTC_SNIPER session handoff using the repository memory and documentation conventions. Use when ending a session, compacting context, preparing a new task, or updating project continuity notes.
---

# Handoff QuFLX

Use this skill to preserve continuity between Cline sessions for `c:\v3\OTC_SNIPER`.

## Primary Targets

Prefer updating or creating one of these artifacts, depending on the user's request:

- `.agent-memory/previousTaskSession.md`
- `.agent-memory/activeContext.md`
- `.agent-memory/progress.md`
- `Dev_Docs/<Topic>_Plan_<YY-MM-DD>.md`
- `@reports/<topic>_<YYYY-MM-DD>.md`

Do not duplicate large content already present elsewhere. Reference existing files by path.

## Handoff Contents

Include:

1. **Current Work** — what was being worked on and why.
2. **Latest Completed Steps** — concrete files changed or reviewed.
3. **Validation Status** — exact commands and pass/fail state.
4. **Open Risks** — unresolved runtime checks, known gaps, or decisions.
5. **Next Valid Step** — the next action that respects the active plan and review protocol.
6. **Relevant Files** — paths the next agent should inspect first.

## Project-Specific Rules

- Preserve Level 3 phase status accurately.
- Do not mark a phase complete unless review/sign-off rules were satisfied.
- Mention QuFLX-v2 commands exactly when validation matters.
- Keep language concise but complete enough for a fresh agent.
- If the handoff follows implementation, include any required `@Reviewer` gate status.
