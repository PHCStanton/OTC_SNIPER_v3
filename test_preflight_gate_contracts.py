"""
Pre-Flight Gate Contract Tests (C1 remediation verification).

Verifies that:
1. `_get_asset_market_context_snapshot` exposes a well-formed `recent_ticks` list.
2. `schedule_candle_open_pulse_execution` forwards non-empty `recent_ticks`
   into `HTFDirectionalBiasEngine.evaluate_directional_confluence`.
3. Lopsided adverse tick flow now triggers the DIVERGENT veto end-to-end
   (previously dead code due to the missing key contract).
"""

from __future__ import annotations

import asyncio
import time
import unittest
from collections import deque
from unittest.mock import patch

from app.backend.services.auto_ghost import AutoGhostService, AutoGhostConfig
from app.backend.services.streaming import StreamingService
from app.backend.services.htf_directional_bias import HTFDirectionalBiasEngine


def _make_streaming_service() -> StreamingService:
    """Lightweight instance bypassing heavy constructor dependencies."""
    service = object.__new__(StreamingService)
    service._market_context_engines = {}
    service._last_manip_flags = {}
    service._last_regime = {}
    service._recent_ticks = {}
    service._latest_bayesian_wp = {}
    return service


class _GateTradeServiceStub:
    """Minimal trade-service stub exposing only what the pre-flight gate touches."""

    def __init__(self, market_context: dict):
        self._mc = market_context
        self.executed: list[dict] = []

    def _get_market_context(self, asset: str) -> dict:
        return self._mc

    def _latest_logged_price(self, asset: str):
        return None


class TestSnapshotRecentTicksContract(unittest.TestCase):
    """C1 contract: the context snapshot must expose recent_ticks."""

    def test_snapshot_exposes_well_formed_recent_ticks(self) -> None:
        service = _make_streaming_service()
        now = time.time()
        service._recent_ticks["EURUSD_otc"] = deque(
            [{"t": now - i, "p": 1.1000 + i * 0.00001} for i in range(50)],
            maxlen=600,
        )

        ctx = service._get_asset_market_context_snapshot("EURUSD_otc")

        self.assertIn("recent_ticks", ctx)
        ticks = ctx["recent_ticks"]
        self.assertEqual(len(ticks), 50)
        for tick in ticks:
            self.assertIn("t", tick)
            self.assertIn("p", tick)
            self.assertIsInstance(tick["t"], float)
            self.assertIsInstance(tick["p"], float)

    def test_snapshot_unknown_asset_returns_empty_recent_ticks(self) -> None:
        service = _make_streaming_service()
        ctx = service._get_asset_market_context_snapshot("UNKNOWN_otc")
        self.assertEqual(ctx.get("recent_ticks"), [])


class TestPreFlightGateReceivesTicks(unittest.IsolatedAsyncioTestCase):
    """C1 integration: the scheduled pulse gate must consume the tick buffer."""

    async def test_gate_forwards_non_empty_recent_ticks(self) -> None:
        now = time.time()
        market_context = {
            "closed_candles": [],
            "recent_ticks": [
                {"t": now - i * 0.5, "p": 1.1000 + (i % 5) * 0.00002}
                for i in range(80)
            ],
            "manipulation": {},
        }
        trade_service = _GateTradeServiceStub(market_context)
        service = AutoGhostService(trade_service, config=AutoGhostConfig(enabled=True))

        captured: dict = {}

        original = HTFDirectionalBiasEngine.evaluate_directional_confluence

        def spy(self_engine, *, asset, direction, candles_1m, recent_ticks, current_ts=None):
            captured["recent_ticks"] = recent_ticks
            captured["candles_1m"] = candles_1m
            return {
                "asset": asset,
                "direction": direction,
                "confluence_status": "ALIGNED",
                "confluence_score": 10.0,
                "calibrated_bayesian_floor": 0.535,
                "veto": False,
                "veto_reason": None,
            }

        async def _noop_sleep(_seconds):
            return None

        async def _fake_execute(**kwargs):
            trade_service.executed.append(kwargs)
            return {"success": True}

        with patch.object(HTFDirectionalBiasEngine, "evaluate_directional_confluence", spy), \
             patch("app.backend.services.auto_ghost.asyncio.sleep", _noop_sleep), \
             patch.object(service, "execute_ai_pulse_signal", _fake_execute):
            await service.schedule_candle_open_pulse_execution(
                asset="EURUSD_otc",
                direction="CALL",
                target_price=None,
                wait_minutes=1,
                target_expiration=60,
                confidence=85,
            )

        self.assertIn("recent_ticks", captured)
        self.assertGreater(len(captured["recent_ticks"]), 0)
        self.assertEqual(len(trade_service.executed), 1)


class TestAdverseTickFlowVeto(unittest.IsolatedAsyncioTestCase):
    """C1 behavioral proof: previously-dead DIVERGENT veto now fires."""

    async def test_lopsided_downward_flow_vetoes_call(self) -> None:
        # 40 strictly descending ticks inside the 60s window -> ratio 0% -> DIVERGENT + veto
        base_ts = time.time()
        recent_ticks = [
            {"t": base_ts - i * 0.5, "p": 1.1000 - i * 0.00005} for i in range(40)
        ]
        market_context = {
            "closed_candles": [],
            "recent_ticks": recent_ticks,
            "manipulation": {},
        }
        trade_service = _GateTradeServiceStub(market_context)
        service = AutoGhostService(trade_service, config=AutoGhostConfig(enabled=True))

        async def _noop_sleep(_seconds):
            return None

        async def _fail_execute(**kwargs):  # must NOT be reached
            raise AssertionError("Execution must have been vetoed by tick-flow gate")

        with patch("app.backend.services.auto_ghost.asyncio.sleep", _noop_sleep), \
             patch.object(service, "execute_ai_pulse_signal", _fail_execute):
            await service.schedule_candle_open_pulse_execution(
                asset="EURUSD_otc",
                direction="CALL",
                target_price=None,
                wait_minutes=1,
                target_expiration=60,
                confidence=85,
            )

        self.assertEqual(len(trade_service.executed), 0)

    async def test_balanced_flow_does_not_veto(self) -> None:
        # Alternating up/down ticks -> ~50% ratio -> ALIGNED, no veto
        base_ts = time.time()
        recent_ticks = []
        price = 1.1000
        for i in range(60):
            price += 0.00003 if i % 2 == 0 else -0.00003
            recent_ticks.append({"t": base_ts - (59 - i) * 0.5, "p": price})
        market_context = {
            "closed_candles": [],
            "recent_ticks": recent_ticks,
            "manipulation": {},
        }
        trade_service = _GateTradeServiceStub(market_context)
        service = AutoGhostService(trade_service, config=AutoGhostConfig(enabled=True))

        executed: list[dict] = []

        async def _noop_sleep(_seconds):
            return None

        async def _fake_execute(**kwargs):
            executed.append(kwargs)
            return {"success": True}

        with patch("app.backend.services.auto_ghost.asyncio.sleep", _noop_sleep), \
             patch.object(service, "execute_ai_pulse_signal", _fake_execute):
            await service.schedule_candle_open_pulse_execution(
                asset="EURUSD_otc",
                direction="CALL",
                target_price=None,
                wait_minutes=1,
                target_expiration=60,
                confidence=85,
            )

        self.assertEqual(len(executed), 1)




def _balanced_mc() -> dict:
    """Market context with balanced tick flow (no veto) for gate tests."""
    base_ts = time.time()
    ticks = []
    price = 1.1000
    for i in range(60):
        price += 0.00003 if i % 2 == 0 else -0.00003
        ticks.append({"t": base_ts - (59 - i) * 0.5, "p": price})
    return {"closed_candles": [], "recent_ticks": ticks, "manipulation": {}}


class TestBayesianFloorGate(unittest.IsolatedAsyncioTestCase):
    """C2 remediation: Bayesian floor enforced fail-closed at the pre-flight gate."""

    def _service(self, mc: dict) -> tuple:
        trade_service = _GateTradeServiceStub(mc)
        service = AutoGhostService(
            trade_service,
            config=AutoGhostConfig(enabled=True, bayesian_filter_enabled=True),
        )
        return service, trade_service

    async def _run(self, service: AutoGhostService, executed: list) -> None:
        async def _noop_sleep(_seconds):
            return None

        async def _fake_execute(**kwargs):
            executed.append(kwargs)
            return {"success": True}

        with patch("app.backend.services.auto_ghost.asyncio.sleep", _noop_sleep), \
             patch.object(service, "execute_ai_pulse_signal", _fake_execute):
            await service.schedule_candle_open_pulse_execution(
                asset="EURUSD_otc",
                direction="CALL",
                target_price=None,
                wait_minutes=1,
                target_expiration=60,
                confidence=85,
            )

    async def test_missing_wp_fails_closed(self) -> None:
        service, trade_service = self._service(_balanced_mc())
        executed: list = []
        await self._run(service, executed)
        self.assertEqual(len(executed), 0)

    async def test_wp_below_floor_aborts(self) -> None:
        mc = _balanced_mc()
        mc["bayesian_win_probability_60s"] = 0.50
        service, trade_service = self._service(mc)
        executed: list = []
        await self._run(service, executed)
        self.assertEqual(len(executed), 0)

    async def test_wp_above_floor_executes(self) -> None:
        mc = _balanced_mc()
        mc["bayesian_win_probability_60s"] = 0.56
        service, trade_service = self._service(mc)
        executed: list = []
        await self._run(service, executed)
        self.assertEqual(len(executed), 1)

    async def test_filter_disabled_backward_compatible(self) -> None:
        mc = _balanced_mc()  # no WP present
        trade_service = _GateTradeServiceStub(mc)
        service = AutoGhostService(
            trade_service,
            config=AutoGhostConfig(enabled=True, bayesian_filter_enabled=False),
        )
        executed: list = []
        await self._run(service, executed)
        self.assertEqual(len(executed), 1)


class TestSnapshotBayesianWpContract(unittest.TestCase):
    """C2 contract: the context snapshot exposes cached Bayesian WP keys."""

    def test_snapshot_exposes_cached_wp(self) -> None:
        service = _make_streaming_service()
        service._latest_bayesian_wp["EURUSD_otc"] = {
            "bayesian_win_probability": 0.5512,
            "bayesian_win_probability_60s": 0.5512,
            "bayesian_win_probability_300s": 0.5401,
        }
        ctx = service._get_asset_market_context_snapshot("EURUSD_otc")
        self.assertAlmostEqual(ctx["bayesian_win_probability_60s"], 0.5512)
        self.assertAlmostEqual(ctx["bayesian_win_probability_300s"], 0.5401)

    def test_snapshot_without_wp_has_no_keys(self) -> None:
        service = _make_streaming_service()
        ctx = service._get_asset_market_context_snapshot("EURUSD_otc")
        self.assertNotIn("bayesian_win_probability_60s", ctx)


class _RaceTradeServiceStub:
    """Trade-service stub whose execute_trade yields, exposing any TOCTOU window."""

    def __init__(self):
        self.calls = 0

    async def execute_trade(self, broker_type, request):
        self.calls += 1
        await asyncio.sleep(0.05)
        return {"success": True, "trade_id": f"RACE-{self.calls}"}


class TestCapacityRace(unittest.IsolatedAsyncioTestCase):
    """C3 remediation: concurrent signals must never exceed max_concurrent_trades."""

    async def test_concurrent_signals_never_oversubscribe(self) -> None:
        trade_service = _RaceTradeServiceStub()
        service = AutoGhostService(
            trade_service,
            config=AutoGhostConfig(enabled=True, max_concurrent_trades=1),
        )

        async def _noop_release(_asset, _delay):
            return None

        base_oteo = {
            "recommended": "CALL",
            "actionable": True,
            "oteo_score": 80.0,
            "confidence": "HIGH",
        }

        results = await asyncio.gather(
            service.consider_signal(
                asset="AAA_otc",
                price=1.0,
                timestamp=time.time(),
                oteo_result=dict(base_oteo),
                manipulation={},
                payout_pct=90.0,
            ),
            service.consider_signal(
                asset="BBB_otc",
                price=1.0,
                timestamp=time.time(),
                oteo_result=dict(base_oteo),
                manipulation={},
                payout_pct=90.0,
            ),
        )

        executed = [r for r in results if isinstance(r, dict) and r.get("success")]
        self.assertEqual(len(executed), 1)
        self.assertEqual(trade_service.calls, 1)

    async def test_failed_execution_releases_reserved_capacity(self) -> None:
        class _FailStub:
            async def execute_trade(self, broker_type, request):
                return {"success": False, "message": "broker offline"}

        trade_service = _FailStub()
        service = AutoGhostService(
            trade_service,
            config=AutoGhostConfig(enabled=True, max_concurrent_trades=2),
        )
        result = await service.consider_signal(
            asset="CCC_otc",
            price=1.0,
            timestamp=time.time(),
            oteo_result={"recommended": "PUT", "actionable": True, "oteo_score": 75.0},
            manipulation={},
            payout_pct=90.0,
        )
        self.assertIsNotNone(result)
        self.assertFalse(result.get("success"))
        self.assertNotIn("CCC_otc", service._active_assets)

class _SioEventCapture:
    """Socket.IO stub that records emitted events for assertion."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    async def emit(self, event: str, data: dict) -> None:
        self.events.append((event, data))


class TestExecutePulseAbortEmission(unittest.IsolatedAsyncioTestCase):
    """H7 remediation: all skip paths in execute_ai_pulse_signal emit ai_pulse_aborted."""

    def _service(self, **config_kwargs) -> tuple:
        trade_service = _GateTradeServiceStub(_balanced_mc())
        trade_service.sio = _SioEventCapture()
        service = AutoGhostService(
            trade_service,
            config=AutoGhostConfig(enabled=True, **config_kwargs),
        )
        return service, trade_service

    def _aborted_events(self, trade_service) -> list:
        return [e for e in trade_service.sio.events if e[0] == "ai_pulse_aborted"]

    async def test_disabled_emits_abort(self) -> None:
        service, ts = self._service()
        service.config = AutoGhostConfig(enabled=False)
        result = await service.execute_ai_pulse_signal(asset="EURUSD_otc", direction="CALL")
        self.assertIsNone(result)
        aborted = self._aborted_events(ts)
        self.assertEqual(len(aborted), 1)
        self.assertEqual(aborted[0][1]["asset"], "EURUSD_otc")
        self.assertIn("disabled", aborted[0][1]["reason"].lower())

    async def test_active_asset_emits_abort(self) -> None:
        service, ts = self._service()
        service._active_assets.add("EURUSD_otc")
        result = await service.execute_ai_pulse_signal(asset="EURUSD_otc", direction="CALL")
        self.assertIsNone(result)
        aborted = self._aborted_events(ts)
        self.assertEqual(len(aborted), 1)
        self.assertIn("active", aborted[0][1]["reason"].lower())

    async def test_max_concurrent_emits_abort(self) -> None:
        service, ts = self._service(max_concurrent_trades=1)
        service._active_assets.add("OTHER_otc")
        result = await service.execute_ai_pulse_signal(asset="EURUSD_otc", direction="CALL")
        self.assertIsNone(result)
        aborted = self._aborted_events(ts)
        self.assertEqual(len(aborted), 1)
        self.assertIn("concurrent", aborted[0][1]["reason"].lower())

    async def test_execution_failure_emits_abort(self) -> None:
        class _FailStub(_GateTradeServiceStub):
            async def execute_trade(self, broker_type, request):
                raise RuntimeError("broker offline")

        ts = _FailStub(_balanced_mc())
        ts.sio = _SioEventCapture()
        service = AutoGhostService(ts, config=AutoGhostConfig(enabled=True))
        result = await service.execute_ai_pulse_signal(asset="EURUSD_otc", direction="CALL")
        self.assertIsNone(result)
        aborted = self._aborted_events(ts)
        self.assertEqual(len(aborted), 1)
        self.assertIn("failed", aborted[0][1]["reason"].lower())


class TestSnapshotRegimeKeysContract(unittest.TestCase):
    """M1 remediation: snapshot reads regime_confidence/regime_stable from classifier-shaped dicts."""

    def test_snapshot_populates_regime_keys_from_classifier_shape(self) -> None:
        service = _make_streaming_service()
        # Exact shape emitted by RegimeClassifier._emit()
        service._last_regime["EURUSD_otc"] = {
            "regime_label": "RANGE_BOUND",
            "regime_confidence": 72.5,
            "regime_detail": {"adx": 15.0},
            "regime_prior": None,
            "regime_stable": True,
            "regime_persistence": 4,
        }
        ctx = service._get_asset_market_context_snapshot("EURUSD_otc")
        self.assertAlmostEqual(ctx["regime_confidence"], 72.5)
        self.assertTrue(ctx["regime_stable"])
        self.assertEqual(ctx["regime_label"], "RANGE_BOUND")

    def test_snapshot_without_regime_defaults_to_none(self) -> None:
        service = _make_streaming_service()
        ctx = service._get_asset_market_context_snapshot("EURUSD_otc")
        self.assertIsNone(ctx.get("regime_confidence"))
        self.assertIsNone(ctx.get("regime_stable"))


class TestStreamingSettingsForwardingContract(unittest.TestCase):
    """Verify update_runtime_settings forwards all gate parameters, including zscore, to auto_ghost."""

    def test_zscore_and_gate_settings_forwarded_to_auto_ghost(self) -> None:
        service = _make_streaming_service()
        service.level2_enabled = False
        service.level3_enabled = False
        service.oteo_ai_enabled = False
        service.oteo_ai_execution_mode = "advisory"
        service._streaming_active = False

        ghost_service = AutoGhostService(_GateTradeServiceStub({}))
        service.auto_ghost = ghost_service

        # Update runtime settings with zscore gate configurations
        service.update_runtime_settings(
            auto_ghost_min_zscore_enabled=True,
            auto_ghost_min_zscore=-1.25,
            auto_ghost_max_zscore_enabled=True,
            auto_ghost_max_zscore=2.5,
            auto_ghost_regime_gate_enabled=True,
        )

        cfg = service.auto_ghost.config
        self.assertTrue(cfg.min_zscore_enabled)
        self.assertEqual(cfg.min_zscore, -1.25)
        self.assertTrue(cfg.max_zscore_enabled)
        self.assertEqual(cfg.max_zscore, 2.5)
        self.assertTrue(cfg.regime_gate_enabled)


if __name__ == "__main__":
    unittest.main()

