# Calibration Mode Stability Remediation Plan

**Date:** 2026-08-31
**Status:** DRAFT — awaiting user approval before implementation (PHASE_REVIEW_PROTOCOL applies).
**Source:** Multi-agent diagnostic (@Investigator/@Reviewer/@Debugger) of `Dev_Docs/Auto_Ghost_Calibration_Mode_Plan_26-08-26.md` Phases 0–5, conducted 2026-08-31 on `feat/ai_kb` @ `8d446f1`.
**Environment:** conda `QuFLX-v2`; PowerShell (`;` separators, no `&&`).
**Scope guard:** Phase 6 (Discord `NotificationSink`) remains **DEFERRED** — nothing in this plan starts it.

---

## Executive Summary

The Calibration Mode implementation is architecturally faithful to the plan (single owner, five-surface silent routing, 409 runtime-config lock, D4 restore, kill-switch, unit contracts — all verified in code; **76/76 calibration-related tests green**). However, forensic evidence in `app/data/calibration_sessions/` proves **two real production failures already occurred**:

1. `auto_ghost_calib_1788119574.json` — stranded in **`PROPOSING`** with 24/24 trades settled, `final_report: null`, and an orphaned `auto_ghost_calib_1788119574.json.tmp` (4,829 B, larger than the final file → the process died mid-finalize, between `json.dump` to tmp and `os.replace`). **D4 restore never executed** — the user's settings stayed replaced, the 409 lock and entry veto stayed active, until the backend process was restarted.
2. `auto_ghost_calib_1788127900.json` — orphaned in **`RUNNING`** (6 settled), never closed, never reconciled.

Root causes: **no crash-resilience / startup reconciliation** (C-A) and **`_finalize` is not exception-safe, with the D4 restore ordered AFTER the awaited AI review** (C-B — the known Phase-3 P1, still open). Additionally, `warm_start_baseline.json` **does not exist** on disk, so the Session Guardian prior-transfer check, the A4 market-drift detector, and meaningful alignment classification are **operationally dead** (H-1) — the drift alarm can never fire and alignment always answers "Conservative".

This plan remediates in three phases: **R1 (P0 hotfixes — crash safety, escape hatch, session-id integrity)**, **R2 (frontend sync re-queue, status recovery, Guardian guards)**, **R3 (operational: generate the warm-start baseline + regression contract tests)**. R1 must be implemented and reviewer-signed before R2; R3's backfill run is independent and can execute any time after R1.

---

## Architecture Context

Single-owner design is preserved: ALL calibration state stays in `CalibrationService` (`app/backend/services/calibration_service.py`). No new module is introduced — the remediation only hardens lifecycle paths in existing files:

```
IDLE → RUNNING → ANALYZING → PROPOSING → DONE|ABORTED
                     ↑            ↑
   crash here leaves a non-terminal  ← C-A/C-B fix: startup reconciliation
   session file forever (C-A)          + exception-safe finalize (R1)
```

Key existing wiring (verified, unchanged by this plan):
- Silent routing: `trade_service.py:265-277` (`_emit_trade_channel`), `auto_ghost.py:1061-1078`, `streaming.py:332-339`.
- 409 lock: `streaming.py:486-493` → `strategy.py:152-154`.
- Entry veto / outcome observers: `auto_ghost.py:375-393`; settlement hook `auto_ghost.py:635-647`.
- Session minting: `auto_ghost.py:327-373` (`_reset_session`, `set_calibration_mode`).

---

## Current State Map

| ID | Severity | Finding | File(s):Lines | Status |
|---|---|---|---|---|
| C-A | 🔴 CRITICAL | No startup reconciliation; non-terminal session files (PROPOSING/RUNNING) survive process death silently; orphan `.tmp` never cleaned. Forensically confirmed ×2 on disk. | `calibration_service.py:127-156` (`__init__` never loads state), `:214-244` (`_persist`), `:736-759` (`_persist_observations`) | [ ] R1-3 |
| C-B | 🔴 CRITICAL | `_finalize` not exception-safe; D4 restore + unwiring run AFTER the awaited final AI review; `_persist_observations` re-raises inside the awaited review → one disk error permanently locks settings + veto, no escape hatch. | `calibration_service.py:411-431`, `:434-438`, `:757-759`, `:696` | [ ] R1-1, R1-2 |
| H-1 | 🟠 HIGH | `warm_start_baseline.json` missing → Guardian prior-transfer always `[]` (`calibration_autonomy.py:209-210`), drift detector always `no_centroids → drifted: False` (`ghost_protocol_profiles.py:271-273`), alignment always "Conservative" (`:329-337`). Phase 4/5 Guardian features operationally dead. | `calibration_service.py:776-786`; `ghost_protocol_profiles.py:271-337` | [ ] R3-1, R3-2 |
| H-2 | 🟠 HIGH | No escape hatch from ANALYZING/PROPOSING: `stop()` requires RUNNING; `abort()` drain path defeated by `_finalizing` early-return in `_finalize`. | `calibration_service.py:332-335`, `:380-400`, `:404-405` | [ ] R1-4 |
| H-3 | 🟠 HIGH | Session-id divergence when Auto-Ghost starts disabled: `start()` calls `update_config(enabled=True)` AFTER `set_calibration_mode(...)`; the enabled-transition re-mints a *different* `auto_ghost_calib_{epoch}` id → trade stamps / journal isolation point at the wrong session (M1/M9 violation). | `calibration_service.py:295-303`; `auto_ghost.py:293-295`, `:330-333` | [ ] R1-5 |

| M-1 | 🟡 MED | Time-budget watchdog duplicates the drain trigger, bypassing the `_begin_drain` guard (saved from double-finalize only by the `_finalizing` flag). | `calibration_service.py:885-899` vs `:346-353`, `:540-548` | [ ] R1-1 |
| M-2 | 🟡 MED | Frontend settings edits during calibration apply locally; sync POST is skipped while locked and **never re-queued after unlock** → next full-state sync can silently overwrite the D4-restored backend config. | `App.jsx` `syncRuntimeConfig` (`:284-287`), payload (`:330-339`) | [ ] R2-1 |
| M-3 | 🟡 MED | Guardian regime-drop proposal can emit `allowed_regimes: []`, which AutoGhost treats as allow-all. | `calibration_autonomy.py:174-193` (esp. `:186`) | [ ] R2-3 |
| M-4 | 🟡 MED | Tier B proposals for `amount` / `expiration_seconds` are rejected as "locked" before the propose-only route (plan intends propose-only with explicit confirm). | `calibration_autonomy.py:89-96` | [ ] R2-4 |
| M-5 | 🟡 MED | Atomic-write sites leave orphan `.json.tmp` on failure; no cleanup pass exists. | `calibration_service.py:238-241`, `:754-756` | [ ] R1-3 |
| M-6 | 🟡 MED | No mount-time `GET /api/strategy/calibration/status` fetch — UI recovers locked state only via the 5s `status_update.calibration` poll (up to 5s of "unlocked-looking" UI after reload). | `CalibrationPanel.jsx` (no fetch), `App.jsx:57-63` | [ ] R2-2 |

**Verified-correct contracts (no action, regression-protected):** five-surface routing; 409 lock; D1 ghost-only block (`trade_service.py:292-299`); D2 copy-execute block (`App.jsx:144-149`); observer exception safety (`auto_ghost.py:387-393`); voids-not-evidence (`calibration_service.py:500-502`); service-owned kill-switch (`:528-538`); Bayesian/payout unit contract end-to-end (`ghost_protocol_profiles.py:130-174` → `App.jsx:331`); AI timeout 60s (`xai_provider.py:16`) bounds any single review call.

---

## Implementation Phases

### Phase R1 — [x] P0 Hotfixes: crash safety, escape hatch, session-id integrity — IMPLEMENTED & REVIEWER-SIGNED-OFF 2026-08-31 (103/103 regression tests green)

**R1-1. Exception-safe `_finalize` with D4-restore-first ordering (fixes C-B, M-1).**
Rewrite `CalibrationService._finalize` (`calibration_service.py:402-447`): PROPOSING + persist, then a `try` block whose FIRST actions are the report build and — critically — **D4 restore + unwiring BEFORE any awaited AI call**, with the AI review wrapped in `asyncio.wait_for(timeout=90)`; the `finally` block always transitions to a terminal state, clears `_finalizing`, persists, and emits status. Fail loud: any exception logs with `logger.exception` and downgrades the terminal state to `ABORTED` (never silently swallowed).

```python
async def _finalize(self, *, final_state: str, reason: str | None = None) -> None:
    if self._finalizing or self._state in ("DONE", "ABORTED"):
        return
    self._finalizing = True
    self._cancel_watchdog()
    ag = self._require_bound()
    self._state = "PROPOSING"
    self._persist()
    try:
        settled = self._settled_wins + self._settled_losses
        self._final_report = { ... }                      # existing report build (:415-425)
        self._persist()
        # D4 restore + unwiring BEFORE the awaited AI review (P1 fix):
        self._restore_snapshot()
        ag.set_calibration_mode(False)
        ag.set_entry_veto_check(None)
        ag.remove_outcome_observer(self._on_outcome)
        if final_state == "DONE":
            try:
                await asyncio.wait_for(
                    self._run_milestone_review(settled, apply_tier_a=False, is_final=True),
                    timeout=90.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Calibration %s final AI review timed out — finalize continues.",
                               self._calibration_id)
    except Exception:
        logger.exception("Calibration %s finalize failed — forcing ABORTED (fail loud).",
                         self._calibration_id)
        final_state = "ABORTED"
    finally:
        self._state = final_state
        self._finalizing = False
        self._persist()
        await self._emit_status()
        if final_state == "ABORTED":
            await self._emit_loud_abort(reason or "finalize_failure")
        elif final_state == "DONE":
            self._arm_guardian()
        logger.info("Calibration %s finalized: %s", self._calibration_id, final_state)
```
Note: `_run_milestone_review` must no longer let `_persist_observations` re-raise un-guarded — wrap the `await self._persist_observations(...)` call (`:696`) in try/except that logs loudly and continues (report emission must not be lost to a reports-folder I/O error).

**R1-2. Review-call hard timeout (C-B).** Included in R1-1 for the final review; additionally apply `wait_for` to mid-run milestone reviews scheduled from `_on_outcome` via `_schedule` (`:525`) so a wedged AI call cannot pin a background task forever.

**R1-3. Startup reconciliation + `.tmp` hygiene (fixes C-A, M-5).**
In `bind()` (and therefore at streaming startup, since `streaming.py:364-367` binds on init), run a one-shot `_reconcile_stale_sessions()`:

```python
def _reconcile_stale_sessions(self) -> None:
    """Boot-time reconciliation (C-A): any non-terminal persisted calibration
    session means the process died mid-run. Mark STALE_ABORTED loudly, clean
    orphan .tmp artifacts. Never silently ignore."""
    directory = self._session_dir()
    if not directory.exists():
        return
    for path in sorted(directory.glob("auto_ghost_calib_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Unreadable calibration session file %s: %s", path.name, exc)
            continue
        state = str(data.get("state") or "")
        if state not in _LOCKED_STATES:
            continue
        changelog = data.setdefault("changelog", [])
        changelog.append({
            "epoch": len(changelog) + 1,
            "event": "reconciled_stale",
            "ts": unix_time(),
            "previous_state": state,
        })
        data["state"] = "STALE_ABORTED"
        data["final_report"] = data.get("final_report") or {
            "final_state": "STALE_ABORTED",
            "reason": "process_interrupted_before_finalize",
            "settled_wins": data.get("settled_wins", 0),
            "settled_losses": data.get("settled_losses", 0),
        }
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        os.replace(tmp, path)
        logger.error(
            "Calibration session %s was interrupted in state %s — marked STALE_ABORTED. "
            "Pre-calibration settings were NOT auto-restored for this run; review protocol settings.",
            data.get("calibration_id"), state,
        )
    for tmp in directory.glob("auto_ghost_calib_*.json.tmp"):
        logger.warning("Removing orphan calibration temp file: %s", tmp.name)
        tmp.unlink(missing_ok=True)
```
`STALE_ABORTED` is a persisted *terminal* marker only (the in-memory service still boots IDLE so a new calibration can start immediately). If `self._sio` is available at bind time, emit one `notification` (`type: "warning"`) summarizing reconciled sessions.

**R1-4. Escape hatch (fixes H-2).**
- `stop()` (`:329-344`): accept `state in ("RUNNING", "ANALYZING")`; when already ANALYZING with a live drain task, await it instead of raising.
- `abort()` (`:380-400`): before awaiting an existing drain task, verify the task is alive; if `_finalizing` is True but no live drain/finalize task exists (the stranded case), reset `_finalizing = False` and call `_finalize_after_drain()` directly. Guarantees a user-issued stop/abort always reaches a terminal state with restore.

**R1-5. Session-id integrity (fixes H-3).**
Reorder `start()` (`calibration_service.py:294-303`): apply `ag.update_config(enabled=True)` **before** `ag.set_calibration_mode(True, session_id=self._calibration_id)` so the enabled-transition re-mint happens while mode is still `standard` (minting a throwaway standard id), and the calibration id minted by `set_calibration_mode` is final and stable:

```python
# Calibration overrides manual Ghost-enabled state; do this BEFORE minting the
# calibration session so update_config's enabled-transition reset cannot re-mint
# a different calib session id afterwards (H3).
ag.update_config(enabled=True)
ag.set_calibration_mode(True, session_id=self._calibration_id)
ag.update_config(**_CALIBRATION_BASELINE_PRESET)
ag.update_config(auto_execute_ai_pulse=False, oteo_ai_enabled=False)
```
Add a fail-fast guard after wiring: `if ag._session_id != self._calibration_id: raise CalibrationStateError(...)` (Core Principle #9).

**R1 tests** (extend `test_calibration_contracts.py`):
- `test_finalize_crash_mid_review_releases_lock` — inject `_ai_reviewer` that raises; assert terminal state reached, `is_locked() is False`, veto/observer unwired, snapshot restored.
- `test_finalize_timeout_still_restores` — injected reviewer sleeps > timeout (patched small); assert DONE + restore.
- `test_startup_reconciliation_stale_sessions` — write fake RUNNING/PROPOSING files + orphan `.tmp`; trigger reconciliation; assert `STALE_ABORTED`, changelog entry, `.tmp` removed.
- `test_stop_works_from_analyzing` / `test_abort_rescues_stranded_finalize`.
- `test_calibration_start_when_ghost_disabled_single_session` — ghost `enabled=False` pre-start; assert `ag._session_id == calib.calibration_id` and exactly one `auto_ghost_calib_*` JSONL session.

### Phase R2 — [x] Frontend sync recovery + Guardian guards — IMPLEMENTED & REVIEWER-SIGNED-OFF 2026-08-31 (105/105 regression tests green; Vite build clean 12.41s)

**R2-1. Re-queue settings sync after unlock (fixes M-2).** In `App.jsx`: track the previous `locked` value from `useCalibrationStore`; on transition `true → false`, flush exactly one `syncRuntimeConfig(state)` (re-using the existing debounced sync function) so the D4-restored backend snapshot is re-affirmed from the authoritative frontend state (or the user's post-run edits are pushed). Log/toast on flush — no silent write.

**R2-2. Mount-time status fetch (fixes M-6).** Add `fetchStatus()` to `useCalibrationStore.js` calling `GET /api/strategy/calibration/status` → `applyStatus(json.calibration)`; invoke once in `CalibrationPanel.jsx`'s existing `useEffect` (and in `App.jsx` bootstrap alongside socket wiring). Guarantees the CALIBRATING badge/lock state is correct immediately after page reload.

**R2-3. Guardian allow-all guard (fixes M-3).** In `calibration_autonomy.py` regime proposal (`:182-192`): if the remaining list would be empty (`[r for r in by_regime if r != regime] == []`), return `[]` and log — never propose a whitelist that degrades to allow-all.

**R2-4. Tier B propose-only routing for `amount`/`expiration_seconds` (fixes M-4).** In `enforce_milestone` (`:89-96`): route Tier-B-classified fields to `proposals` (with `"requires_confirm": True`) instead of rejecting as locked; proposals remain never-auto-applied (enforcement unchanged — only the classification path moves). Keep `mode` and other true locked internals rejected.

**R2 tests:** `test_guardian_never_proposes_allow_all`; `test_tier_b_amount_is_proposal_not_rejection`. Frontend: Vite production build clean; manual pass — toggle a setting mid-calibration (no sync POST), stop calibration → exactly one re-queued sync; reload page mid-RUNNING → badge/lock correct immediately.

### Phase R3 — [x] Operational: warm-start baseline + regression coverage — IMPLEMENTED 2026-08-31 (106/106 tests; Vite build clean; baseline generated N=3551)

**R3-1. Generate the KB warm-start baseline (fixes H-1).** Run the existing Phase-4 CLI and commit the staged output through the existing staging path:
```powershell
conda activate QuFLX-v2
python scripts/kb_health_backfill.py --audit --backfill --stage-only
# Then commit the staged updates via the journal staging modal (human-in-the-loop, N-guards + .bak).
# Success criterion: app/data/ghost_trades/stats/warm_start_baseline.json exists and passes
# kb_health.load_warm_start_baseline validation.
```
**R3-2. Loud baseline-missing signal.** Escalate the existing warning in `_load_warm_start_baseline` (`calibration_service.py:785`) to a one-time Socket.IO `notification` (`type: "warning"`, message names the path + the Guardian features that stay disabled) when Guardian arms without a baseline — no silent degradation (Core Principle #8).

**R3-3. Post-remediation regression suite (all green before sign-off):**
```powershell
conda run -n QuFLX-v2 python -m pytest test_calibration_contracts.py test_calibration_autonomy.py test_ghost_protocol_profiles.py test_kb_health_phase4.py test_ai_pulse_prompt.py test_auto_ghost.py -q
npm --prefix app/frontend run build
```

### Phase R4 — [x] @Reviewer phase-gate (protocol-mandated) — performed after each phase

### Phase R5 — [x] Ops Hotfix: one-shot reconciliation + live-run protection — IMPLEMENTED & VERIFIED 2026-08-31 (110/110 tests)

**Incident:** the startup reconciliation notification ("1 interrupted calibration session(s) marked STALE_ABORTED…") repeated in the notification bell **while a calibration was running**.
**Root cause (R1-3 defect):** `_reconcile_stale_sessions()` re-ran on every `bind()` — and `get_calibration_service(auto_ghost=…)` re-binds on **every calibration API call** (`strategy.py:172/196/215`, plus the R2-2 mount fetch) — and it treated the **live run's own session file** (`state: RUNNING` is a locked state) as stale, flipping it `STALE_ABORTED` on disk between persists (which restored `RUNNING`), re-triggering the notification each cycle.
**Fix:** (1) `_reconcile_done` one-shot flag — `bind()` reconciles only on the first call per process (true boot-time semantics); (2) skip-active guard — the reconcile loop never touches a file whose `calibration_id` matches the in-memory `self._calibration_id`.
**Tests:** `TestReconcileOneShot.test_reconcile_runs_once_across_rebinds` (exactly 1 `reconciled_stale` entry + exactly 1 warning notification across 3 re-binds) and `test_reconcile_never_marks_active_calibration` (active file state stays `RUNNING`, no `reconciled_stale` entry). The R1 reconciliation test updated for the one-shot semantics (fresh-boot flag reset).
**Note:** the affected session file `auto_ghost_calib_1788219693.json` self-heals at the next persist/DONE if that run is still live; otherwise the `STALE_ABORTED` marker stands (genuinely interrupted from the journal's view).

---

## Verification Checklist

- [x] R1-1: `_finalize` exception-safe; D4 restore precedes awaited AI review; AI review bounded by 90s timeout; forced-ABORTED on internal failure with loud notification
- [x] R1-2: mid-run milestone reviews also timeout-bounded
- [x] R1-3: boot reconciliation marks non-terminal persisted sessions `STALE_ABORTED` + loud log/notification; orphan `.tmp` files cleaned
- [x] R1-4: `stop()` works from RUNNING and ANALYZING; `abort()` rescues a stranded `_finalizing` state
- [x] R1-5: starting calibration with Auto-Ghost disabled yields exactly one calibration session id; fail-fast guard added
- [x] R2-1: one re-queued settings sync fires on locked→unlocked transition
- [x] R2-2: page reload mid-calibration shows correct locked/badge state immediately (no 5s blind window)
- [x] R2-3: Guardian can never propose an `allowed_regimes` that resolves to `[]`
- [x] R2-4: Tier B `amount`/`expiration_seconds` arrive as confirmed proposals, never auto-applied, never rejected as locked
- [x] R3-1: `warm_start_baseline.json` exists, validates, and Guardian prior-transfer/drift/alignment execute against real centroids (verify a drift dry-run against synthetic OOD samples) — **DRY-RUN CONFIRMED: `detect_market_drift` returns `drifted: true` with z-scores (was permanently `no_centroids`)**
- [x] R3-2: missing-baseline warning escalated to a loud one-time Socket.IO `notification` when the Guardian arms without a baseline (new contract test `TestBaselineMissingNotification`)
- [x] R3-3: full pytest suite green; Vite build clean — **106/106 passed; `npm run build` EXIT=0**
- [ ] Phase 6 Discord `NotificationSink` — still NOT started (deferred)
- [ ] Manual live pass (outstanding from the original plan): full calibration run with BADGE-only UI, journal Calibration filter, Apply cards

## Files Touched Summary

| Phase | Files |
|---|---|
| R1 | `app/backend/services/calibration_service.py`, `test_calibration_contracts.py` |
| R2 | `app/frontend/src/App.jsx`, `app/frontend/src/stores/useCalibrationStore.js`, `app/frontend/src/components/shared/CalibrationPanel.jsx`, `app/backend/services/calibration_autonomy.py`, `test_calibration_autonomy.py` |
| R3 | `scripts/kb_health_backfill.py` (run only), staged KB commit via existing modal, `calibration_service.py` (baseline-missing notification), regression suite run |
| R4 | Review reports only (no code) |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Re-occurrence of stranded PROPOSING (settings locked, no trading) on every finalize-adjacent crash/kill | High if unpatched | High | R1-1/R1-2/R1-4 (exception-safe finalize + timeouts + escape hatch) |
| User config silently left replaced after an interrupted run (no restore, no signal) | Medium | High | R1-3 boot reconciliation + loud `STALE_ABORTED` marker + notification |
| Dead Guardian/drift/alignment gives false "market OK" confidence | Medium | High | R3-1 baseline generation + R3-2 loud missing-baseline notice |
| Mid-calibration frontend edits overwrite D4-restored config post-run | Medium | Medium | R2-1 re-queued sync flush |
| Calibration run trades logged to the wrong session id (journal isolation breach, M1/M9) | Medium (whenever ghost starts disabled) | Medium | R1-5 ordering fix + fail-fast guard |
| Allow-all regime regression via Guardian proposal | Low | Medium | R2-3 guard |
| Remediation itself regresses the 5-surface silence or unit contracts | Low | High | Existing 76-test battery re-run (R3-3) + @Reviewer phase gates |

---

*Plan produced per workspace conventions by @Investigator; handed to @Coder for implementation. PHASE_REVIEW_PROTOCOL applies between all phases.*





