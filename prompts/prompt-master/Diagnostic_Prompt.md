# Objective
Conduct a full, read-only critical diagnostic review and assessment of the Ghost Trader logic and streaming pipeline in the OTC_SNIPER codebase. The primary outcome is to identify any potential blockers, misalignments, or latency issues that could prevent ghost trades from executing or receiving signals, and deliver a comprehensive executive review report.

## Context
Active Context and project state (sourced from `.agent-memory/activeContext.md` and `.agent-memory/progress.md`):
- Calibrated UI indicators, warm-up progress tracking, and 11 streaming pipeline latency/lag optimizations are implemented.
- Plugin hooks (Adaptive Edge, AI Pulse & Noise Filter) are integrated and active.
- Z-Score and regime whitelist gates (Ghost Protocol) are operational.
- AI Advisory review loop and background suggestions are integrated.
- 15-minute stale tick filter is applied on seeding.

## Scope
You MUST restrict your review to the following key codebase modules:
- Core signal logic: `app/backend/services/auto_ghost.py`
- Streaming pipeline: `app/backend/services/streaming.py`
- Context and filters: `app/backend/services/market_context.py` and `app/backend/services/oteo.py`
- Extensions/Plugins: `app/backend/services/extensions/`

## Constraints
- **Read-Only**: You MUST NOT perform any code modifications, create commits, or write files to the codebase.
- **Autonomy**: You MUST ask before running any terminal commands. No destructive commands are allowed.
- **Zero Hallucination**: Ground your analysis strictly on the actual codebase implementation. If a file or import is missing, report it; do not assume its presence.

## Multi-Agent Perspective Guidelines
Analyze the signal-to-execution path by adopting the specialized expertise from these project personas:
1. **Reviewer** (from `ssid_integration_package/.agents/Reviewer.json`): Evaluate code quality, error containment, principle adherence, and separation of concerns.
2. **Optimizer** (from `.agents/Optimizer.json`): Check for hot-path bottlenecks, latency in asynchronous call blocks, and O(N) operations in the tick/signal stream.
3. **Debugger** (from `.agents/Debugger.json`): Perform a step-by-step trace of incoming signals, identifying possible silent failure states (e.g. payout check timeouts, queue drops, extension veto triggers).
4. **Prompt Engineer** (from `.agents/Prompt-Engineer.json`): Structure the final analysis into a premium, hyper-readable Markdown report.

## Success Criteria / Target Deliverable
Deliver a single, comprehensive `executive_review.md` artifact in the workspace containing:
1. **Executive Summary**: A high-level assessment of the health and stability of the Ghost Trader pipeline.
2. **Detailed Diagnostic Log (Debugger Perspective)**: A step-by-step audit of where signals can be lost or blocked, detailing specific logic conditions and exceptions.
3. **Performance & Latency Audit (Optimizer Perspective)**: Identification of hot-path bottlenecks and async blocking hazards.
4. **Code Quality & Compliance Audit (Reviewer Perspective)**: Review of error handling robustness and compliance with core project patterns.
5. **Actionable Recommendations**: Categorized and prioritized optimizations, settings suggestions, or fixes to resolve blocks or improve execution latency.
