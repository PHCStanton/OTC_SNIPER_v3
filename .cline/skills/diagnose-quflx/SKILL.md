---
name: diagnose-quflx
description: Performs OTC_SNIPER / QuFLX-v2 forensic diagnosis using the project investigation protocol. Use when bugs, regressions, failing tests, runtime anomalies, Socket.IO issues, broker/session failures, or performance regressions are reported in this repository.
---

# Diagnose QuFLX

Use this skill for disciplined read-only diagnosis in `c:\v3\OTC_SNIPER`.

## Mandatory Context Load

Start by reading:

1. `.agent-memory/activeContext.md`
2. `.agent-memory/progress.md`
3. `.clinerules/agent-investigation-workflow.md`
4. `.clinerules/PHASE_REVIEW_PROTOCOL.md`
5. Any active implementation plan relevant to the issue, usually `Dev_Docs/Level3_Implementation_Plan_26-04-29.md`

## Delegation Rule

Use the project convention:

`Delegating to @Investigator: perform read-only forensic analysis of [specific issue].`

Do not edit files during investigation. If root cause is found and code changes are needed, hand off to `@Debugger` or `@Coder` after reporting findings.

## Diagnosis Loop

1. **Reproduce / confirm signal** — identify the failing command, symptom, UI behavior, log, or test.
2. **Scope the blast radius** — list affected modules and data paths.
3. **Read only** — inspect code, tests, plans, and logs without modifying anything.
4. **Form hypotheses** — keep each hypothesis tied to evidence.
5. **Find exact evidence** — cite file paths and line numbers.
6. **Recommend next action** — name the specialist responsible for remediation.

## Required Report Format

1. **Summary** — 1-2 sentences.
2. **Critical Issues** — severity-rated: CRITICAL / HIGH / MEDIUM / LOW.
3. **Detailed Findings** — file + line + exact quote + explanation + why it matters.
4. **Recommendations** — what must be fixed and which specialist should handle it.
5. **Risk Forecast** — what breaks next if ignored.

## Guardrails

- Never modify code while diagnosing.
- Never guess file contents or behavior.
- If unclear, say `Need clarification`.
- Do not continue into fixes until the user approves implementation.
- Preserve QuFLX-v2 environment commands: `conda run -n QuFLX-v2 ...`.
- Use PowerShell-compatible command syntax on this Windows workspace.
