# Objective
Conduct a full, read-only critical diagnostic review, audit, and structural assessment of all newly completed implementations in the OTC_SNIPER system. The primary goal is to verify execution reliability, timing synchronization, Bayesian precision, mathematical soundness, error containment, and UI/UX telemetry, while identifying concrete opportunities where the codebase can be optimized, simplified, or made more performant and elegant according to CORE_PRINCIPLES.

---

## Context
Active Context and verified implementations from the current development cycle:
1. **Candle-Synchronized AI Pulse Execution**: Clock-aligned scheduling in `streaming.py` targeting $:45\text{s}$ before the target minute interval for execution on the exact 1-minute candle open ($t=00.000\text{s}$).
2. **Multi-Scale HTF Directional Bias Engine** (`htf_directional_bias.py`): Synthetic 5m/15m candle resampling from in-memory 1m buffer, EMA(5)/EMA(13) macro trend classification, rolling 60s/300s Tick Flow Ratio ($\frac{\text{Up Ticks}}{\text{Total Ticks}}$), and dynamic Bayesian win probability floor calibration ($51.0\% - 56.0\%$).
3. **Pre-Flight Validation & Target Price Proximity Gate**: Pre-flight checks at $T-5\text{s}$ in `auto_ghost.py` verifying capacity, manipulation $<0.35$, HTF directional confluence vetoes, Bayesian threshold, and target price proximity tolerance ($\pm 0.4\%$).
4. **Multi-Candle Wait Timer Support**: AI JSON and regex parsing of `wait_minutes` (`Wait: 2m` / `Wait: 1m`), scheduling execution $N$ candles into the future.
5. **Defensive Asset Parsing & Normalization**: Sanitization and validation in `streaming.py` and `auto_ghost.py` preventing reserved token collisions (e.g. phantom `CALL_otc`).
6. **UI Telemetry & Pending Setup Countdown**: Real-time WebSocket card with dynamic `MM:SS` countdown timer and target price display in `GhostTradingWidget.jsx`.
7. **Bayesian Adaptive Expiries & Multi-Horizon Prior Routing**: Dual horizon stores (`bayesian_priors.json` for 60s and `bayesian_priors_300s.json` for 300s), protocol health classification (`READY`, `EXPERIMENTAL`, `UNSAFE` based on $N \ge 500, 100 \le N < 500, N < 100$) in `shared/bayesian_protocol.py` and `KnowledgeBaseStagingModal.jsx`.
8. **Pulse Trajectory Post-Mortem Engine & MFE/MAE Excursion Tracking**: Intermediate checkpoint sampling ($30\text{s}, 60\text{s}, 120\text{s}, 180\text{s}, 300\text{s}$), Maximum Favorable/Adverse Excursion tracking (MFE/MAE), 4-way post-mortem classification (`CLEAN_WIN`, `PREMATURE_EXPIRATION`, `MOMENTUM_EXHAUSTION`, `STRUCTURAL_TRAP`, `DIRECTIONAL_FAIL`), and `AIPulseTrajectoryCard.jsx`.

---

## Scope
Restrict your forensic investigation to the following modules and components:
- **Backend Services & Signal Logic**:
  - `app/backend/services/htf_directional_bias.py`
  - `app/backend/services/auto_ghost.py`
  - `app/backend/services/streaming.py`
  - `app/backend/services/pulse_trajectory_engine.py`
  - `app/backend/services/journal_stats_service.py`
  - `app/backend/services/extensions/bayesian_signal_filter.py`
- **Shared Bayesian Architecture**:
  - `shared/bayesian_protocol.py`
  - `shared/bayesian_prior_store.py`
- **Frontend Components & State Stores**:
  - `app/frontend/src/components/shared/GhostTradingWidget.jsx`
  - `app/frontend/src/components/journal/AIPulseTrajectoryCard.jsx`
  - `app/frontend/src/components/journal/KnowledgeBaseStagingModal.jsx`
  - `app/frontend/src/stores/useSettingsStore.js`
- **Automated Test Suites**:
  - `test_htf_directional_bias.py`, `test_auto_ghost.py`, `tests/test_journal_stats_service.py`, `tests/test_vps_phase4_prior_store.py`

---

## Constraints & Rules
- **Read-Only**: You MUST NOT perform any code modifications, write files, or create commits during this diagnostic.
- **Zero Hallucination & Zero Assumptions**: Verify actual code, types, imports, and dictionary schemas. Never guess.
- **Adherence to CORE_PRINCIPLES**:
  1. Functional Simplicity First (eliminate unnecessary complexity).
  2. Sequential Logic (clean, traceable execution chains).
  3. Incremental Testing (verify edge cases).
  4. Separation of Concerns (single responsibility per module).
  5. Defensive & Explicit Error Handling (never swallow exceptions, zero silent failures).
  6. Fail Fast, Fail Loud, Fail Predictably.

---

## Multi-Agent Specialist Delegation

To maximize the depth, rigour, and precision of the assessment, delegate specific sections of the audit to the following specialized agents:

1. **@Investigator**:
   - Perform end-to-end trace from AI Pulse generation $\rightarrow$ Clock Alignment $\rightarrow$ Pre-Flight Validation Gate $\rightarrow$ Ghost Controller Execution $\rightarrow$ Trajectory Settlement.
   - Audit dictionary key contracts (e.g. `closed_candles` vs `closed_candles_1m`, `regime_label` vs `regime`, `priors` vs `feature_counts`).
2. **@Debugger**:
   - Inspect race conditions in asynchronous tasks, timer drifts, lock contention on `bayesian_priors.json.lock`, and edge cases in multi-candle sleep loops.
   - Detect potential silent drops (e.g. if websocket transport drops during pre-flight countdown).
3. **@Optimizer**:
   - Audit time/space complexity in the tick hot-paths (`record_tick`, `compute_tick_flow_ratio`, in-memory buffer sizing).
   - Identify redundant recalculations, unnecessary object allocations, or opportunities for $O(1)$ lookups.
4. **@Code_Simplifier**:
   - Identify overly verbose logic, duplicated parsing patterns, or bloated helper routines that can be streamlined without sacrificing defensive guarantees.
5. **@UI-Designer & @Frontend-Specialist**:
   - Review `GhostTradingWidget.jsx`, `AIPulseTrajectoryCard.jsx`, and `KnowledgeBaseStagingModal.jsx` against modern UI/UX best practices:
     - Dark-mode visual hierarchy, color harmony (emerald/rose/amber/cyan), typography, and micro-interactions.
     - Responsive layouts, layout shift prevention during countdowns, and Lucide React icon consistency.
6. **@Architect & @Backend-Specialist**:
   - Assess modularity, protocol schema versioning, and compliance with the two-channel Bayesian architecture.
7. **@Tester**:
   - Review test coverage gaps across `test_htf_directional_bias.py` and identify untested edge cases (e.g. zero-tick intervals, clock rollover over midnight UTC).

---

## Success Criteria / Target Deliverable

Produce a comprehensive, structured **`Executive_Diagnostic_and_Audit_Report.md`** containing:

1. **Executive Scorecard**: Overall system health, stability score (0–100%), and readiness rating.
2. **End-to-End Execution Trace & Verification (@Investigator & @Debugger)**: Forensic verification of the signal flow, clock timing, pre-flight gate, and trajectory settlement.
3. **Mathematical & Bayesian Calibration Audit (@Architect)**: Assessment of the HTF confluence scoring, 51%–56% Bayesian floor calibration, and Laplace prior stability.
4. **Performance & Latency Optimization Audit (@Optimizer)**: Hot-path bottlenecks, memory profile, and async concurrency analysis.
5. **Code Simplification & Refactoring Recommendations (@Code_Simplifier)**: Specific, high-impact simplification targets.
6. **UI/UX & Telemetry Review (@UI-Designer & @Frontend-Specialist)**: Visual polish, layout ergonomics, responsiveness, and state management audit.
7. **CORE_PRINCIPLES Compliance Matrix**: Systematic check against all 9 Core Principles.
8. **Prioritized Action Plan**: Clear, bulleted list of high, medium, and low-priority refinements.
