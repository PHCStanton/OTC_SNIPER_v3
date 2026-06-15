import unittest

from app.backend.services.auto_ghost import AutoGhostConfig, AutoGhostService
from app.backend.services.market_context import (
    Candle,
    Level2Config,
    MarketContextEngine,
    _detect_cci_divergence,
    apply_level3_policy,
)


def _oteo_result(**overrides):
    result = {
        "oteo_score": 60.0,
        "recommended": "CALL",
        "confidence": "MEDIUM",
        "actionable": True,
        "level2_suppressed_reason": None,
        "market_context": {
            "adx_regime": "moderate",
            "cci_state": "oversold",
            "tick_health": "healthy",
            "cci_divergence": None,
        },
    }
    result.update(overrides)
    return result


def _market_context(**overrides):
    context = {
        "trend_direction": "up",
        "tick_health": "healthy",
        "cci_divergence": None,
    }
    context.update(overrides)
    return context


def _regime(**overrides):
    regime = {
        "regime_label": "RANGE_BOUND",
        "regime_confidence": 80.0,
        "regime_stable": True,
    }
    regime.update(overrides)
    return regime


class _TradeServiceStub:
    def __init__(self) -> None:
        self.requests = []

    async def execute_trade(self, broker_type, request):
        self.requests.append((broker_type, request))
        return {"success": True, "trade_id": f"ghost-{len(self.requests)}"}


class Level3Phase3MarketContextTests(unittest.TestCase):
    def test_tick_frequency_and_health_are_exposed(self) -> None:
        engine = MarketContextEngine(config=Level2Config(candle_seconds=60))

        first = engine.update_tick(1.0000, timestamp=0.0)
        second = engine.update_tick(1.0001, timestamp=2.0)
        third = engine.update_tick(1.0002, timestamp=4.0)

        self.assertEqual(first["tick_health"], "warming_up")
        self.assertEqual(second["tick_health"], "healthy")
        self.assertEqual(third["tick_health"], "healthy")
        self.assertEqual(third["tick_frequency"], 30.0)

    def test_tick_frequency_is_capped_for_extreme_feeds(self) -> None:
        engine = MarketContextEngine(config=Level2Config(candle_seconds=60))

        engine.update_tick(1.0000, timestamp=0.0)
        capped = engine.update_tick(1.0001, timestamp=0.01)

        self.assertEqual(capped["tick_frequency"], 300.0)
        self.assertEqual(capped["tick_health"], "healthy")

    def test_detect_cci_divergence_flags_bullish_pattern(self) -> None:
        candles = [
            Candle(index, 100.0 - index, 101.0 - index, 100.0 - index, 100.5 - index)
            for index in range(5)
        ] + [
            Candle(index + 5, 95.0 - index, 96.0 - index, 94.0 - index, 95.5 - index)
            for index in range(5)
        ]
        cci_values = [-220.0, -210.0, -205.0, -195.0, -190.0, -150.0, -140.0, -135.0, -130.0, -125.0]

        self.assertEqual(_detect_cci_divergence(candles, cci_values), "bullish")


class Level3Phase3PolicyTests(unittest.TestCase):
    def test_dead_market_suppresses_signal(self) -> None:
        result = apply_level3_policy(
            _oteo_result(),
            _market_context(tick_health="dead"),
            _regime(),
        )

        self.assertFalse(result["actionable"])
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn("dead market", result["level3_suppressed_reason"])

    def test_low_tick_health_penalty_and_divergence_boost_are_applied(self) -> None:
        result = apply_level3_policy(
            _oteo_result(),
            _market_context(tick_health="low", cci_divergence="bullish"),
            _regime(),
        )

        self.assertEqual(result["oteo_score"], 65.8)
        self.assertIsNone(result["level3_suppressed_reason"])
        self.assertTrue(result["actionable"])


class Level3Phase3AutoGhostTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.trade_service = _TradeServiceStub()
        self.service = AutoGhostService(
            self.trade_service,
            AutoGhostConfig(
                enabled=True,
                expiration_seconds=5,
                per_asset_cooldown_seconds=10,
                minimum_payout_pct=0.0,
                block_on_manipulation=False,
            ),
        )
        self.service.CONFIRMATION_TICKS = 3
        self.service.update_config(enabled=True, minimum_payout_pct=0.0)

        async def _instant_release(asset: str, delay_seconds: int) -> None:
            return None

        self.service._release_asset = _instant_release

    async def test_confirmation_window_delays_trade_until_third_tick(self) -> None:
        signal = _oteo_result()

        first = await self.service.consider_signal(
            asset="EURUSD_otc",
            price=1.0,
            timestamp=1.0,
            oteo_result=signal,
            manipulation={},
            payout_pct=90.0,
        )
        second = await self.service.consider_signal(
            asset="EURUSD_otc",
            price=1.0,
            timestamp=2.0,
            oteo_result=signal,
            manipulation={},
            payout_pct=90.0,
        )
        third = await self.service.consider_signal(
            asset="EURUSD_otc",
            price=1.0,
            timestamp=3.0,
            oteo_result=signal,
            manipulation={},
            payout_pct=90.0,
        )

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(len(self.trade_service.requests), 1)
        self.assertEqual(third["success"], True)

    async def test_confirmation_resets_on_direction_change(self) -> None:
        call_signal = _oteo_result(recommended="CALL")
        put_signal = _oteo_result(
            recommended="PUT",
            market_context={
                "adx_regime": "moderate",
                "cci_state": "overbought",
                "tick_health": "healthy",
                "cci_divergence": None,
            },
        )

        await self.service.consider_signal(
            asset="GBPUSD_otc",
            price=1.0,
            timestamp=1.0,
            oteo_result=call_signal,
            manipulation={},
            payout_pct=90.0,
        )
        await self.service.consider_signal(
            asset="GBPUSD_otc",
            price=1.0,
            timestamp=2.0,
            oteo_result=put_signal,
            manipulation={},
            payout_pct=90.0,
        )
        await self.service.consider_signal(
            asset="GBPUSD_otc",
            price=1.0,
            timestamp=3.0,
            oteo_result=put_signal,
            manipulation={},
            payout_pct=90.0,
        )
        fourth = await self.service.consider_signal(
            asset="GBPUSD_otc",
            price=1.0,
            timestamp=4.0,
            oteo_result=put_signal,
            manipulation={},
            payout_pct=90.0,
        )
        result = await self.service.consider_signal(
            asset="GBPUSD_otc",
            price=1.0,
            timestamp=5.0,
            oteo_result=put_signal,
            manipulation={},
            payout_pct=90.0,
        )

        self.assertIsNone(fourth)
        self.assertEqual(len(self.trade_service.requests), 1)
        self.assertEqual(result["success"], True)

    async def test_report_outcome_updates_cooldown_and_condition_stats(self) -> None:
        entry_context = {
            "regime_label": "RANGE_BOUND",
            "market_context": {
                "adx_regime": "moderate",
                "cci_state": "oversold",
                "tick_health": "low",
            },
        }

        self.service.report_outcome("ghost-1", "loss", -1.0, asset="EURUSD_otc", entry_context=entry_context)
        loss_one_started = self.service._last_streak_start_time
        first_cooldown = self.service._cooldown_until["EURUSD_otc"]
        self.assertEqual(self.service._consecutive_losses["EURUSD_otc"], 1)

        self.service.report_outcome("ghost-2", "loss", -1.0, asset="EURUSD_otc", entry_context=entry_context)
        self.service.report_outcome("ghost-3", "loss", -1.0, asset="EURUSD_otc", entry_context=entry_context)
        third_cooldown = self.service._cooldown_until["EURUSD_otc"]
        self.service.report_outcome("ghost-4", "win", 0.8, asset="EURUSD_otc", entry_context=entry_context)

        self.assertGreaterEqual(first_cooldown, loss_one_started + 19.0)
        self.assertGreater(third_cooldown, first_cooldown)
        self.assertNotIn("EURUSD_otc", self.service._consecutive_losses)

        stats = self.service.get_condition_stats()
        self.assertEqual(stats["regime:RANGE_BOUND"]["total"], 4)
        self.assertEqual(stats["asset:EURUSD_otc"]["wins"], 1)
        self.assertEqual(stats["tick_health:low"]["losses"], 3)


if __name__ == "__main__":
    unittest.main()
