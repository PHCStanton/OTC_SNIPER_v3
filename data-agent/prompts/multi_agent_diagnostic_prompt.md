# TASK: Comprehensive Multi-Agent System Diagnostic & SSID Integration Audit

**Recipient:** [@Team-Leader](file:///c:/v3/OTC_SNIPER/.agents/Team_Leader.json)  
**Governing Standard:** [.agents/CORE_PRINCIPLES.md](file:///c:/v3/OTC_SNIPER/.agents/CORE_PRINCIPLES.md)  
**Memory & Context:** [data-agent/coding-agent-memory/.agent-memory/](file:///c:/v3/OTC_SNIPER/data-agent/coding-agent-memory/.agent-memory/) & [SSID_Operations_Reference.md](file:///c:/v3/OTC_SNIPER/data-agent/dev-docs/SSID_Operations_Reference.md)  
**Target Codebase:** [OTC_SNIPER Root](file:///c:/v3/OTC_SNIPER/) (`app/backend`, `ssid_integration_package`, `data-agent`, `shared`, `ui`)  
**Date:** 2026-08-09  

---

## 1. Objective & Scope
Orchestrate a read-only, multi-agent forensic diagnostic of the entire `OTC_SNIPER` and `data-agent` ecosystem. Identify architectural defects, thread/concurrency hazards, silent error swallows, and cross-boundary contract drift—with primary emphasis on the **SSID authentication and WebSocket ingestion pipeline**.

All investigations must enforce the **9 Non-Negotiable Core Principles** ([CORE_PRINCIPLES.md](file:///c:/v3/OTC_SNIPER/.agents/CORE_PRINCIPLES.md)), especially:
- **Principle 6 (Strict Separation of Concerns):** Clear boundaries between UI, API, session hooks, and tick sinks.
- **Principle 7 (Stop Patching, Start Rewriting):** Flag brittle, over-patched modules exceeding 2–3 failure cycles.
- **Principle 8 (Zero Silent Failures):** Detect empty `except:`/`catch`, unhandled promises, and swallowed IO/WebSocket errors.
- **Principle 9 (Fail Fast, Fail Loud):** Detect missing boundary validation, unsafe `?.`/`??` fallbacks, and unvalidated payloads.

---

## 2. Multi-Agent Delegation Plan

@Team-Leader, execute the diagnostic across three sequential phases by delegating to the following specialists:

### Phase 1: Forensic Inspection & Core Principles Audit
- **Delegating to @Investigator:**
  > "Perform a read-only forensic analysis across `app/backend/`, `ssid_integration_package/`, and `data-agent/src/` to identify root causes of silent failures, empty catch blocks, unhandled thread exceptions, and violations of [.agents/CORE_PRINCIPLES.md](file:///c:/v3/OTC_SNIPER/.agents/CORE_PRINCIPLES.md) (specifically Rules 8 & 9). Output findings with exact file paths, line numbers, quotes, and severity (CRITICAL/HIGH/MEDIUM/LOW)."

- **Delegating to @Architect:**
  > "Audit the macro architecture and module boundaries across `app/`, `ssid_integration_package/`, `data-agent/`, and `shared/` against [systemPatterns.md](file:///c:/v3/OTC_SNIPER/data-agent/coding-agent-memory/.agent-memory/systemPatterns.md). Verify clean dependency directions, cross-process atomic locks (`bayesian_prior_store.py`), and decoupled telemetry boundaries."

---

### Phase 2: Domain Deep-Dive — SSID Pipeline & Data Resilience
- **Delegating to @Backend-Specialist:**
  > "Inspect the end-to-end SSID lifecycle (`PocketOptionSession`, `SessionManager`, `SSIDTickCollector`) against [SSID_Operations_Reference.md](file:///c:/v3/OTC_SNIPER/data-agent/dev-docs/SSID_Operations_Reference.md). Evaluate:
  > 1. Strict SSID token parsing and immutable `isDemo` enforcement.
  > 2. Monkey patch safety (`gv.set_csv` -> `hooked_set_csv`) and clean teardown on disconnect.
  > 3. Concurrency safety between worker threads and the main asyncio event loop (`run_coroutine_threadsafe`).
  > 4. Producer-consumer tick buffering, backpressure, SQLite local fallback durability, and BigQuery/GCS streaming."

- **Delegating to @Frontend-Specialist:**
  > "Analyze `ui/` and web client components consuming WebSocket feeds and SSID session states. Verify that session disconnects, rate limits, and network dropouts surface explicit user-facing toasts/modals rather than silently freezing or desynchronizing UI state."

- **Delegating to @Debugger:**
  > "Perform vulnerability scanning for race conditions in account switching (`switch_account`), re-authentication loops, orphan WebSocket connections, SQLite thread locks, and unhandled `asyncio.CancelledError` or task terminations."

---

### Phase 3: Verification, Test Health & Synthesis
- **Delegating to @Tester:**
  > "Audit test suites across `tests/`, `data-agent/tests/`, and `ssid_integration_package/tests/`. Measure regression coverage for SSID failure modes (invalid token, demo/real switch, network dropout, corrupt local SQLite buffer, concurrent prior updates) and highlight un-mocked external dependencies."

- **Delegating to @Code_Simplifier & @Reviewer:**
  > "Review all flagged code sections for excessive complexity (Principle 1), bloated functions (>40 lines touching >3 concerns), and candidates requiring a clean rewrite (Principle 7) rather than further patches."

---

## 3. Required Diagnostic Output Deliverable

Synthesize all findings into a structured report saved to `reports/diagnostic_report_YYYY-MM-DD.md` containing:
1. **Executive Health Summary:** System-wide readiness score and key operational risks.
2. **SSID Integration Matrix:** Status of token extraction, validation, WS streaming, hook integrity, and disconnection cleanup.
3. **Core Principles Compliance Table:** Exact violations of Rules 1 through 9 with line-by-line evidence.
4. **Silent Failure & Concurrency Hotspots:** Enumeration of uncaught exceptions, race conditions, and error-swallowing code.
5. **Prioritized Action Plan:** Sequenced remediation backlog delegated to `@Coder`, `@Engineer`, or designated specialists.
