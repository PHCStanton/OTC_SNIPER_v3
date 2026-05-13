---
name: tdd-quflx
description: Runs a QuFLX-v2-compatible red-green-refactor loop for OTC_SNIPER backend and frontend work. Use when implementing features, fixing logic, adding regression coverage, or changing trading/session/streaming behavior.
---

# TDD QuFLX

Use this skill when changing behavior in `c:\v3\OTC_SNIPER`.

## Mandatory Context

Before proposing tests or code changes, read relevant project context:

- `.agent-memory/activeContext.md`
- `.agent-memory/progress.md`
- `.clinerules/PHASE_REVIEW_PROTOCOL.md`
- the active implementation plan in `Dev_Docs/`
- nearby existing tests, for example `test_level3_phase1.py`, `test_level3_phase2.py`, or `test_level3_phase3.py`

## Loop

1. **Define the behavior** — state the observable outcome in user/domain terms.
2. **Red** — add or identify a failing test for the behavior.
3. **Green** — implement the smallest safe change.
4. **Refactor** — simplify without changing behavior.
5. **Verify** — run the narrowest relevant test command.
6. **Review gate** — after a completed implementation phase, delegate `@Reviewer` before proceeding.

## Test Command Patterns

Backend examples:

```powershell
conda run -n QuFLX-v2 python -m unittest test_level3_phase1.py test_level3_phase2.py test_level3_phase3.py
conda run -n QuFLX-v2 python -m py_compile app/backend/services/streaming.py app/backend/services/market_context.py
```

Frontend example:

```powershell
npm --prefix C:\v3\OTC_SNIPER\app\frontend run build
```

## Test Quality Rules

- Test public behavior, not private implementation details.
- Add regression tests for every bug fix.
- Keep tests focused and deterministic.
- Prefer small vertical slices over broad rewrites.
- If more than 2-3 patches are needed in the same area, trigger the clean-rewrite rule from `CORE_PRINCIPLES.md`.

## Error Handling Rules

- No silent failures.
- No empty catch blocks.
- Validate inputs early.
- Async tasks must expose/log failures predictably.
- UI failures must surface user-friendly feedback.
