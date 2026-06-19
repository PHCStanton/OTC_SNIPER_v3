import unittest
import numpy as np
import asyncio
from unittest.mock import AsyncMock

from app.backend.services.manipulation import ManipulationDetector
from app.backend.services.auto_ghost import AutoGhostService, AutoGhostConfig
from app.backend.services.streaming import StreamingService
from app.backend.brokers.base import BrokerType
from app.backend.models.requests import TradeExecutionRequest


class TestManipulationSeverity(unittest.TestCase):
    def test_mean_absolute_velocity_spikes(self):
        detector = ManipulationDetector()

        # Generate a baseline of alternating small ticks (mean signed velocity will cancel out, but MAV will be ~1.0)
        timestamp = 1000.0
        prices = [10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 10.0, 11.0, 10.0, 11.0]
        
        for price in prices:
            detector.update(timestamp, price)
            timestamp += 1.0  # dt = 1.0

        # MAV should be around 1.0. The threshold for spike should be 3 * 1.0 = 3.0.
        # Now trigger a small tick velocity (+1.5, which is > 3 * signed_avg but < 3 * MAV)
        # Signed avg velocity is 0.1, so 3 * signed_avg = 0.3.
        # If we used signed average velocity, 1.5 would trigger a false spike.
        # With MAV, the threshold is 3.0, so a velocity of 1.5 should NOT trigger a spike.
        res = detector.update(timestamp, 12.5)  # vel = 1.5 over 1s -> 1.5
        self.assertNotIn("push_snap", res)

        # Now trigger a massive spike of +5.0 (which is > 3 * MAV = 3.0)
        # This should trigger push_snap.
        res_spike = detector.update(timestamp + 1.0, 17.5)  # vel = 5.0
        self.assertIn("push_snap", res_spike)
        self.assertGreater(res_spike["push_snap"], 0.0)

    def test_exponential_decay(self):
        detector = ManipulationDetector()
        
        # Populate some ticks with tiny velocity
        timestamp = 1000.0
        for i in range(10):
            detector.update(timestamp, 10.0 + (i % 2) * 0.1)
            timestamp += 1.0
        
        # Trigger spike
        res = detector.update(timestamp, 20.0)  # Huge velocity spike
        self.assertIn("push_snap", res)
        initial_severity = res["push_snap"]
        self.assertGreaterEqual(initial_severity, 0.3)

        # Evaluate decay after 5.0 seconds (should be exactly initial * e^-1 ~ initial * 0.368)
        res_decay_5s = detector.update(timestamp + 5.0, 20.0)
        self.assertIn("push_snap", res_decay_5s)
        self.assertAlmostEqual(res_decay_5s["push_snap"], round(initial_severity * np.exp(-1.0), 3), places=3)

        # Evaluate decay after 25.0 seconds (should decay to 0.0, so the key is removed)
        res_decay_25s = detector.update(timestamp + 25.0, 20.0)
        self.assertNotIn("push_snap", res_decay_25s)

    def test_pinning_severity(self):
        detector = ManipulationDetector()

        # Seed 20 flat ticks
        avg_price = 1.0
        for i in range(20):
            detector.update(1000.0 + i, avg_price)

        # Flat prices (range = 0) -> severity should be 1.0 (maximal pinning)
        res_flat = detector.update(1020.0, avg_price)
        self.assertIn("pinning", res_flat)
        self.assertEqual(res_flat["pinning"], 1.0)

        # Add price movement to raise price range to exactly half of threshold
        # threshold = avg_price * 0.00005 = 0.00005
        # Set range to 0.000025 -> severity should be 1.0 - (0.5) = 0.5
        # Since last 20 ticks are used, append prices with a tiny variance
        detector.price_history.clear()
        for i in range(19):
            detector.price_history.append(1.0)
        detector.price_history.append(1.000025)

        res_half = detector.update(1021.0, 1.0)
        self.assertIn("pinning", res_half)
        self.assertAlmostEqual(res_half["pinning"], 0.5, places=2)


class MockTradeService:
    def __init__(self):
        self.trades = []

    async def execute_trade(self, broker, request):
        self.trades.append(request)
        return {"success": True, "message": "executed"}


class TestAutoGhostSeverityGating(unittest.IsolatedAsyncioTestCase):
    async def test_auto_ghost_severity_thresholds(self):
        trade_service = MockTradeService()
        
        # Configure AutoGhost with a severity threshold of 0.5
        config = AutoGhostConfig(
            enabled=True,
            amount=1.0,
            expiration_seconds=10,
            block_on_manipulation=True,
            manipulation_severity_threshold=0.5
        )
        service = AutoGhostService(trade_service, config)
        service.CONFIRMATION_TICKS = 3
        service._session_id = "test_session"

        oteo_result = {
            "recommended": "CALL",
            "actionable": True,
            "confidence": "HIGH",
            "oteo_score": 85.0
        }

        # Signal 1: manipulation active but severity is 0.3 (below threshold of 0.5)
        # Should NOT block the trade
        res1 = await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1000.0,
            oteo_result=oteo_result,
            manipulation={"push_snap": 0.3},
            payout_pct=90.0
        )
        # Confirmation ticks requires 3 matching ticks to execute.
        # Tick 1: returns None (stored pending)
        self.assertIsNone(res1)
        self.assertEqual(len(trade_service.trades), 0)

        # Tick 2: matching, returns None
        await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1001.0,
            oteo_result=oteo_result,
            manipulation={"push_snap": 0.3},
            payout_pct=90.0
        )

        # Tick 3: matches, should execute the trade
        res_exec = await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1002.0,
            oteo_result=oteo_result,
            manipulation={"push_snap": 0.3},
            payout_pct=90.0
        )
        self.assertIsNotNone(res_exec)
        self.assertEqual(len(trade_service.trades), 1)

        # Clear trades and active assets for next test
        trade_service.trades.clear()
        service._active_assets.clear()
        service._pending_signals.clear()

        # Signal 2: manipulation active with severity 0.6 (above threshold of 0.5)
        # Should reject the trade immediately (returns None)
        res_blocked = await service.consider_signal(
            asset="GBPUSD",
            price=1.2,
            timestamp=1003.0,
            oteo_result=oteo_result,
            manipulation={"push_snap": 0.6},
            payout_pct=90.0
        )
        self.assertIsNone(res_blocked)
        self.assertEqual(len(trade_service.trades), 0)

    async def test_auto_ghost_confidence_bounds(self):
        trade_service = MockTradeService()
        
        # Configure with min confidence 80% and max confidence 95%
        config = AutoGhostConfig(
            enabled=True,
            amount=1.0,
            expiration_seconds=10,
            block_on_manipulation=False,
            min_confidence_enabled=True,
            min_confidence=80.0,
            max_confidence_enabled=True,
            max_confidence=95.0
        )
        service = AutoGhostService(trade_service, config)
        service.CONFIRMATION_TICKS = 3
        service._session_id = "test_session"

        # oteo_score = 75.0 (below min of 80) -> should be rejected
        oteo_result_low = {
            "recommended": "CALL",
            "actionable": True,
            "confidence": "HIGH",
            "oteo_score": 75.0
        }
        res_low = await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1000.0,
            oteo_result=oteo_result_low,
            manipulation={},
            payout_pct=90.0
        )
        self.assertIsNone(res_low)

        # oteo_score = 98.0 (above max of 95) -> should be rejected
        oteo_result_high = {
            "recommended": "CALL",
            "actionable": True,
            "confidence": "HIGH",
            "oteo_score": 98.0
        }
        res_high = await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1001.0,
            oteo_result=oteo_result_high,
            manipulation={},
            payout_pct=90.0
        )
        self.assertIsNone(res_high)

        # oteo_score = 88.0 (within 80 to 95) -> should match confirm ticks
        oteo_result_mid = {
            "recommended": "CALL",
            "actionable": True,
            "confidence": "HIGH",
            "oteo_score": 88.0
        }
        
        # Tick 1
        res1 = await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1002.0,
            oteo_result=oteo_result_mid,
            manipulation={},
            payout_pct=90.0
        )
        self.assertIsNone(res1)
        
        # Tick 2
        await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1003.0,
            oteo_result=oteo_result_mid,
            manipulation={},
            payout_pct=90.0
        )
        
        # Tick 3 -> execute
        res_exec = await service.consider_signal(
            asset="EURUSD",
            price=1.1,
            timestamp=1004.0,
            oteo_result=oteo_result_mid,
            manipulation={},
            payout_pct=90.0
        )
        self.assertIsNotNone(res_exec)
        self.assertEqual(len(trade_service.trades), 1)


if __name__ == "__main__":
    unittest.main()
