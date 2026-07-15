import json
import tempfile
import unittest
from pathlib import Path

from scripts.backtest_hybrid_kalman_hurst import (
    Tick,
    TickSchemaError,
    KalmanFilter,
    HybridBacktestConfig,
    HybridBacktestRunner,
    evaluate_expiry,
    load_ticks_from_file,
)

class _FakeOTEO:
    def __init__(self) -> None:
        self.calls = 0
        self.signal_emitted = False

    def update_tick(self, price: float, timestamp: float):
        self.calls += 1
        if self.calls == 1 or self.signal_emitted:
            return 50.0
        self.signal_emitted = True
        return {
            "oteo_score": 76.0,
            "recommended": "CALL",
            "confidence": "HIGH",
            "velocity": -0.1,
            "pressure_pct": -80.0,
            "z_score": -2.0,
            "maturity": 1.0,
            "slow_velocity": -0.05,
            "trend_aligned": True,
            "actionable": True,
            "stretch_alignment": 1.2,
        }

class _FakeMarketContext:
    def update_tick(self, price: float, timestamp: float):
        return {
            "ready": True,
            "candle_closed": True,
            "candle_count": 20,
            "trend_direction": "up",
            "adx": 12.0,
            "adx_slope": -0.4,
            "plus_di": 12.0,
            "minus_di": 10.0,
            "cci": -120.0,
            "cci_state": "oversold",
            "atr": 0.0001,
            "nearest_structure_atr": 0.2,
            "micro_support": 1.0,
            "micro_resistance": 1.1,
            "support_alignment": True,
            "resistance_alignment": False,
            "adx_regime": "weak",
            "adx_falling": True,
            "reversal_friendly": True,
            "tick_health": "healthy",
            "cci_divergence": "bullish",
        }

class _FakeRegimeClassifier:
    def classify(self, market_context):
        return {
            "regime_label": "RANGE_BOUND",
            "regime_confidence": 80.0,
            "regime_detail": {},
            "regime_prior": None,
            "regime_stable": True,
            "regime_persistence": 3,
        }

class HybridBacktestUnitTests(unittest.TestCase):
    def test_kalman_filter_updates(self) -> None:
        kf = KalmanFilter(q=1e-9, r=1e-7)
        # First update initializes state
        x1 = kf.update(1.2345)
        self.assertEqual(x1, 1.2345)
        
        # Second update smooths
        x2 = kf.update(1.2355)
        self.assertNotEqual(x2, 1.2355)
        self.assertTrue(1.2345 < x2 < 1.2355)

    def test_load_ticks_validates_required_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "ticks.jsonl"
            path.write_text(json.dumps({"t": 1.0, "p": 1.2345}) + "\n", encoding="utf-8")

            with self.assertRaises(TickSchemaError) as error:
                load_ticks_from_file(path)

        self.assertIn("missing required field 'a'", str(error.exception))

    def test_evaluate_expiry_outcomes(self) -> None:
        ticks = [
            Tick(timestamp=0.0, price=1.0000, asset="EURUSD_otc"),
            Tick(timestamp=15.0, price=1.0010, asset="EURUSD_otc"),
            Tick(timestamp=30.0, price=0.9990, asset="EURUSD_otc"),
        ]
        timestamps = [t.timestamp for t in ticks]

        self.assertEqual(evaluate_expiry(ticks, timestamps, 0.0, 1.0000, "CALL", 15)["outcome"], "win")
        self.assertEqual(evaluate_expiry(ticks, timestamps, 0.0, 1.0000, "PUT", 15)["outcome"], "loss")
        self.assertEqual(evaluate_expiry(ticks, timestamps, 0.0, 1.0000, "CALL", 60)["outcome"], "missing_exit")

    def test_hybrid_runner_populates_comparison_rows(self) -> None:
        # Mock class patching inside the runner
        config = HybridBacktestConfig(expiry_seconds=[15], payout_pct=92.0)
        runner = HybridBacktestRunner(config)
        
        # Replace runner parts with mocks to avoid full calculations
        runner.oteo_base = _FakeOTEO()
        runner.oteo_kalman = _FakeOTEO()
        runner.oteo_hurst = _FakeOTEO()
        runner.oteo_hybrid = _FakeOTEO()
        
        runner.context_base = _FakeMarketContext()
        runner.context_kalman = _FakeMarketContext()
        runner.context_hurst = _FakeMarketContext()
        runner.context_hybrid = _FakeMarketContext()
        
        runner.regime_base = _FakeRegimeClassifier()
        runner.regime_kalman = _FakeRegimeClassifier()
        runner.regime_hurst = _FakeRegimeClassifier()
        runner.regime_hybrid = _FakeRegimeClassifier()

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "2026-06-19.jsonl"
            path.write_text(
                "\n".join([
                    json.dumps({"t": 0.0, "p": 1.0000, "a": "EURUSD_otc"}),
                    json.dumps({"t": 1.0, "p": 1.0000, "a": "EURUSD_otc"}),
                    json.dumps({"t": 16.0, "p": 1.0010, "a": "EURUSD_otc"}),
                ]) + "\n",
                encoding="utf-8",
            )

            rows = runner.run_file(path)
            
        self.assertTrue(len(rows) > 0)
        
        levels = {row["level"] for row in rows}
        self.assertIn("L1_BASELINE", levels)
        self.assertIn("L1_KALMAN", levels)
        self.assertIn("L1_HURST", levels)
        self.assertIn("L1_HYBRID", levels)

if __name__ == "__main__":
    unittest.main()
