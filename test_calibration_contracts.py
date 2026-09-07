"""
Calibration Mode Phase 1 Contract Tests (Auto_Ghost_Calibration_Mode_Plan_26-08-26).

REV1 contract battery:
- test_calibration_no_live_ui_leak        (C1 — all five live surfaces silent)
- test_calibration_preset_payout_units    (C2 — 85.0 percent, never 0.85)
- test_calibration_runtime_config_locked  (C3 — 409 semantics via CalibrationLockError)
- test_calibration_drawdown_aborts_not_cools (C4 — kill-switch → ABORTED, not cooldown)
- test_calibration_session_id_isolated    (M1/M9 — auto_ghost_calib_{epoch})
- test_calibration_settings_restore       (D4 — snapshot auto-restored)
- test_calibration_in_flight_drain        (M10 — freeze, drain, then terminal)
- test_calibration_budget_counts_settled_only (M1 — voids are not evidence)
- state-machine transition tests
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.backend.services.auto_ghost import (
    AutoGhostService,
    AutoGhostConfig,
)
from app.backend.services.calibration_service import (
    CalibrationLockError,
    CalibrationService,
    CalibrationStateError,
    _CALIBRATION_BASELINE_PRESET,
)


class _FakeSio:
    """Records every emitted (event, payload) pair."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict | None]] = []

    async def emit(self, event, payload=None, **kwargs):
        self.events.append((event, payload))


class _StubTradeService:
    """Minimal trade-service stub for AutoGhostService construction."""

    def __init__(self, sio: _FakeSio | None = None):
        self.sio = sio

    def _get_market_context(self, asset: str) -> dict:
        return {}

    def _latest_logged_price(self, asset: str):
        return None


_OTEO_RESULT = {
    "recommended": "CALL",
    "oteo_score": 80.0,
    "confidence": 0.9,
    "actionable": True,
    "maturity": "MATURE",
    "market_context": {
        "z_score": 0.5,
        "adx_regime": "TRENDING",
        "adx": 30.0,
        "cci_state": "NEUTRAL",
        "tick_health": "HEALTHY",
    },
}


class CalibrationHarness:
    """Builds a bound (AutoGhostService, CalibrationService, FakeSio) triple."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.sio = _FakeSio()
        self.auto_ghost = AutoGhostService(
            _StubTradeService(self.sio),
            config=AutoGhostConfig(
                enabled=False,
                amount=5.0,
                minimum_payout_pct=92.0,
                max_concurrent_trades=3,
                auto_execute_ai_pulse=True,  # user had it on — must be locked off + restored
            ),
        )
        self.calibration = CalibrationService()
        self.calibration._session_dir = lambda: Path(self.tmp.name)
        self.calibration.bind(self.auto_ghost, self.sio)

    def cleanup(self) -> None:
        self.calibration._cancel_watchdog()
        self.calibration._cancel_guardian()
        self.tmp.cleanup()


async def _drain_loop(calibration: CalibrationService) -> None:
    """Let scheduled transition tasks run to completion."""
    for _ in range(80):
        await asyncio.sleep(0.05)
        if calibration.state in ("DONE", "ABORTED"):
            if calibration._drain_task is None or calibration._drain_task.done():
                return
        if calibration._drain_task is not None and not calibration._drain_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(calibration._drain_task), timeout=0.05)
            except (asyncio.TimeoutError, asyncio.InvalidStateError, asyncio.CancelledError):
                continue
        elif calibration._drain_task is not None and calibration._drain_task.done():
            if calibration.state in ("DONE", "ABORTED"):
                return


class TestNoLiveUILeak(unittest.IsolatedAsyncioTestCase):
    """C1: zero live-surface emissions during calibration (five surfaces)."""

    async def test_calibration_no_live_ui_leak(self) -> None:
        harness = CalibrationHarness()
        try:
            from app.backend.services.trade_service import TradeService
            from app.backend.models.domain import TradeRecord, TradeKind

            await harness.calibration.start()
            self.assertEqual(harness.auto_ghost.config.mode, "calibration")

            # Build a real TradeService wired to the calibration-mode auto_ghost.
            ts = object.__new__(TradeService)
            ts.sio = harness.sio
            ts._auto_ghost = harness.auto_ghost

            trade = TradeRecord(
                session_id=harness.auto_ghost._session_id,
                asset="EURUSD_otc",
                direction="call",
                amount=1.0,
                expiration_seconds=60,
                broker="pocket_option",
                kind=TradeKind.GHOST,
                success=True,
                message="test",
                trade_id="ghost-test",
                entry_price=1.1,
                entry_time=1000.0,
                exit_price=1.2,
                exit_time=1060.0,
                outcome="win",
                profit=0.85,
                simulated_profit=0.85,
                payout_pct=85.0,
                entry_context={"z_score": 0.5},
            )

            # Surfaces 1 & 2: trade_entry / trade_result.
            await ts._emit_trade_entry(trade)
            await ts._emit_trade_result(trade)
            # Surfaces 3 & 4: pulse pending / aborted helpers.
            await harness.auto_ghost._emit_pulse_channel(
                "ai_pulse_pending", {"asset": "EURUSD_otc"}
            )
            await harness.auto_ghost._emit_pulse_channel(
                "ai_pulse_aborted", {"asset": "EURUSD_otc", "reason": "test"}
            )
            # Surface 5: pulse notification mapping.
            from app.backend.services.streaming import _pulse_notification_event_name
            self.assertEqual(
                _pulse_notification_event_name("calibration"), "calibration_notification"
            )

            # THE CONTRACT: no live-surface event names were emitted.
            event_names = [name for name, _ in harness.sio.events]
            for live in ("trade_entry", "trade_result", "ai_pulse_pending", "ai_pulse_aborted"):
                self.assertNotIn(live, event_names)
            for name, payload in harness.sio.events:
                if name == "notification":
                    self.assertNotEqual(
                        (payload or {}).get("type"), "ai_pulse",
                        "notification type=ai_pulse leaked during calibration",
                    )
            # And the calibration channels DID receive the payloads.
            self.assertIn("calibration_trade_entry", event_names)
            self.assertIn("calibration_trade_result", event_names)
            self.assertIn("calibration_ai_pulse_pending", event_names)
            self.assertIn("calibration_ai_pulse_aborted", event_names)

            # H1: live poll redacts session metrics even after real settlements.
            harness.auto_ghost.report_outcome("t1", "win", 0.85, asset="EURUSD_otc")
            live = harness.auto_ghost.status_for_live_poll()
            self.assertEqual(live["auto_ghost_session_trades"], 0)
            self.assertEqual(live["auto_ghost_session_pnl"], 0.0)
            self.assertIsNone(live["auto_ghost_session_id"])
            self.assertGreater(harness.auto_ghost.status["auto_ghost_session_trades"], 0)

            # H4: advisory notifications remap off the live channel.
            await harness.auto_ghost._emit_notification({
                "type": "ai_advisory",
                "message": "should not leak",
            })
            self.assertIn("calibration_notification", [n for n, _ in harness.sio.events])
            self.assertFalse(any(
                n == "notification" and (p or {}).get("type") == "ai_advisory"
                for n, p in harness.sio.events
            ))

            # Sanity: after exit, the same surfaces emit live names again.
            harness.auto_ghost.set_calibration_mode(False)
            await ts._emit_trade_entry(trade)
            self.assertIn("trade_entry", [n for n, _ in harness.sio.events])
        finally:
            harness.cleanup()


class TestPresetPayoutUnits(unittest.IsolatedAsyncioTestCase):
    """C2: preset writes 85.0 percent — never the 0-1 fraction."""

    async def test_calibration_preset_payout_units(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            cfg = harness.auto_ghost.config
            self.assertEqual(cfg.minimum_payout_pct, 85.0)
            self.assertNotEqual(cfg.minimum_payout_pct, 0.85)
            self.assertTrue(0.0 <= cfg.minimum_payout_pct <= 100.0)
            # The whole preset is percent-form for payout and 0-1 for probability.
            self.assertNotIn("0.85", json.dumps(_CALIBRATION_BASELINE_PRESET))
            self.assertEqual(_CALIBRATION_BASELINE_PRESET["bayesian_min_probability"], 0.50)

            # Gate contract: 80% payout rejected, 90% accepted (percent semantics).
            reject_80 = harness.auto_ghost._passes_ghost_gates(
                asset="EURUSD_otc", price=1.1, timestamp=0.0,
                oteo_result=dict(_OTEO_RESULT), manipulation={}, payout_pct=80.0,
            )
            self.assertEqual(reject_80, "payout_below_minimum")
            reject_90 = harness.auto_ghost._passes_ghost_gates(
                asset="EURUSD_otc", price=1.1, timestamp=0.0,
                oteo_result=dict(_OTEO_RESULT), manipulation={}, payout_pct=90.0,
            )
            self.assertNotEqual(reject_90, "payout_below_minimum")
        finally:
            harness.cleanup()


class TestRuntimeConfigLocked(unittest.IsolatedAsyncioTestCase):
    """C3: runtime-config writes refused while calibration is active."""

    async def test_calibration_runtime_config_locked(self) -> None:
        harness = CalibrationHarness()
        try:
            from app.backend.services.streaming import StreamingService

            await harness.calibration.start()
            self.assertTrue(harness.calibration.is_locked())

            svc = object.__new__(StreamingService)
            svc.level2_enabled = False
            svc.level3_enabled = False
            svc.oteo_ai_enabled = False
            svc.oteo_ai_execution_mode = "advisory"
            svc.auto_ghost = harness.auto_ghost
            svc.calibration_service = harness.calibration
            svc._calibration_prefs = {}
            svc._streaming_active = False

            with self.assertRaises(CalibrationLockError):
                svc.update_runtime_settings(auto_ghost_enabled=False)

            # Config unchanged (the frontend sync did NOT overwrite the preset).
            self.assertTrue(harness.auto_ghost.config.enabled)
            self.assertEqual(harness.auto_ghost.config.mode, "calibration")

            from app.backend.api.strategy import RuntimeStrategyConfigRequest, update_runtime_config

            class _App:
                def __init__(self, streaming):
                    self.state = type("S", (), {"streaming_service": streaming})()

            class _Request:
                def __init__(self, streaming):
                    self.app = _App(streaming)

            resp = await update_runtime_config(RuntimeStrategyConfigRequest(), _Request(svc))
            self.assertEqual(resp.status_code, 409)
            body = json.loads(resp.body)
            self.assertEqual(body["reason"], "calibration_locked")

            await harness.calibration.stop()
            await _drain_loop(harness.calibration)
            # After finalization the lock is released.
            self.assertFalse(harness.calibration.is_locked())
        finally:
            harness.cleanup()


class TestDrawdownAbortsNotCools(unittest.IsolatedAsyncioTestCase):
    """C4: kill-switch → loud ABORTED (config restored), not a cooldown resume."""

    async def test_calibration_drawdown_aborts_not_cools(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            # Two losses exceeding the 25.0 kill-switch threshold.
            harness.auto_ghost.report_outcome("t1", "loss", -15.0, asset="EURUSD_otc")
            harness.auto_ghost.report_outcome("t2", "loss", -15.0, asset="EURUSD_otc")
            await _drain_loop(harness.calibration)

            self.assertEqual(harness.calibration.state, "ABORTED")
            # D4: user config restored.
            self.assertEqual(harness.auto_ghost.config.amount, 5.0)
            self.assertEqual(harness.auto_ghost.config.mode, "standard")
            self.assertFalse(harness.auto_ghost.config.oteo_ai_enabled)
            # Entry veto is active after abort.
            veto = harness.calibration._entry_veto()
            self.assertEqual(veto, "calibration_not_accepting_entries")
            # Loud alert emitted on the notification channel (intentional visibility).
            self.assertTrue(any(
                n == "notification" and (p or {}).get("type") == "calibration_aborted"
                for n, p in harness.sio.events
            ))
        finally:
            harness.cleanup()


class TestSessionIdIsolated(unittest.IsolatedAsyncioTestCase):
    """M1/M9: dedicated `auto_ghost_calib_{epoch}` session id."""

    async def test_calibration_session_id_isolated(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            self.assertTrue(harness.auto_ghost._session_id.startswith("auto_ghost_calib_"))
            self.assertEqual(harness.calibration.calibration_id, harness.auto_ghost._session_id)
            await harness.calibration.stop()
            await _drain_loop(harness.calibration)
            self.assertTrue(harness.auto_ghost._session_id.startswith("auto_ghost_"))
            self.assertFalse(harness.auto_ghost._session_id.startswith("auto_ghost_calib_"))
        finally:
            harness.cleanup()


class TestSettingsRestore(unittest.IsolatedAsyncioTestCase):
    """D4: the exact pre-calibration config is auto-restored on DONE."""

    async def test_calibration_settings_restore(self) -> None:
        harness = CalibrationHarness()
        try:
            pre = harness.auto_ghost.config
            await harness.calibration.start()
            # Preset actually overrode user values.
            self.assertEqual(harness.auto_ghost.config.amount, 1.0)
            self.assertEqual(harness.auto_ghost.config.minimum_payout_pct, 85.0)
            self.assertFalse(harness.auto_ghost.config.auto_execute_ai_pulse)
            self.assertTrue(harness.auto_ghost.config.enabled)

            await harness.calibration.stop()
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "DONE")

            post = harness.auto_ghost.config
            self.assertEqual(post.amount, pre.amount)
            self.assertEqual(post.minimum_payout_pct, pre.minimum_payout_pct)
            self.assertEqual(post.auto_execute_ai_pulse, pre.auto_execute_ai_pulse)
            self.assertEqual(post.max_concurrent_trades, pre.max_concurrent_trades)
            self.assertEqual(post.mode, "standard")
            # D4 P1: None optional fields must revert, not keep the preset bounds.
            self.assertIsNone(pre.min_zscore)
            self.assertIsNone(post.min_zscore)
            self.assertIsNone(post.max_zscore)
            self.assertFalse(post.min_zscore_enabled)
            self.assertFalse(post.max_zscore_enabled)
            self.assertIsNone(post.min_confidence)
            self.assertIsNone(post.allowed_regimes)
        finally:
            harness.cleanup()


class TestInFlightDrain(unittest.IsolatedAsyncioTestCase):
    """M10: stop freezes entries, in-flight settle on calibration channels, then DONE."""

    async def test_calibration_in_flight_drain(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            harness.auto_ghost.note_in_flight_settlement()

            await harness.calibration.stop()
            self.assertEqual(harness.calibration.state, "ANALYZING")
            # Entries frozen immediately.
            self.assertEqual(harness.calibration._entry_veto(), "calibration_not_accepting_entries")

            # In-flight settlement completes → drain completes → DONE.
            harness.auto_ghost.release_in_flight_settlement()
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "DONE")
            self.assertIsNone(harness.calibration._entry_veto())
        finally:
            harness.cleanup()


class TestBudgetCountsSettledOnly(unittest.IsolatedAsyncioTestCase):
    """M1: voids are not evidence — budget counts settled win/loss only."""

    async def test_calibration_budget_counts_settled_only(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(target_trades=5)
            harness.auto_ghost.report_outcome("t1", "win", 0.85, asset="EURUSD_otc")
            harness.auto_ghost.report_outcome("t2", "win", 0.85, asset="EURUSD_otc")
            harness.auto_ghost.report_outcome("t3", "loss", -1.0, asset="EURUSD_otc")
            for i in range(3):
                harness.auto_ghost.report_outcome(f"v{i}", "void", 0.0, asset="EURUSD_otc")

            # Let any scheduled transition run (should NOT have fired).
            for _ in range(10):
                await asyncio.sleep(0)

            self.assertEqual(harness.calibration.state, "RUNNING")
            self.assertEqual(harness.calibration.public_status()["settled_total"], 3)
            self.assertEqual(harness.calibration.public_status()["settled_voids"], 3)
        finally:
            harness.cleanup()


class TestStateMachineTransitions(unittest.IsolatedAsyncioTestCase):
    """IDLE→RUNNING→ANALYZING→PROPOSING→DONE; invalid transitions fail loud."""

    async def test_start_while_running_rejected(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            with self.assertRaises(CalibrationStateError):
                await harness.calibration.start()
        finally:
            harness.cleanup()

    async def test_stop_while_idle_rejected(self) -> None:
        harness = CalibrationHarness()
        try:
            with self.assertRaises(CalibrationStateError):
                await harness.calibration.stop()
        finally:
            harness.cleanup()

    async def test_trade_budget_completes_to_done(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(target_trades=4)
            for i in range(4):
                harness.auto_ghost.report_outcome(
                    f"t{i}", "win" if i % 2 else "loss", 0.5, asset="EURUSD_otc"
                )
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "DONE")
            self.assertEqual(harness.calibration.public_status()["settled_total"], 4)
        finally:
            harness.cleanup()

    async def test_time_budget_completes_to_done(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(duration_minutes=25)
            # Simulate elapsed time budget deterministically.
            harness.calibration._started_at -= (harness.calibration._time_budget_seconds + 1)
            harness.auto_ghost.report_outcome("t1", "win", 0.5, asset="EURUSD_otc")
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "DONE")
        finally:
            harness.cleanup()

    async def test_time_budget_seconds_uses_minutes(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(duration_minutes=25)
            self.assertEqual(harness.calibration._time_budget_seconds, 25 * 60)
            self.assertFalse(harness.auto_ghost.config.oteo_ai_enabled)
            self.assertFalse(harness.auto_ghost.config.auto_execute_ai_pulse)
        finally:
            harness.cleanup()


class TestPhase11Contracts(unittest.IsolatedAsyncioTestCase):
    """Phase 1.1: abort drain, sync budget veto, health checkpoints, persist."""

    async def test_calibration_abort_drains_before_live_restore(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            harness.auto_ghost.note_in_flight_settlement()
            harness.auto_ghost.report_outcome("t1", "loss", -15.0, asset="EURUSD_otc")
            harness.auto_ghost.report_outcome("t2", "loss", -15.0, asset="EURUSD_otc")
            await asyncio.sleep(0.05)
            # Drain in progress: still in calibration mode so settlement stays silent.
            self.assertEqual(harness.auto_ghost.config.mode, "calibration")
            self.assertIn(harness.calibration.state, {"ANALYZING", "PROPOSING", "RUNNING"})
            harness.auto_ghost.release_in_flight_settlement()
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "ABORTED")
            self.assertEqual(harness.auto_ghost.config.mode, "standard")
        finally:
            harness.cleanup()

    async def test_calibration_entry_veto_on_trade_budget(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(target_trades=4)
            # H5: veto must fire while still RUNNING (before async finalize).
            harness.calibration._settled_wins = 4
            self.assertEqual(harness.calibration.state, "RUNNING")
            self.assertEqual(
                harness.calibration._entry_veto(),
                "calibration_trade_budget_reached",
            )
        finally:
            harness.cleanup()

    async def test_calibration_health_checkpoint_every_four(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(target_trades=24)
            for i in range(4):
                harness.auto_ghost.report_outcome(
                    f"t{i}", "win", 0.5, asset="EURUSD_otc"
                )
            events = [e["event"] for e in harness.calibration._changelog]
            self.assertIn("health_checkpoint", events)
            self.assertEqual(harness.calibration.state, "RUNNING")
        finally:
            harness.cleanup()

    async def test_calibration_drain_waits_for_emit_not_capacity(self) -> None:
        """H2: clearing `_active_assets` must not finalize before the settlement emit."""
        harness = CalibrationHarness()
        try:
            from app.backend.services.trade_service import TradeService
            from app.backend.models.domain import TradeRecord, TradeKind

            await harness.calibration.start()
            harness.auto_ghost.note_in_flight_settlement()
            harness.auto_ghost._active_assets.discard("EURUSD_otc")

            ts = object.__new__(TradeService)
            ts.sio = harness.sio
            ts._auto_ghost = harness.auto_ghost

            trade = TradeRecord(
                session_id=harness.auto_ghost._session_id,
                asset="EURUSD_otc",
                direction="call",
                amount=1.0,
                expiration_seconds=60,
                broker="pocket_option",
                kind=TradeKind.GHOST,
                success=True,
                message="test",
                trade_id="ghost-drain",
                entry_price=1.1,
                entry_time=1000.0,
                exit_price=1.2,
                exit_time=1060.0,
                outcome="win",
                profit=0.85,
                simulated_profit=0.85,
                payout_pct=85.0,
                entry_context={"z_score": 0.5},
            )

            await harness.calibration.stop()
            self.assertEqual(harness.calibration.state, "ANALYZING")
            self.assertEqual(harness.auto_ghost.config.mode, "calibration")

            await ts._emit_trade_result(trade)
            event_names = [n for n, _ in harness.sio.events]
            self.assertIn("calibration_trade_result", event_names)
            self.assertNotIn("trade_result", event_names)

            harness.auto_ghost.release_in_flight_settlement()
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "DONE")
        finally:
            harness.cleanup()

    async def test_milestone_catastrophic_applies_one_family(self) -> None:
        harness = CalibrationHarness()

        async def fake_ai(settled, is_final, current):
            return (
                '```json\n{"tier_a_changes":['
                '{"field":"bayesian_min_probability","new":0.62,"rationale":"wipeout","evidence_n":12},'
                '{"field":"min_zscore","new":-1.0,"rationale":"also","evidence_n":12}'
                '],"tier_b_proposals":[],"observations":[]}\n```'
            )

        harness.calibration._ai_reviewer = fake_ai
        try:
            await harness.calibration.start()
            for i in range(12):
                harness.auto_ghost.report_outcome(f"t{i}", "loss", -1.0, asset="EURUSD_otc")
            for _ in range(80):
                await asyncio.sleep(0.05)
                if harness.calibration._milestones:
                    break
            self.assertTrue(harness.calibration._milestones)
            self.assertEqual(harness.auto_ghost.config.bayesian_min_probability, 0.62)
            self.assertEqual(harness.auto_ghost.config.min_zscore, -2.5)
            self.assertIn("calibration_milestone", [n for n, _ in harness.sio.events])
        finally:
            harness.cleanup()

    async def test_calibration_persist_includes_counters(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start(target_trades=24)
            harness.auto_ghost.report_outcome("t1", "win", 0.85, asset="EURUSD_otc")
            path = Path(harness.tmp.name) / f"{harness.calibration.calibration_id}.json"
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["settled_wins"], 1)
            self.assertEqual(payload["settled_losses"], 0)
            self.assertEqual(payload["calibration_pnl"], 0.85)
        finally:
            harness.cleanup()

class TestFinalizeCrashSafety(unittest.IsolatedAsyncioTestCase):
    """R1-1/R1-2 (C-B): a failing or timing-out final AI review must NEVER leave
    calibration stranded in PROPOSING with the 409 lock / entry veto active.
    D4 restore + unwiring must happen regardless of review outcome.
    """

    async def _run_with_reviewer(self, reviewer, *, expect_state: str) -> CalibrationHarness:
        harness = CalibrationHarness()
        harness.calibration._ai_reviewer = reviewer
        try:
            await harness.calibration.start()
            self.assertTrue(harness.calibration.is_locked())
            await harness.calibration._finalize(final_state="DONE")
            self.assertEqual(harness.calibration.state, expect_state)
            self.assertFalse(harness.calibration.is_locked())
            # D4 restore + unwiring must have completed regardless of review outcome.
            self.assertEqual(harness.auto_ghost.config.mode, "standard")
            self.assertIsNone(harness.auto_ghost._entry_veto_check)
            self.assertNotIn(
                harness.calibration._on_outcome, harness.auto_ghost._outcome_observers
            )
            self.assertEqual(harness.auto_ghost.config.amount, 5.0)  # pre-start amount
            return harness
        except Exception:
            harness.cleanup()
            raise

    async def test_finalize_review_raises_forces_aborted_and_releases(self) -> None:
        async def reviewer(settled, is_final, current):
            raise RuntimeError("simulated provider crash")

        harness = await self._run_with_reviewer(reviewer, expect_state="ABORTED")
        harness.cleanup()

    async def test_finalize_review_timeout_still_restores(self) -> None:
        async def reviewer(settled, is_final, current):
            await asyncio.sleep(0.5)
            return ""

        with mock.patch(
            "app.backend.services.calibration_service.MILESTONE_AI_TIMEOUT_SECONDS",
            0.05,
        ):
            harness = await self._run_with_reviewer(reviewer, expect_state="DONE")
        harness.cleanup()


class TestEscapeHatch(unittest.IsolatedAsyncioTestCase):
    """R1-4 (H-2): stop() works from ANALYZING; abort() rescues a stranded
    finalize so the user is never locked out of recovery.
    """

    async def test_stop_works_from_analyzing(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            # Force ANALYZING without a live drain (simulates a drain already
            # recovered mid-drain / second stop while draining).
            harness.calibration._state = "ANALYZING"
            harness.calibration._stop_requested = True
            harness.calibration._stop_reason = "test"
            await harness.calibration.stop()  # must NOT raise now
            self.assertEqual(harness.calibration.state, "ANALYZING")
            await _drain_loop(harness.calibration)
            self.assertEqual(harness.calibration.state, "DONE")
            self.assertFalse(harness.calibration.is_locked())
        finally:
            harness.cleanup()

    async def test_abort_rescues_stranded_finalize(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            # Simulate a stranded finalize: flag set, no live drain/finalize task.
            harness.calibration._finalizing = True
            harness.calibration._state = "ANALYZING"
            await harness.calibration.abort(reason="simulated_strand")
            self.assertEqual(harness.calibration.state, "ABORTED")
            self.assertFalse(harness.calibration.is_locked())
            self.assertEqual(harness.auto_ghost.config.mode, "standard")
        finally:
            harness.cleanup()

class TestStartupReconciliation(unittest.IsolatedAsyncioTestCase):
    """R1-3 (C-A): non-terminal persisted sessions are marked STALE_ABORTED at
    bind time with a changelog entry; orphan .json.tmp files are removed.
    """

    async def test_startup_reconciliation_stale_sessions(self) -> None:
        harness = CalibrationHarness()
        try:
            stale = Path(harness.tmp.name) / "auto_ghost_calib_11111111.json"
            tmp_artifact = Path(harness.tmp.name) / "auto_ghost_calib_11111111.json.tmp"
            stale.write_text(json.dumps({
                "calibration_id": "auto_ghost_calib_11111111",
                "state": "PROPOSING",
                "settled_wins": 13,
                "settled_losses": 11,
                "changelog": [],
            }), encoding="utf-8")
            tmp_artifact.write_text("leftover", encoding="utf-8")
            fresh = Path(harness.tmp.name) / "auto_ghost_calib_22222222.json"
            fresh.write_text(json.dumps({
                "calibration_id": "auto_ghost_calib_22222222",
                "state": "DONE",
                "changelog": [],
            }), encoding="utf-8")

            # Re-bind to trigger reconciliation (R5: one-shot per process — reset the
            # flag to simulate a fresh boot, as the R1 contract tests a boot-time scan).
            harness.calibration._reconcile_done = False
            harness.calibration.bind(harness.auto_ghost, harness.sio)

            payload = json.loads(stale.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "STALE_ABORTED")
            self.assertIn("reconciled_stale", [e.get("event") for e in payload["changelog"]])
            self.assertEqual(payload["final_report"]["final_state"], "STALE_ABORTED")
            # DONE session untouched; orphan .tmp removed.
            self.assertEqual(json.loads(fresh.read_text(encoding="utf-8"))["state"], "DONE")
            self.assertFalse(tmp_artifact.exists())
        finally:
            harness.cleanup()


class TestSessionIdIntegrity(unittest.IsolatedAsyncioTestCase):
    """R1-5 (H-3): starting calibration while Auto-Ghost is disabled yields a
    single authoritative calibration session id — deterministically, independent
    of second-boundary minting.
    """

    async def test_calibration_start_when_ghost_disabled_single_session(self) -> None:
        harness = CalibrationHarness()
        try:
            self.assertFalse(harness.auto_ghost.config.enabled)
            await harness.calibration.start()
            self.assertEqual(harness.auto_ghost._session_id, harness.calibration.calibration_id)
            self.assertTrue(harness.auto_ghost._session_id.startswith("auto_ghost_calib_"))
            await harness.calibration.stop()
            await _drain_loop(harness.calibration)
            self.assertTrue(harness.auto_ghost._session_id.startswith("auto_ghost_"))
            self.assertFalse(harness.auto_ghost._session_id.startswith("auto_ghost_calib_"))
        finally:
            harness.cleanup()


class TestBaselineMissingNotification(unittest.IsolatedAsyncioTestCase):
    """R3-2 (H-1): arming the Guardian without a KB warm-start baseline is LOUD —
    a one-time warning notification is emitted. Never silent degradation."""

    async def test_guardian_arm_without_baseline_emits_warning(self) -> None:
        harness = CalibrationHarness()
        try:
            # Point the baseline path at a guaranteed-missing file (deterministic
            # regardless of whether a real baseline exists in the repo data dir).
            missing = Path(harness.tmp.name) / "missing_warm_start_baseline.json"
            harness.calibration._warm_start_path = lambda: missing
            await harness.calibration.start()
            harness.calibration._arm_guardian()
            await asyncio.sleep(0.05)
            warns = [
                (n, p) for n, p in harness.sio.events
                if n == "notification" and (p or {}).get("type") == "warning"
            ]
            self.assertTrue(warns, "no warning notification emitted for missing baseline")
            self.assertIn("warm-start baseline", warns[0][1]["message"].lower())
        finally:
            harness.cleanup()


class TestReconcileOneShot(unittest.IsolatedAsyncioTestCase):
    """R5: startup reconciliation is ONE-SHOT per process and NEVER touches the
    in-memory active calibration's own session file (notification-bell spam +
    live-run file corruption, observed 2026-08-31 while a calibration ran)."""

    def _write_stale(self, path: Path, calibration_id: str) -> None:
        path.write_text(json.dumps({
            "calibration_id": calibration_id,
            "state": "RUNNING",
            "changelog": [],
        }), encoding="utf-8")

    async def test_reconcile_runs_once_across_rebinds(self) -> None:
        harness = CalibrationHarness()
        try:
            stale = Path(harness.tmp.name) / "auto_ghost_calib_99990001.json"
            self._write_stale(stale, "auto_ghost_calib_99990001")

            # Simulate a fresh process, then re-bind repeatedly (as the
            # calibration API endpoints do on every call).
            harness.calibration._reconcile_done = False
            harness.calibration.bind(harness.auto_ghost, harness.sio)
            harness.calibration.bind(harness.auto_ghost, harness.sio)
            harness.calibration.bind(harness.auto_ghost, harness.sio)
            await asyncio.sleep(0.05)  # flush the scheduled notification task

            payload = json.loads(stale.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "STALE_ABORTED")
            events = [e.get("event") for e in payload["changelog"]]
            self.assertEqual(events.count("reconciled_stale"), 1)
            warnings = [
                p for n, p in harness.sio.events
                if n == "notification" and (p or {}).get("type") == "warning"
            ]
            self.assertEqual(len(warnings), 1)
        finally:
            harness.cleanup()

    async def test_reconcile_never_marks_active_calibration(self) -> None:
        harness = CalibrationHarness()
        try:
            await harness.calibration.start()
            active_id = harness.calibration.calibration_id
            active_file = Path(harness.tmp.name) / f"{active_id}.json"
            self.assertTrue(active_file.exists())

            # Force a re-bind that would re-run reconcile without the one-shot
            # flag — the active run's own file must be skipped.
            harness.calibration._reconcile_done = False
            harness.calibration.bind(harness.auto_ghost, harness.sio)

            payload = json.loads(active_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "RUNNING")
            self.assertNotIn(
                "reconciled_stale",
                [e.get("event") for e in payload.get("changelog", [])],
            )
        finally:
            harness.cleanup()


    async def test_reconcile_restores_snapshot_and_prunes_done(self) -> None:
        harness = CalibrationHarness()
        try:
            # Create a stale file with a snapshot that had custom amount 17.5
            stale_file = Path(harness.tmp.name) / "auto_ghost_calib_99990002.json"
            stale_file.write_text(json.dumps({
                "calibration_id": "auto_ghost_calib_99990002",
                "state": "RUNNING",
                "config_snapshot": {"amount": 17.5},
                "changelog": [],
            }), encoding="utf-8")

            # Create 25 dummy DONE session files
            for i in range(25):
                done_file = Path(harness.tmp.name) / f"auto_ghost_calib_done_{i:02d}.json"
                done_file.write_text(json.dumps({
                    "calibration_id": f"auto_ghost_calib_done_{i:02d}",
                    "state": "DONE",
                    "changelog": [],
                }), encoding="utf-8")

            harness.calibration._reconcile_done = False
            harness.calibration.bind(harness.auto_ghost, harness.sio)

            # 1. Config should have been restored from the interrupted session's snapshot
            self.assertEqual(harness.auto_ghost.config.amount, 17.5)

            # 2. DONE files should be pruned to at most 20
            remaining_done = [
                p for p in Path(harness.tmp.name).glob("auto_ghost_calib_done_*.json")
            ]
            self.assertEqual(len(remaining_done), 20)

            # 3. STALE_ABORTED file is kept
            self.assertTrue(stale_file.exists())
            self.assertEqual(json.loads(stale_file.read_text(encoding="utf-8"))["state"], "STALE_ABORTED")
        finally:
            harness.cleanup()


class TestGuardianNotificationTypes(unittest.IsolatedAsyncioTestCase):
    """Test that Guardian emits guardian_proposal and guardian_alignment types, not ai_pulse."""

    async def test_guardian_notification_types(self) -> None:
        harness = CalibrationHarness()
        try:
            # Prime baseline
            harness.calibration._warm_start_baseline = {
                "feature_centroids": {
                    "overall": {
                        "volatility": {"mean": 0.001, "std": 0.0001},
                        "liquidity": {"mean": 100.0, "std": 10.0},
                        "manipulation": {"mean": 0.0, "std": 0.0},
                        "z_score": {"mean": 0.0, "std": 1.0},
                    }
                }
            }

            trades = [
                {
                    "trade_id": f"t_{i}",
                    "asset": "EURUSD_otc",
                    "outcome": "loss",
                    "profit": -5.0,
                    "entry_price": 1.0500,
                    "exit_price": 1.0490,
                    "direction": "call",
                    "entry_time": 1000 + i * 60,
                    "exit_time": 1060 + i * 60,
                    "market_context": {
                        "volatility": 0.0005,
                        "liquidity": 50.0,
                        "manipulation": 2.0,
                        "z_score": 1.5,
                        "utc_4h_block": 2,
                    },
                }
                for i in range(20)
            ]

            await harness.calibration._run_alignment_and_drift(trades)

            # Check that any emitted notifications do NOT use type "ai_pulse"
            notif_events = [p for n, p in harness.sio.events if n == "notification"]
            for notif in notif_events:
                self.assertNotEqual(notif.get("type"), "ai_pulse")
            # Should have emitted a guardian_alignment notification
            alignment_notifs = [p for p in notif_events if p.get("type") == "guardian_alignment"]
            self.assertTrue(len(alignment_notifs) > 0)
        finally:
            harness.cleanup()


if __name__ == "__main__":
    unittest.main()




