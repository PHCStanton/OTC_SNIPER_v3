# Calibrated Apply Gates Plan — 26-09-04

**Branch:** `feat/ai_kb` · **Status:** In progress · **Scope decision (user):** Calibrated Apply Card + Bayesian decoupling only (Phase 2 pulse seeding deferred).

## 1. Problem
After a DONE calibration the user gets only generic Relaxed/Conservative/Strict presets — no one-click apply of the **specific gates the calibration itself tuned** (Tier A changes are reverted by the D4 restore and exist only inside the final report). The AI Pulse "Proposed Ghost Protocol" card is an empty shell post-calibration because live-session state is M1/M9-isolated from calibration trades (N=0 by design). Additionally, all three presets hard-enable `bayesian_filter_enabled`, cutting trade volume and starving post-calibration learning.

## 2. Contract (user-approved)
```
Calibration DONE → card: Apply Calibrated Gates
  [✓] Z-Score   [✓] Vol / LiQ   [✓] Regimes
  [ ] Bayesian (off unless prior store READY)
  [Apply]  [Save as Protocol]
secondary: generic Relaxed / Balanced / Strict stay as backup
```
- Calibration applies its **own** gates, not a canned preset.
- Bayesian is a **choice**, never a preset side effect.
- Presets remain as backup until the card is proven.

## 3. Phases
- [~] **P1 Backend:** NEW `calibrated_apply.py` (pure `build_calibrated_gates` from changelog `tier_a_applied` last-write-wins + Guardian proposals precedence + `_suggest_bayesian_floor`; `bayesian_prior_ready()` = 60s prior store `total_trades >= 500`); `CalibrationService._compile_calibrated_gates()` compiled after the final review (idempotent, also on review-timeout path); `calibration_final` event + `public_status().final_report` carry it.
- [~] **P2 Frontend:** `useCalibrationStore.calibratedGates` (+ `setCalibratedGates`, `applyStatus` mapping); `App.jsx` `calibration_final` handler; `CalibratedGatesCard` in `CalibrationPanel.jsx` (family checkboxes, evidence strip, Apply → `applyGhostProtocolGates(gates,'calibrated')`, Save as Protocol → `mergeGhostProtocols`); presets block relabeled "Backup presets"; builtin presets renamed Conservative→Balanced and stripped of `autoGhostBayesianFilterEnabled`.
- [~] **P3 Backend decoupling:** `ghost_protocol_profiles.py` presets drop `bayesian_filter_enabled` (floor values 0.50/0.535/0.58 + strict +0.02 kept); `FRONTEND_GATE_KEYS` validation updated; label "Balanced".
- [~] **P4 Tests:** NEW `test_calibrated_apply.py` (families LWW, proposal precedence, Bayesian choice/READY, presets decoupling, finalize integration via CalibrationHarness).
- [~] **P5 Verification:** full pytest regression + Vite production build.

## 4. Invariants
- M1/M9 calibration isolation untouched; D4 restore semantics untouched; no master KB writes.
- `allowed_regimes` proposals keep the never-empty guard (`calibration_autonomy.py:188-194`).
- Card values are frontend-keyed via existing `backend_gates_to_frontend` (percent-unit Bayesian).

## 5. Review Status & Tracked Follow-ups

**Review:** ⚠️ @Reviewer passed with 1 HIGH + 3 LOW. **F-1 (HIGH) closed** 26-09-04: Tier A `allowed_regimes: []` now never surfaces on the Apply card (`calibrated_apply.py:95-104`, mirrors the proposal-path guard) — regression test `test_tier_a_empty_allowed_regimes_never_surfaced`. F-2 (empty-only family) subsumed by F-1. F-3/F-4 informational, no action.

### Tracked follow-ups (open)
- **[ARCH-1 / HIGH-adjacent] Harden `enforce_milestone` upstream (defense-in-depth, separate from this feature):**
  - **Where:** `app/backend/services/calibration_autonomy.py` — `enforce_milestone()` Tier A path, `calibration_autonomy.py:120-130` region: `allowed_regimes` is in `CALIBRATION_TIER_A_FIELDS` (`auto_ghost.py:187`) and currently validates only N≥20 regime counts (non-first-milestone) with **no non-empty whitelist check** before `applied.append(item)`.
  - **Why:** Same blast radius as F-1 but upstream — an AI-emitted `allowed_regimes: []` at a catastrophic milestone would be auto-applied directly to config (allow-all regime bypass) without even hitting the Apply card.
  - **Fix:** reject or derive empty `allowed_regimes` (mirror the skip-last-regime guard at `calibration_autonomy.py:188-194`); add contract test.
  - **Owner:** @Architect (policy semantics) + @Coder (implementation). **Status:** [ ] open — tracked 26-09-04, not part of this phase.
- **[LOW, deferred] P2 Pulse seeding** (Phase 2 of the original scope: session Context seeding into AI Pulse prompts post-calibration) — explicitly deferred by user; revisit once the Apply card is proven in production.

## 6. Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| AI emits empty `allowed_regimes` (Apply-card path) | Low | HIGH (allow-all bypass) | **F-1 closed** (calibrated_apply guard + regression test) |
| AI emits empty `allowed_regimes` (auto-apply path) | Low | HIGH (allow-all bypass) | **ARCH-01 open** — upstream `enforce_milestone` hardening |
| Bayesian preset side-effect starves learning | High | MEDIUM (fewer trades) | P3 decoupling shipped — Bayesian is now opt-in only |
| Calibrated card values stale post-restart | Low | LOW | Card rides live `final_report` status; regenerated on DONE |
