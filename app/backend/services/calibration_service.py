"""
CalibrationService — single owner of ALL Auto-Ghost Calibration Mode state.

Implements Phase 1 of `Dev_Docs/Auto_Ghost_Calibration_Mode_Plan_26-08-26.md`.

Historical lesson honored: the deprecated 2026-06-16 calibration feature failed
because its state was smeared across five files with no backend owner. This
module centralizes ALL calibration state. The UI only observes and controls.

State machine:
    IDLE → RUNNING → ANALYZING → PROPOSING → DONE
                                ↘ ABORTED (kill-switch or fatal stop)

Contracts implemented here:
- M1/M9: dedicated session_id `auto_ghost_calib_{epoch}` (journal isolation).
- D4: pre-calibration config snapshot auto-restored on DONE/ABORTED.
- C4/EX-18: drawdown kill-switch owned HERE (checked after every settlement) —
  the AutoGhost drawdown cooldown (a 300s resume-after) is explicitly NOT reused.
- M10: stop() freezes new entries immediately; in-flight trades settle on
  calibration channels before the terminal transition (drain contract).
- C5: `auto_execute_ai_pulse` forced False; report payloads go out as
  `calibration_milestone`/`calibration_final`, never `notification type=ai_pulse`.
- C3: while state ∈ {RUNNING, ANALYZING, PROPOSING}, external runtime-config
  writes are refused (409) — see `is_locked()` used by streaming.update_runtime_settings.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from time import time as unix_time
from typing import Any

from ..config import get_settings
from .auto_ghost import CALIBRATION_TIER_A_FIELDS
from .calibration_autonomy import (
    MILESTONE_SIZE,
    enforce_milestone,
    guardian_prior_transfer,
    guardian_proposals,
    parse_autonomy_payload,
)
from .ghost_protocol_profiles import (
    build_strictness_presets,
    classify_alignment,
    detect_market_drift,
)

logger = logging.getLogger(__name__)


class CalibrationError(RuntimeError):
    """Base error for calibration lifecycle violations (maps to HTTP 409)."""


class CalibrationStateError(CalibrationError):
    """Raised on invalid state-machine transitions (fail fast, fail loud)."""


class CalibrationLockError(CalibrationError):
    """Raised when an external runtime-config write is attempted mid-calibration (C3)."""


# Calibration Baseline Preset (Official Spec — "Safety rails ON, learning gates OPEN").
#
# ⚠ REV1 (A1 / EX-23): setting `manipulation_severity_threshold=0.35` ACTIVATES a
# currently-inert pulse-path veto (`streaming.py` pulse gate requires threshold > 0,
# but the production default is 0.0). This is an INTENTIONAL, journaled behavior
# change recorded in the changelog at start(). The `>0`-guard vs `any(>=threshold)`
# inconsistency between the consider_signal path and the pulse path is logged as a
# report-only observation — NOT silently "fixed".
#
# ⚠ REV1 (C2): `minimum_payout_pct` is 0–100 PERCENT (85.0-form). NEVER write 0.85.
_CALIBRATION_BASELINE_PRESET: dict[str, Any] = {
    # Locked safety rails
    "amount": 1.0,
    "expiration_seconds": 60,
    "max_concurrent_trades": 2,
    "max_drawdown_amount": 25.0,          # kill-switch → loud ABORTED (25 × amount)
    "block_on_manipulation": True,
    "manipulation_severity_threshold": 0.35,  # A1: activates inert pulse-path veto (intentional)
    "minimum_payout_pct": 85.0,           # percent units — breakeven @85% ≈ 54.05%
    "max_session_trades": 100,
    "drawdown_cooldown_seconds": 300,
    "adaptive_expiry_enabled": False,     # LOCKED — protects the 60s prior
    "auto_execute_ai_pulse": False,       # LOCKED — C5
    "oteo_ai_enabled": False,             # LOCKED — H4: no AI-advisory toasts in the sample
    # Open learning gates (Tier A tightens with evidence in Phase 3)
    "bayesian_filter_enabled": True,
    "bayesian_min_probability": 0.50,     # loosest floor via READY priors (0-1 float form)
    "min_zscore_enabled": True,
    "min_zscore": -2.5,
    "max_zscore_enabled": True,
    "max_zscore": 2.5,
    "regime_gate_enabled": False,
    "volatility_gate_enabled": False,
    "liquidity_gate_enabled": False,
    "adx_gate_enabled": False,
    "cci_gate_enabled": False,
    "rsi_cci_enabled": False,
    "per_asset_cooldown_seconds": 45,
    "allowed_regimes": [],
    "blacklist_assets": [],
}

# Locked internals the AI must never write (Tier table, Phase 3 enforcement).
CALIBRATION_LOCKED_FIELDS = frozenset({
    "mode",
    "block_on_manipulation",
    "adaptive_expiry_enabled",
    "auto_execute_ai_pulse",
    "oteo_ai_enabled",
    "expiration_seconds",
    "amount",
})

_LOCKED_STATES = frozenset({"RUNNING", "ANALYZING", "PROPOSING"})

# R1-2 (C-B): hard bound on any single calibration AI review call — a wedged
# provider must never hang the event loop or strand a finalize. Applied in
# `_run_milestone_review` via asyncio.wait_for.
MILESTONE_AI_TIMEOUT_SECONDS = 90.0


class CalibrationService:
    """Single owner of calibration state. Bind once via `bind()`, drive via `start()`/`stop()`."""

    def __init__(self) -> None:
        self._auto_ghost = None
        self._sio = None
        self._state: str = "IDLE"
        self._calibration_id: str | None = None
        self._started_at: float = 0.0
        self._time_budget_seconds: int = 25 * 60
        self._trade_budget: int = 24
        self._autonomy_tier: str = "tiered"
        self._settled_wins: int = 0
        self._settled_losses: int = 0
        self._settled_voids: int = 0
        self._calibration_pnl: float = 0.0
        self._config_snapshot: dict[str, Any] | None = None
        self._changelog: list[dict[str, Any]] = []
        self._milestones: list[dict[str, Any]] = []
        self._final_report: dict[str, Any] | None = None
        self._drain_task: asyncio.Task | None = None
        self._watchdog_task: asyncio.Task | None = None
        self._stop_requested: bool = False
        self._stop_reason: str | None = None
        self._terminal_state: str = "DONE"
        self._finalizing: bool = False
        self._last_milestone_settled: int = 0
        self._guardian_task: asyncio.Task | None = None
        self._guardian_emitted: set[str] = set()
        self._warm_start_baseline: dict[str, Any] | None = None
        self._last_alignment: str | None = None
        self._drift_streak: int = 0
        self._ai_reviewer = None  # injectable for tests: async (system, user) -> str
        # R5: startup reconciliation is ONE-SHOT per process — `bind()` is called
        # on every calibration API call (strategy.py start/stop/status), and
        # re-running reconcile would repeatedly re-mark the live run's own
        # session file (RUNNING is a locked state) and spam the notification bell.
        self._reconcile_done: bool = False

    # ── Wiring ────────────────────────────────────────────────────────────────

    def bind(self, auto_ghost, sio=None) -> None:
        """Bind the AutoGhostService (and Socket.IO server) to this singleton.

        R1-3 (C-A): binding is the natural startup hook — reconcile any stale
        persisted sessions (the process died mid-run) and surface them loudly
        so a stranded PROPOSING/RUNNING can never be silently ignored.
        """
        self._auto_ghost = auto_ghost
        self._sio = sio
        if self._reconcile_done:
            return
        self._reconcile_done = True
        disrupted = self._reconcile_stale_sessions()
        if disrupted and sio is not None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                loop.create_task(self._emit_notification({
                    "type": "warning",
                    "message": (
                        f"{len(disrupted)} interrupted calibration session(s) marked "
                        f"STALE_ABORTED on startup — pre-calibration settings were NOT "
                        f"auto-restored for those runs: {', '.join(disrupted[:3])}"
                    ),
                    "timestamp": unix_time(),
                }))

    @property
    def initialized(self) -> bool:
        return self._auto_ghost is not None

    @property
    def state(self) -> str:
        return self._state

    @property
    def calibration_id(self) -> str | None:
        return self._calibration_id

    def is_locked(self) -> bool:
        """C3: True while external runtime-config writes must be refused."""
        return self._state in _LOCKED_STATES

    def public_status(self) -> dict[str, Any]:
        """Frozen, read-only status payload pushed to the frontend (C3)."""
        return {
            "state": self._state,
            "calibration_id": self._calibration_id,
            "started_at": self._started_at,
            "elapsed_seconds": round(unix_time() - self._started_at, 1) if self._started_at else 0.0,
            "time_budget_seconds": self._time_budget_seconds,
            "trade_budget": self._trade_budget,
            "settled_wins": self._settled_wins,
            "settled_losses": self._settled_losses,
            "settled_voids": self._settled_voids,
            "settled_total": self._settled_wins + self._settled_losses,
            "calibration_pnl": round(self._calibration_pnl, 2),
            "autonomy_tier": self._autonomy_tier,
            "locked": self.is_locked(),
            "stop_requested": self._stop_requested,
            "stop_reason": self._stop_reason,
            "config": self._current_frozen_config(),
        }

    def _current_frozen_config(self) -> dict[str, Any] | None:
        ag = self._auto_ghost
        if ag is None or self._state not in _LOCKED_STATES:
            return None
        cfg = ag.config
        return asdict(cfg) if is_dataclass(cfg) else dict(cfg)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _session_dir(self):
        return get_settings().data_dir / "calibration_sessions"

    def _persist(self) -> None:
        """Atomic-write the calibration session file (fail loud, never silent)."""
        if not self._calibration_id:
            return
        try:
            directory = self._session_dir()
            directory.mkdir(parents=True, exist_ok=True)
            payload = {
                "calibration_id": self._calibration_id,
                "state": self._state,
                "started_at": self._started_at,
                "time_budget_seconds": self._time_budget_seconds,
                "trade_budget": self._trade_budget,
                "autonomy_tier": self._autonomy_tier,
                "settled_wins": self._settled_wins,
                "settled_losses": self._settled_losses,
                "settled_voids": self._settled_voids,
                "calibration_pnl": round(self._calibration_pnl, 2),
                "config_snapshot": self._config_snapshot,
                "changelog": self._changelog,
                "milestones": self._milestones,
                "final_report": self._final_report,
            }
            path = directory / f"{self._calibration_id}.json"
            tmp_path = path.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, default=str)
            os.replace(tmp_path, path)
        except Exception as exc:
            logger.error("Failed to persist calibration session %s: %s", self._calibration_id, exc)
            raise

    def _journal(self, event: str, **fields: Any) -> None:
        """Append an epoch record to the changelog (epoch contract)."""
        entry = {"epoch": len(self._changelog) + 1, "event": event, "ts": unix_time(), **fields}
        self._changelog.append(entry)
        self._persist()

    def _reconcile_stale_sessions(self) -> list[str]:
        """R1-3 (C-A): boot-time reconciliation of non-terminal persisted sessions.

        Any session file in a _LOCKED_STATE means the previous process died
        mid-run (finalize never completed). Mark it STALE_ABORTED in place with
        a changelog entry and a loud error log; clean orphan `.json.tmp`
        artifacts. Never silently ignore (Core Principle #8). The in-memory
        service still boots IDLE so a new calibration can start immediately.

        Returns the list of interrupted calibration ids (empty when healthy).
        """
        try:
            directory = self._session_dir()
        except Exception as exc:
            logger.error("Calibration reconcile: cannot resolve session dir: %s", exc)
            return []
        if not directory.exists():
            return []
        disrupted: list[str] = []
        for path in sorted(directory.glob("auto_ghost_calib_*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error("Calibration reconcile: unreadable session file %s: %s", path.name, exc)
                continue
            state = str(data.get("state") or "")
            if state not in _LOCKED_STATES:
                continue
            # R5: NEVER treat the in-memory active calibration's own file as
            # stale — while RUNNING its persisted state is a locked state by
            # design and self-heals at the next persist/DONE.
            if self._calibration_id and str(data.get("calibration_id") or "") == self._calibration_id:
                continue
            changelog = data.setdefault("changelog", [])
            if not isinstance(changelog, list):
                changelog = []
                data["changelog"] = changelog
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
            try:
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, default=str)
                os.replace(tmp, path)
            except Exception as exc:
                logger.error("Calibration reconcile: failed to rewrite %s: %s", path.name, exc)
                continue
            disrupted.append(str(data.get("calibration_id") or path.stem))
            logger.error(
                "Calibration session %s was interrupted in state %s — marked STALE_ABORTED. "
                "Review protocol settings for that run (settings were not auto-restored).",
                data.get("calibration_id"), state,
            )
        for tmp in directory.glob("auto_ghost_calib_*.json.tmp"):
            try:
                tmp.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Calibration reconcile: failed to remove orphan tmp %s: %s", tmp.name, exc)
            else:
                logger.warning("Calibration reconcile: removed orphan temp file %s", tmp.name)
        return disrupted

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(
        self,
        *,
        duration_minutes: int = 25,
        target_trades: int = 24,
        autonomy_tier: str = "tiered",
    ) -> dict[str, Any]:
        """Enter calibration mode: snapshot config, apply the baseline preset, arm budgets."""
        ag = self._require_bound()
        if self._state in _LOCKED_STATES:
            raise CalibrationStateError(
                f"Calibration already active in state {self._state}; stop it first."
            )

        # D4: snapshot the FULL user config for auto-restore.
        self._config_snapshot = asdict(ag.config)

        self._calibration_id = f"auto_ghost_calib_{int(unix_time())}"
        self._started_at = unix_time()
        # REV2: ~25 min default. max(60, minutes)*60 wrongly turned 25 min into 60 min.
        self._time_budget_seconds = max(60, int(duration_minutes) * 60)
        self._trade_budget = max(4, int(target_trades))
        self._autonomy_tier = str(autonomy_tier)
        self._settled_wins = self._settled_losses = self._settled_voids = 0
        self._calibration_pnl = 0.0
        self._changelog = []
        self._milestones = []
        self._final_report = None
        self._stop_requested = False
        self._stop_reason = None
        self._terminal_state = "DONE"
        self._finalizing = False
        self._last_milestone_settled = 0
        self._guardian_emitted = set()
        self._warm_start_baseline = None
        self._last_alignment = None
        self._drift_streak = 0
        self._cancel_watchdog()
        self._cancel_guardian()

        # Calibration overrides manual Ghost-enabled state (trades must execute
        # even when the user had Auto-Ghost off); D4 restore brings it back.
        # R1-5 (H-3): enable BEFORE minting the calibration session so the
        # enabled-transition reset in update_config (`auto_ghost.py:293-295`)
        # cannot re-mint a different auto_ghost_calib_* id afterwards. The id
        # minted by set_calibration_mode is the single authoritative session id.
        ag.update_config(enabled=True)

        # M1/M9: dedicated isolated session id + calibration mode (mints the session).
        ag.set_calibration_mode(True, session_id=self._calibration_id)

        # Apply the baseline preset through the single mutation path (spec-table bounds).
        ag.update_config(**_CALIBRATION_BASELINE_PRESET)
        # Force locked pulse/AI behavior (C5/H4) — explicit bools, never silently skipped.
        ag.update_config(auto_execute_ai_pulse=False, oteo_ai_enabled=False)

        # Fail fast (Core Principle #9): the calibration session id must be the
        # id used by all trade stamps and journal analytics. Divergence aborts start.
        if ag._session_id != self._calibration_id:
            raise CalibrationStateError(
                "Calibration session id divergence: "
                f"auto_ghost={ag._session_id} != calibration={self._calibration_id}.",
            )

        # Entry veto + settlement observation wiring.
        ag.set_entry_veto_check(self._entry_veto)
        ag.add_outcome_observer(self._on_outcome)

        self._journal(
            "calibration_started",
            preset={k: _CALIBRATION_BASELINE_PRESET[k] for k in sorted(_CALIBRATION_BASELINE_PRESET)},
            note=(
                "A1 (EX-23): manipulation_severity_threshold=0.35 intentionally activates the "
                "currently-inert pulse-path veto; path inconsistency (>0 guard vs any(>=threshold)) "
                "is report-only, not silently fixed."
            ),
        )

        self._state = "RUNNING"
        self._persist()
        self._arm_watchdog()
        await self._emit_status()
        logger.info(
            "Calibration %s started (budget: %d trades / %d min)",
            self._calibration_id, self._trade_budget, self._time_budget_seconds // 60,
        )
        return self.public_status()

    async def stop(self, *, reason: str = "user_requested") -> dict[str, Any]:
        """User stop: freeze new entries NOW, drain in-flight trades, then finalize (M10).

        R1-4 (H-2) escape hatch: accepted from RUNNING **and** ANALYZING so a
        calibration can never strand with the 409 lock / veto active while a
        drain or finalize is already in recovery.
        """
        ag = self._require_bound()
        if self._state not in ("RUNNING", "ANALYZING"):
            raise CalibrationStateError(
                f"stop() requires RUNNING or ANALYZING (current: {self._state})."
            )
        self._stop_requested = True
        self._stop_reason = str(reason)
        self._terminal_state = "DONE"
        # Freezes entries immediately: _entry_veto vetoes unless state == RUNNING.
        if self._state == "RUNNING":
            self._state = "ANALYZING"
        self._journal("stop_requested", reason=self._stop_reason)
        await self._emit_status()
        await self._begin_drain()
        return self.public_status()

    async def _begin_drain(self) -> None:
        """Start (or await) the in-flight drain. HTTP stop returns after scheduling."""
        if self._drain_task is not None and not self._drain_task.done():
            return
        try:
            self._drain_task = asyncio.get_running_loop().create_task(self._finalize_after_drain())
        except RuntimeError:
            await self._finalize_after_drain()

    async def _finalize_after_drain(self) -> None:
        """Wait for in-flight trades to settle on calibration channels, then finalize.

        H2: abort AND stop both drain before restoring config / leaving calibration
        mode, so in-flight settlements cannot leak onto live `trade_result`.
        """
        ag = self._auto_ghost
        max_wait = 360.0  # > max expiration (300s) + settlement grace
        waited = 0.0
        # H2: wait for settlement *emits*, not capacity slots. `_release_asset`
        # can empty `_active_assets` before `_emit_trade_result`.
        while getattr(ag, "_in_flight_settlements", 0) > 0 and waited < max_wait:
            await asyncio.sleep(0.25)
            waited += 0.25
        leftover = int(getattr(ag, "_in_flight_settlements", 0) or 0)
        if leftover > 0:
            logger.warning(
                "Calibration drain timeout with %d in-flight settlements — finalizing anyway (fail loud)",
                leftover,
            )
        await self._finalize(
            final_state=self._terminal_state or "DONE",
            reason=self._stop_reason,
        )

    async def abort(self, *, reason: str) -> dict[str, Any]:
        """Loud abort (kill-switch or fatal). Freeze, drain, THEN restore (H2).

        R1-4 (H-2) escape hatch: if the finalize is stranded (flag set but no
        live drain/finalize task — e.g. a previous process died mid-finalize),
        reset the flag and drive finalize to completion so the user is never
        locked out of recovery.
        """
        if self._state in ("DONE", "ABORTED", "IDLE"):
            raise CalibrationStateError(
                f"abort() requires an active calibration (current: {self._state})."
            )
        self._stop_requested = True
        self._stop_reason = str(reason)
        self._terminal_state = "ABORTED"
        if self._state == "RUNNING":
            self._state = "ANALYZING"
        self._journal("calibration_aborted", reason=reason)
        await self._emit_status()

        drain = self._drain_task
        alive = drain is not None and not drain.done()
        if self._finalizing and not alive:
            # Stranded finalize (process died / task cancelled without cleanup):
            # rescue it so the terminal state + D4 restore are guaranteed.
            logger.warning(
                "Calibration %s finalize was stranded (finalizing=True, no live task) — "
                "rescuing via abort.",
                self._calibration_id,
            )
            self._finalizing = False
        if self._finalizing:
            # A live finalize is already draining/restoring; it completes on its own.
            logger.info(
                "Calibration %s finalize already in progress; abort acknowledged.",
                self._calibration_id,
            )
            return self.public_status()
        if alive:
            try:
                await drain
            except asyncio.CancelledError:
                await self._finalize_after_drain()
            return self.public_status()
        await self._finalize_after_drain()
        return self.public_status()

    async def _finalize(self, *, final_state: str, reason: str | None = None) -> None:
        """Common finalization: build final report, restore snapshot (D4), transition.

        R1-1 (C-B / Phase-3 P1): EXCEPTION-SAFE. D4 restore + unwiring happen
        AFTER the (non-awaiting) report build but BEFORE any awaited AI review,
        and the `finally` block ALWAYS reaches a terminal state — a review
        failure, timeout, or disk error can never leave calibration stranded in
        PROPOSING with the 409 lock and entry veto still active. Any internal
        failure forces ABORTED loudly.
        """
        if self._finalizing or self._state in ("DONE", "ABORTED"):
            return
        self._finalizing = True
        self._cancel_watchdog()
        if final_state != "DONE":
            self._cancel_guardian()
        ag = self._require_bound()
        self._state = "PROPOSING"
        self._persist()

        try:
            settled = self._settled_wins + self._settled_losses
            self._final_report = {
                "calibration_id": self._calibration_id,
                "final_state": final_state,
                "reason": reason or ("stop_requested" if self._stop_reason else "budget_complete"),
                "settled_wins": self._settled_wins,
                "settled_losses": self._settled_losses,
                "settled_voids": self._settled_voids,
                "win_rate": round(self._settled_wins / settled * 100.0, 2) if settled else None,
                "calibration_pnl": round(self._calibration_pnl, 2),
                "changelog_epochs": len(self._changelog),
            }
            self._persist()

            # D4: auto-restore the pre-calibration snapshot + unwiring BEFORE
            # any awaited AI review (C-B / Phase-3 P1): a review failure must
            # never leave the user's config replaced or the veto/lock active.
            self._restore_snapshot()

            ag.set_calibration_mode(False)
            ag.set_entry_veto_check(None)
            ag.remove_outcome_observer(self._on_outcome)

            if final_state == "DONE":
                await self._run_milestone_review(
                    settled, apply_tier_a=False, is_final=True,
                )
        except Exception:
            logger.exception(
                "Calibration %s finalize failed — forcing ABORTED (fail loud).",
                self._calibration_id,
            )
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

    def _restore_snapshot(self) -> None:
        """D4: restore the exact pre-calibration user config, including None fields."""
        ag = self._require_bound()
        if not self._config_snapshot:
            logger.warning("No config snapshot captured; skipping restore (fail loud).")
            return
        ag.restore_config_snapshot(self._config_snapshot)
        self._journal("config_restored", fields=sorted(
            k for k in self._config_snapshot.keys() if k != "mode"
        ))

    # ── Hooks (wired into AutoGhostService) ──────────────────────────────────

    def _entry_veto(self) -> str | None:
        """Entry veto callback: returns a reject reason when entries must be frozen.

        H5: budget and time limits reject SYNCHRONOUSLY while still RUNNING so
        consider_signal cannot overshoot while finalize is only scheduled.
        """
        if self._state == "RUNNING":
            if self._settled_wins + self._settled_losses >= self._trade_budget:
                return "calibration_trade_budget_reached"
            if self._started_at and (unix_time() - self._started_at) >= self._time_budget_seconds:
                return "calibration_time_budget_elapsed"
            return None
        if self._state in _LOCKED_STATES or self._state == "ABORTED":
            return "calibration_not_accepting_entries"
        return None

    def _on_outcome(
        self,
        *,
        trade_id: str,
        outcome: str,
        profit: float,
        asset: str | None = None,
        **_: Any,
    ) -> None:
        """Settlement observer (sync; called from report_outcome).

        M1: budget counts settled win/loss ONLY — voids are not evidence.
        C4: drawdown kill-switch checked after EVERY settlement → loud ABORTED.
        """
        if self._state not in _LOCKED_STATES:
            return
        if outcome == "win":
            self._settled_wins += 1
            self._calibration_pnl += float(profit or 0.0)
        elif outcome == "loss":
            self._settled_losses += 1
            self._calibration_pnl += float(profit or 0.0)
        elif outcome == "void":
            self._settled_voids += 1  # observed, never counted toward the budget
            return
        else:
            return

        self._persist()
        settled = self._settled_wins + self._settled_losses
        if settled > 0 and settled % 4 == 0 and settled < self._trade_budget:
            wr = round(self._settled_wins / settled * 100.0, 2)
            self._journal(
                "health_checkpoint",
                settled=settled,
                wins=self._settled_wins,
                losses=self._settled_losses,
                win_rate=wr,
                pnl=round(self._calibration_pnl, 2),
            )
            self._schedule(self._emit_status())
        if (
            settled % MILESTONE_SIZE == 0
            and settled != self._last_milestone_settled
            and settled < self._trade_budget
        ):
            self._last_milestone_settled = settled
            self._schedule(self._run_milestone_review(settled, apply_tier_a=True, is_final=False))
        self._check_budgets_sync()

    def _check_budgets_sync(self) -> None:
        """Budget + kill-switch evaluation after each settled outcome."""
        # C4 kill-switch: drawdown → loud ABORTED (NOT the 300s drawdown cooldown).
        kill_threshold = self._current_kill_threshold()
        if kill_threshold > 0 and self._calibration_pnl <= -abs(kill_threshold):
            logger.warning(
                "Calibration kill-switch hit: PnL %.2f <= -%.2f → ABORTED",
                self._calibration_pnl, kill_threshold,
            )
            self._schedule(self.abort(reason=f"drawdown_kill_switch ({self._calibration_pnl:.2f})"))
            return
        # Time / trade budgets: freeze now, drain in-flight, THEN restore (H2).
        if unix_time() - self._started_at >= self._time_budget_seconds:
            logger.info("Calibration time budget elapsed → draining.")
            self._request_terminal("DONE", "time_budget_elapsed")
            self._schedule(self._finalize_after_drain())
            return
        if self._settled_wins + self._settled_losses >= self._trade_budget:
            logger.info("Calibration trade budget reached (%d settled) → draining.", self._trade_budget)
            self._request_terminal("DONE", "trade_budget_complete")
            self._schedule(self._finalize_after_drain())

    def _current_kill_threshold(self) -> float:
        cfg = getattr(self._auto_ghost, "config", None)
        return float(getattr(cfg, "max_drawdown_amount", 0.0) or 0.0)

    def _request_terminal(self, final_state: str, reason: str) -> None:
        """Freeze new entries and record the intended terminal state (H2/H5)."""
        self._stop_requested = True
        self._stop_reason = reason
        self._terminal_state = final_state
        if self._state == "RUNNING":
            self._state = "ANALYZING"

    # ── Emissions ─────────────────────────────────────────────────────────────

    async def _emit_status(self) -> None:
        """Push the frozen calibration snapshot to the frontend (C3)."""
        if not self._sio:
            return
        try:
            await self._sio.emit("calibration_status", self.public_status())
        except Exception as exc:
            logger.error("Failed to emit calibration_status: %s", exc)

    async def _emit_notification(self, payload: dict[str, Any]) -> None:
        """Emit a live-UI notification (best-effort, fail loud)."""
        if not self._sio:
            return
        try:
            await self._sio.emit("notification", payload)
        except Exception as exc:
            logger.error("Failed to emit notification: %s", exc)

    async def _emit_loud_abort(self, reason: str) -> None:
        """Kill-switch alert: intentionally VISIBLE on the live notification channel."""
        if not self._sio:
            return
        try:
            await self._sio.emit("notification", {
                "type": "calibration_aborted",
                "message": f"⚠ Calibration aborted: {reason}",
                "calibration_id": self._calibration_id,
                "timestamp": unix_time(),
            })
        except Exception as exc:
            logger.error("Failed to emit calibration abort notification: %s", exc)

    def _schedule(self, coro) -> None:
        """Schedule an async transition from the sync observer context (fail loud)."""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(coro)
            task.add_done_callback(
                lambda t: logger.error("Calibration transition failed: %s", t.exception())
                if not t.cancelled() and t.exception() else None
            )
        except RuntimeError:
            logger.error("Calibration transition %r requires a running event loop.", coro)

    def _arm_watchdog(self) -> None:
        """M1: clock-gated time budget — must not wait for the next settlement."""
        self._cancel_watchdog()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._watchdog_task = loop.create_task(self._time_budget_watchdog())
        self._watchdog_task.add_done_callback(
            lambda t: logger.error("Calibration time watchdog failed: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )

    def _cancel_watchdog(self) -> None:
        task = self._watchdog_task
        self._watchdog_task = None
        if task is not None and not task.done():
            task.cancel()

    async def _run_milestone_review(
        self,
        settled: int,
        *,
        apply_tier_a: bool,
        is_final: bool,
    ) -> None:
        """Phase 3: AI (or injected) review → server-side enforce → optional one-family apply."""
        ag = self._auto_ghost
        if ag is None:
            return
        cfg = ag.config
        current = {
            name: getattr(cfg, name, None)
            for name in list(CALIBRATION_TIER_A_FIELDS) + ["max_concurrent_trades", "max_drawdown_amount"]
        }
        regime_counts: dict[str, int] = {}
        for key, stat in (ag.get_condition_stats() or {}).items():
            if str(key).startswith("regime:"):
                regime_counts[str(key).split(":", 1)[-1]] = int(stat.get("wins", 0)) + int(stat.get("losses", 0))

        # R1-2 (C-B): hard-bound the AI call — a wedged provider must never pin
        # the event loop or strand a finalize. Fail loud on timeout: continue
        # without AI changes this cycle.
        try:
            raw_text = await asyncio.wait_for(
                self._ask_milestone_ai(settled=settled, is_final=is_final, current=current),
                timeout=MILESTONE_AI_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Calibration %s milestone AI review timed out after %.0fs (n=%d) "
                "— no AI changes this cycle.",
                self._calibration_id, MILESTONE_AI_TIMEOUT_SECONDS, settled,
            )
            raw_text = ""
        parsed = parse_autonomy_payload(raw_text)
        verdict = enforce_milestone(
            parsed,
            current=current,
            locked_fields=set(CALIBRATION_LOCKED_FIELDS),
            settled_wins=self._settled_wins,
            settled_losses=self._settled_losses,
            regime_counts=regime_counts,
            is_first_milestone=(settled <= MILESTONE_SIZE),
            apply_tier_a=apply_tier_a and self._state == "RUNNING",
        )
        applied_records = []
        if verdict["applied"] and apply_tier_a and self._state == "RUNNING":
            patch = {item["field"]: item["new"] for item in verdict["applied"]}
            olds = {field: getattr(ag.config, field, None) for field in patch}
            ag.update_config(**patch)
            for item in verdict["applied"]:
                applied_records.append({
                    **item,
                    "old": olds.get(item["field"]),
                    "trade_index": settled,
                    "family": item["field"],
                })
                self._journal(
                    "tier_a_applied",
                    field=item["field"],
                    old=olds.get(item["field"]),
                    new=item["new"],
                    trade_index=settled,
                    rationale=item.get("rationale"),
                    evidence_n=item.get("evidence_n"),
                )

        report = {
            "settled": settled,
            "is_final": is_final,
            "win_rate": round(self._settled_wins / settled * 100.0, 2) if settled else None,
            "applied": applied_records,
            "proposals": verdict["proposals"],
            "rejected": verdict["rejected"],
            "observations": verdict["observations"],
            "catastrophic": verdict["catastrophic"],
        }
        if is_final:
            report["strictness_presets"] = build_strictness_presets(final_report=self._final_report)
            report["message"] = (
                "Calibration complete. Pre-calibration protocol will be restored. "
                "Relaxed / Conservative / Strict presets are ready to apply."
            )
        self._milestones.append(report)
        if is_final and self._final_report is not None:
            self._final_report["autonomy"] = {
                "proposals": verdict["proposals"],
                "observations": verdict["observations"],
            }
        self._persist()
        try:
            await self._persist_observations(verdict["observations"])
        except Exception as obs_err:
            # R1-1 (C-B): observation persistence must never break the milestone /
            # final report flow — log loudly and continue (report emission safety).
            logger.error(
                "Calibration %s failed to persist AI observations (non-fatal): %s",
                self._calibration_id, obs_err,
            )
        event = "calibration_final" if is_final else "calibration_milestone"
        await self._emit_named(event, report)
        logger.info("Calibration %s %s at n=%d applied=%d proposals=%d",
                    self._calibration_id, event, settled, len(applied_records), len(verdict["proposals"]))

    async def _ask_milestone_ai(self, *, settled: int, is_final: bool, current: dict) -> str:
        if self._ai_reviewer is not None:
            return await self._ai_reviewer(settled, is_final, current)
        try:
            from ..models.ai_models import AIChatRequest, AIMessage
            from .ai_service import get_ai_service
            ai = get_ai_service()
            if not ai.status().enabled:
                logger.warning("Calibration milestone AI disabled — no Tier A auto-apply this cycle")
                return ""
            wr = (self._settled_wins / settled * 100.0) if settled else 0.0
            system = (
                "You are OTC SNIPER's calibration reviewer. "
                "Return ONLY a JSON object with keys tier_a_changes, tier_b_proposals, observations. "
                "tier_a_changes items: {field, new, rationale, evidence_n}. "
                "bayesian_min_probability is a 0.50-0.90 float. minimum_payout_pct is percent. "
                "REV2: with N<20 per bucket, prefer empty tier_a_changes unless the sample is catastrophic "
                "(≤2 wins in 12). Never suggest locked fields (mode, amount, expiration_seconds, "
                "block_on_manipulation, adaptive_expiry_enabled, auto_execute_ai_pulse)."
            )
            user = (
                f"Milestone {'FINAL' if is_final else 'mid-run'} n={settled} "
                f"wins={self._settled_wins} losses={self._settled_losses} wr={wr:.1f}% "
                f"pnl={self._calibration_pnl:.2f}. Current gates: {json.dumps(current, default=str)}. "
                f"Session id={self._calibration_id}."
            )
            res = await ai.chat(AIChatRequest(
                messages=[AIMessage(role="system", content=system), AIMessage(role="user", content=user)],
            ))
            return getattr(res, "text", "") or ""
        except Exception as exc:
            logger.warning("Calibration milestone AI failed (no auto-apply): %s", exc)
            return ""

    async def _persist_observations(self, observations: list[dict[str, Any]]) -> None:
        if not observations:
            return
        try:
            root = Path(__file__).resolve().parents[3]
            path = root / "reports" / "analysis" / "ai_observations.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            existing: list[Any] = []
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8") or "[]")
                if not isinstance(existing, list):
                    existing = []
            for item in observations:
                existing.append({
                    **item,
                    "calibration_id": self._calibration_id,
                    "ts": unix_time(),
                })
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            os.replace(tmp, path)
        except Exception as exc:
            logger.error("Failed to persist AI observations: %s", exc)
            raise

    async def _emit_named(self, event: str, payload: dict[str, Any]) -> None:
        if not self._sio:
            return
        try:
            await self._sio.emit(event, {
                "calibration_id": self._calibration_id,
                "timestamp": unix_time(),
                **payload,
            })
        except Exception as exc:
            logger.error("Failed to emit %s: %s", event, exc)

    def _warm_start_path(self) -> Path:
        return get_settings().data_dir / "ghost_trades" / "stats" / "warm_start_baseline.json"

    def _load_warm_start_baseline(self) -> dict[str, Any] | None:
        from .kb_health import KbHealthError, load_warm_start_baseline
        path = self._warm_start_path()
        try:
            baseline = load_warm_start_baseline(path)
        except KbHealthError as exc:
            logger.error("Warm-start baseline failed validation: %s", exc)
            return None
        if baseline is None:
            logger.warning("No KB warm-start baseline at %s — Guardian prior-transfer check skipped", path)
        return baseline

    def _arm_guardian(self) -> None:
        self._cancel_guardian()
        self._warm_start_baseline = self._load_warm_start_baseline()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self._warm_start_baseline is None:
            # R3-2 (H-1): arming the Guardian WITHOUT a KB warm-start baseline is
            # LOUD — one warning per DONE. Prior-transfer / drift / alignment are
            # degraded, never silently. (Core Principle #8.)
            path = self._warm_start_path()
            loop.create_task(self._emit_notification({
                "type": "warning",
                "message": (
                    "Calibration complete but NO KB warm-start baseline was found at "
                    f"{path} — Session Guardian prior-transfer, market-drift detector, "
                    "and alignment classification stay DISABLED until "
                    "`python scripts/kb_health_backfill.py --backfill --stage-only` is run."
                ),
                "calibration_id": self._calibration_id,
                "timestamp": unix_time(),
            }))
        self._guardian_task = loop.create_task(self._guardian_loop())
        self._guardian_task.add_done_callback(
            lambda t: logger.error("Session Guardian failed: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )

    def _cancel_guardian(self) -> None:
        task = self._guardian_task
        self._guardian_task = None
        if task is not None and not task.done():
            task.cancel()

    async def _guardian_loop(self) -> None:
        """REV2 Session Guardian — propose-only, N>=20 buckets, live session after DONE."""
        logger.info("Session Guardian started after calibration %s", self._calibration_id)
        try:
            while True:
                await asyncio.sleep(30)
                ag = self._auto_ghost
                if ag is None or getattr(ag.config, "mode", "standard") == "calibration":
                    continue
                trades = list(getattr(ag, "_session_trades", []) or [])
                await self._run_alignment_and_drift(trades)
                proposals = guardian_proposals(trades, already_emitted=self._guardian_emitted)
                transfer = guardian_prior_transfer(
                    trades,
                    self._warm_start_baseline,
                    already_emitted=self._guardian_emitted,
                )
                items = (transfer + proposals)[:1]
                if not items:
                    continue
                item = items[0]
                bucket = str(item.get("bucket") or item.get("field") or "guardian")
                self._guardian_emitted.add(bucket)
                self._journal("guardian_proposal", **item)
                if self._sio:
                    suggestions = {}
                    if item.get("field") == "allowed_regimes":
                        suggestions["ghostAllowedRegimes"] = item.get("new")
                    await self._sio.emit("notification", {
                        "type": "ai_pulse",
                        "message": f"Session Guardian: {item.get('rationale')}",
                        "timestamp": unix_time(),
                        "suggestions": suggestions or None,
                    })
        except asyncio.CancelledError:
            return

    async def _run_alignment_and_drift(self, trades: list[dict[str, Any]]) -> None:
        """Phase 5 — condition alignment + A4 drift. Propose-only, one notice per change."""
        if not trades:
            return
        centroids = None
        if self._warm_start_baseline:
            centroids = self._warm_start_baseline.get("feature_centroids")
        drift = detect_market_drift(trades[-20:], centroids)
        if drift.get("drifted"):
            self._drift_streak += 1
        else:
            self._drift_streak = 0
        if self._drift_streak >= 3 and "alignment:drift" not in self._guardian_emitted:
            self._guardian_emitted.add("alignment:drift")
            rationale = (
                "Market has drifted from calibrated conditions — re-run calibration advised "
                f"(dims={drift.get('drifted_dims')}, z={drift.get('z_scores')})"
            )
            self._journal("market_drift", **drift)
            if self._sio:
                await self._sio.emit("notification", {
                    "type": "warning",
                    "message": f"⚠ {rationale}",
                    "timestamp": unix_time(),
                })
        alignment = classify_alignment(trades[-1], self._warm_start_baseline)
        level = alignment.get("level")
        if level and level != self._last_alignment:
            self._last_alignment = str(level)
            presets = build_strictness_presets(final_report=self._final_report)
            chosen = presets.get(level) or {}
            self._journal("condition_alignment", **alignment)
            if self._sio:
                await self._sio.emit("notification", {
                    "type": "ai_pulse",
                    "message": alignment.get("message"),
                    "timestamp": unix_time(),
                    "suggestions": chosen.get("gates"),
                    "strictness_level": level,
                })

    async def _time_budget_watchdog(self) -> None:
        try:
            await asyncio.sleep(self._time_budget_seconds)
        except asyncio.CancelledError:
            return
        if self._state != "RUNNING" or self._finalizing:
            return
        logger.info("Calibration time budget elapsed (watchdog) → draining.")
        self._stop_requested = True
        self._stop_reason = "time_budget_elapsed"
        self._terminal_state = "DONE"
        self._state = "ANALYZING"
        self._journal("time_budget_elapsed")
        await self._emit_status()
        await self._finalize_after_drain()

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _require_bound(self):
        if self._auto_ghost is None:
            raise CalibrationStateError("CalibrationService is not bound to an AutoGhostService.")
        return self._auto_ghost

    def reset_to_idle(self) -> None:
        """Post-terminal cleanup so a new calibration can start (DONE/ABORTED → IDLE)."""
        if self._state in _LOCKED_STATES:
            raise CalibrationStateError("Cannot reset while calibration is active.")
        self._cancel_guardian()
        self._state = "IDLE"
        self._calibration_id = None


# Module-level singleton (consistent with the other service accessors).
_instance: CalibrationService | None = None


def get_calibration_service(auto_ghost=None, sio=None) -> CalibrationService:
    """Return the CalibrationService singleton, binding it on first use."""
    global _instance
    if _instance is None:
        _instance = CalibrationService()
    if auto_ghost is not None:
        _instance.bind(auto_ghost, sio)
    return _instance


