# Grok Build Task: Bayesian + Adaptive Expiry + Load Protocol
## Mode: PLAN ONLY — No implementation until explicit user approval

You are operating under OTC_SNIPER_v3 team rules and **must obey** `.agents/CORE_PRINCIPLES.md` and `AGENTS.md` at all times:
1. Functional Simplicity First
2. Sequential Logic
3. Incremental Testing after every change
4. Zero Assumptions
5. Code Integrity / no breaking changes without approval
6. Strict Separation of Concerns
7. Stop Patching, Start Rewriting (after 2–3 failed patches)
8. Defensive & Explicit Error Handling (no silent failures)
9. Fail Fast, Fail Loud, Fail Predictably

**Plan mode only.** Do not edit files, run write operations, or implement anything until I approve the final phased plan.

---

## Objective

1. **Assess** the proposed Bayesian + Adaptive Expiry + Load Protocol design thoroughly against the live codebase.
2. Produce a **concise phased implementation plan** that is safe, sequential, and CORE_PRINCIPLES-compliant.
3. Stop after the plan. Await explicit approval before Act mode.

---

## Product intent (authoritative)

We need a working, effective system where:

- Users can **Load Protocols** (saved Bayesian priors + optional condition patterns + gate settings) from the Journal **Knowledge Base & Bayesian Priors Staging** modal left rail.
- Protocols are **horizon-stamped** (`60` and `300` at minimum).
- **Live Bayesian gating** must **distinguish expiries** — never train or score with mixed-horizon outcomes in one prior bag.
- **Adaptive Expiry** may propose 60s or 300s, but Bayesian must evaluate `P(Win | features, T)` using the protocol for that same `T`.
- **One Active protocol** for the default live path; library can hold many; compare max 2–3 in UI.
- Staging remains **manual / user verification gate** — no silent auto-commit to global KB or priors.
- Online `on_trade_outcome` updates only the protocol matching `expiration_seconds`.
- Prefer a strong **60s baseline** for live now; **300s** as separate protocol until sample size is READY.

### Known empirical constraints (must respect)

- Historical corpus is heavily 60s-dominated (~93% of ~14.7k trades).
- Non-60s buckets were sparse; 300s is usable for a **separate** protocol only when N is adequate.
- Adaptive expiry changing duration after a 60s-trained approve, then writing losses back into 60s priors = **prior poisoning**. Phase 1 must prevent this.
- Staged patterns with sample_size = 1 are research-only; do not treat as production KB.

### Reference docs / code (read before assessing)

- `Dev_Docs/Bayesian_Adaptive_Expiries_and_Gates_Architectural_Assessment_26-08-12.md`
- `app/backend/services/extensions/bayesian_signal_filter.py`
- `app/backend/services/extensions/volatility_adaptive_expiry.py`
- `shared/bayesian_prior_store.py`
- `data-agent/src/bayesian/prior_updater.py`
- `app/backend/services/auto_ghost.py` (signal → gates → Bayesian → adaptive → execute → outcome order)
- Journal staging UI (Knowledge Base & Bayesian Priors Staging modal — left rail = staged queue; target location for Load Protocol)
- `app/backend/services/journal_stats_service.py` if present
- Knowledge base loader / `condition_patterns` usage in AI confirmation path

Prefer **code over docs** when they differ. Verify paths and current behavior with read-only inspection. Zero assumptions.

---

## Proposed design summary (to assess, not rubber-stamp)

### Protocol artifact
Named, versioned JSON bundle:
- metadata: id, name, horizon_seconds, schema_version, source sessions, trade_count, date_range, notes
- priors: total_wins/losses/trades + feature_counts (existing store shape)
- optional patterns[] for KB
- optional gates (min_win_probability, flags)
- health derived from N + horizon (READY / EXPERIMENTAL / UNSAFE)

### Load Protocol UX (Staging modal left rail)
- Tabs or stacked: **Queue** (staged session reports) | **Protocols** (saved configs)
- Import JSON; list protocols with horizon + N + health + Active badge
- Actions: Inspect | Compare (≤3) | Activate (1 live) | Save snapshot from staging
- Commit to global KB remains gated by min sample size; default path = Save as Protocol

### Runtime rules
1. `on_trade_outcome`: update only matching horizon protocol / working copy; skip mismatched duration.
2. When Bayesian enabled: either clamp adaptive to active protocol horizon, or re-score with the protocol for adaptive’s chosen T (only if that protocol exists and is allowable).
3. Fail closed if context/prior missing — no fabricated probabilities.
4. Do not merge 60s and 300s counts into one feature_counts bag.

---

## Your deliverables (Plan mode)

### A. Assessment (thorough, concise)
Cover at least:
1. Current data flow: tick → OTEO → gates → Bayesian → adaptive expiry → execute → outcome → prior update
2. Horizon conflation / poisoning risks still present in code
3. Fit of Load Protocol with existing `BayesianPriorStore` + filter extension + Journal staging
4. Gaps vs proposed design (schema, UI, activate rules, AI KB binding)
5. Risks to CORE_PRINCIPLES (complexity, breaking changes, silent failure paths)
6. Verdict: what to keep, what to change, what to defer

### B. Concise phased plan (implementation-ready, not vague)
Each phase must include:
- Goal (one sentence)
- Scope (files/modules touched)
- Explicit non-goals
- Acceptance criteria / tests
- CORE_PRINCIPLES checks (simplicity, SoC, fail-closed, no silent writes)

**Required phase shape (adjust only with justification):**

**Phase 0 — Investigation only (read-only)**  
Confirm current expiry distribution hooks, outcome update paths, staging export paths, and UI entry points. No code changes.

**Phase 1 — Horizon integrity (highest priority)**  
- Guard Bayesian outcome updates to matching duration  
- Safe interaction with adaptive when Bayesian is on (clamp and/or re-score policy — recommend simplest safe default)  
- Seed/ensure 60s baseline prior path without destroying existing files (backup first)  
- Tests for non-60s skip + 60s persist

**Phase 2 — Load Protocol (library + one Active)**  
- Protocol schema + disk layout  
- Left-rail Protocols list + Import + Activate (1) + Inspect  
- Working copy vs immutable snapshot save rules  
- Activate validation (horizon, schema_version, min N health)  
- Tests + no break to current staging queue

**Phase 3 — Wire Adaptive to horizon-aware Bayesian (only if Phase 1–2 solid)**  
- `predict_win_probability(..., target_duration)`  
- Adaptive proposes T → Bayesian uses protocol T → execute  
- 300s protocol support as secondary when READY  
- Fail closed if protocol T missing

**Phase 4 — KB binding + commit gates (minimal)**  
- Patterns used by AI confirmation follow Active protocol  
- Min sample_size gate on global KB commit; Save as Protocol always available  
- Export/import round-trip

Do **not** expand into Chroma, Obsidian, or broad feature-schema redesign unless required for Phase 1–2 correctness. Prefer simplest path that ships a working Load Protocol + safe Bayesian/adaptive behavior.

---

## Constraints

- No production edits in Phase 0.
- No phase marked complete without tests and a short review note.
- After the plan: stop with  
  `Plan complete. Awaiting explicit approval to proceed to Phase 0 / Act mode.`
- If code and docs conflict, trust code and state the conflict.
- If sample-size or path facts are uncertain, measure/read — do not guess.
- Delegate to @Investigator / @Architect style reasoning as needed; keep the written plan unified and concise.

---

## Success definition

A phased plan that lets us ship:
1. Safe 60s Bayesian learning (no cross-horizon poisoning),
2. User-visible Load Protocol (save/load/activate),
3. A clear, minimal path to horizon-aware adaptive scoring,

without violating CORE_PRINCIPLES or expanding scope into unneeded infrastructure.