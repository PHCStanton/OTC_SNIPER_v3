import unittest
import tempfile
import json
import pandas as pd
from pathlib import Path
from backtester_app.core.engine import UnifiedBacktester, UnifiedBacktestConfig, UnifiedHurstTracker

class TestBacktesterEngine(unittest.TestCase):
    def test_hurst_tracker_initialization(self):
        config = UnifiedBacktestConfig()
        config.hurst.window_size = 300
        config.hurst.mean_revert_limit = 0.44
        config.hurst.trend_limit = 0.58

        tracker = UnifiedHurstTracker(
            window_size=config.hurst.window_size,
            mean_revert_limit=config.hurst.mean_revert_limit,
            trend_limit=config.hurst.trend_limit
        )
        self.assertEqual(tracker.mean_revert_limit, 0.44)
        self.assertEqual(tracker.trend_limit, 0.58)
        self.assertEqual(tracker.prices.maxlen, 300)

    def test_config_to_from_dict_symmetry(self):
        config = UnifiedBacktestConfig()
        config.hurst.veto_enabled = True
        config.kalman.enabled = True
        config.manipulation.veto_enabled = True
        config.manipulation.severity_threshold = 0.5
        
        cfg_dict = config.to_dict()
        self.assertTrue(cfg_dict["hurst"]["veto_enabled"])
        self.assertTrue(cfg_dict["kalman"]["enabled"])
        self.assertTrue(cfg_dict["manipulation"]["veto_enabled"])
        self.assertEqual(cfg_dict["manipulation"]["severity_threshold"], 0.5)

        restored = UnifiedBacktestConfig.from_dict(cfg_dict)
        self.assertEqual(restored.hurst.veto_enabled, True)
        self.assertEqual(restored.kalman.enabled, True)
        self.assertEqual(restored.manipulation.veto_enabled, True)
        self.assertEqual(restored.manipulation.severity_threshold, 0.5)

    def test_backtester_mock_run(self):
        config = UnifiedBacktestConfig()
        config.hurst.veto_enabled = True
        config.ou.veto_enabled = True
        config.bayesian.enabled = True
        config.manipulation.veto_enabled = True
        
        tester = UnifiedBacktester(config)
        
        # Create a mock daily tick log
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / "2026-06-30.jsonl"
            ticks = [
                {"t": 1771496580.0, "p": 1.2345, "a": "CADJPY_otc"},
                {"t": 1771496581.0, "p": 1.2346, "a": "CADJPY_otc"},
                {"t": 1771496582.0, "p": 1.2347, "a": "CADJPY_otc"},
                {"t": 1771496583.0, "p": 1.2344, "a": "CADJPY_otc"},
                {"t": 1771496645.0, "p": 1.2345, "a": "CADJPY_otc"}
            ]
            with open(temp_path, "w", encoding="utf-8") as f:
                for tk in ticks:
                    f.write(json.dumps(tk) + "\n")
            
            # Run the file
            rows = tester.run_file(temp_path)
            # Since mock data doesn't generate OTEO signals, rows should be empty but run_file shouldn't crash
            self.assertEqual(len(rows), 0)

    def test_optimizer_mock_run(self):
        from backtester_app.core.optimizer import run_optuna_study
        with tempfile.TemporaryDirectory() as tmp_dir:
            import backtester_app.core.optimizer as opt_module
            old_tick_root = opt_module.TICK_ROOT
            opt_module.TICK_ROOT = Path(tmp_dir)
            try:
                asset_dir = Path(tmp_dir) / "EURUSD_otc"
                asset_dir.mkdir(parents=True, exist_ok=True)
                temp_path = asset_dir / "2026-06-30.jsonl"
                ticks = [
                    {"t": 1771496580.0, "p": 1.2345, "a": "EURUSD_otc"},
                    {"t": 1771496581.0, "p": 1.2346, "a": "EURUSD_otc"}
                ]
                with open(temp_path, "w", encoding="utf-8") as f:
                    for tk in ticks:
                        f.write(json.dumps(tk) + "\n")
                
                results = run_optuna_study(
                    dates=["2026-06-30"],
                    asset="EURUSD_otc",
                    n_trials=2,
                    target_metric="pnl",
                    min_trades=0,
                    payout_pct=92.0
                )
                self.assertIn("best_value", results)
                self.assertIn("best_params", results)
                self.assertEqual(results["total_trials"], 2)
            finally:
                opt_module.TICK_ROOT = old_tick_root

    def test_hurst_regime_whitelist(self):
        config = UnifiedBacktestConfig()
        config.hurst.veto_enabled = True
        config.hurst.allowed_regimes = ["mean_reverting"]
        
        from backtester_app.core.engine import GateContext, HurstFilterGate
        gate = HurstFilterGate(config.hurst)
        
        ctx_mr = GateContext(0, 1.0, "CALL", 0.35, "mean_reverting", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0)
        ctx_rw = GateContext(0, 1.0, "CALL", 0.50, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0)
        
        vetoed_mr, reason_mr = gate.evaluate(ctx_mr)
        vetoed_rw, reason_rw = gate.evaluate(ctx_rw)
        
        self.assertFalse(vetoed_mr)
        self.assertTrue(vetoed_rw)
        self.assertEqual(reason_rw, "hurst_veto_random_walk")

    def test_oteo_gate_bounds(self):
        from backtester_app.core.engine import GateContext, OTEOSignalGate, OTEOGateConfig
        cfg = OTEOGateConfig(
            min_score_enabled=True, min_score=60.0,
            min_zscore_enabled=True, min_zscore=1.0
        )
        gate = OTEOSignalGate(cfg)
        
        ctx_bad = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, oteo_score=50.0, z_score=0.5)
        ctx_good = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, oteo_score=75.0, z_score=2.1)
        
        vetoed_bad, _ = gate.evaluate(ctx_bad)
        vetoed_good, _ = gate.evaluate(ctx_good)
        
        self.assertTrue(vetoed_bad)
        self.assertFalse(vetoed_good)

    def test_config_bridge_roundtrip(self):
        from backtester_app.core.config_bridge import backtester_to_ghost_protocol, ghost_protocol_to_backtester
        config = UnifiedBacktestConfig()
        config.payout_pct = 85.0
        config.hurst.veto_enabled = True
        config.hurst.filter_threshold = 0.52
        config.oteo_gate.min_zscore_enabled = True
        config.oteo_gate.min_zscore = 1.5
        config.pocket.blacklist_assets = ["EURUSD", "GBPUSD"]
        
        ghost_json = backtester_to_ghost_protocol(config)
        reconstructed_dict = ghost_protocol_to_backtester(ghost_json)
        reconstructed = UnifiedBacktestConfig.from_dict(reconstructed_dict)
        
        self.assertEqual(reconstructed.payout_pct, 85.0)
        self.assertTrue(reconstructed.hurst.veto_enabled)
        self.assertEqual(reconstructed.hurst.filter_threshold, 0.52)
        self.assertTrue(reconstructed.oteo_gate.min_zscore_enabled)
        self.assertEqual(reconstructed.oteo_gate.min_zscore, 1.5)
        self.assertEqual(reconstructed.pocket.blacklist_assets, ["EURUSD", "GBPUSD"])

    def test_volatility_liquidity_thresholds(self):
        from backtester_app.core.engine import PocketTracker, VolatilityConfig, LiquidityConfig
        tracker = PocketTracker()
        
        vol_cfg = VolatilityConfig(high_ratio=1.5, medium_ratio=1.1)
        liq_cfg = LiquidityConfig(high_freq=30.0, medium_freq=10.0)
        
        vol_lvl, liq_lvl, manip_lvl, state = tracker.update(1771496580.0, 1.0, vol_cfg, liq_cfg)
        self.assertEqual(vol_lvl, "LOW")
        self.assertEqual(liq_lvl, "LOW")

    def test_manipulation_severity_float(self):
        from backtester_app.core.engine import GateContext, ManipulationFilterGate, ManipulationConfig
        cfg = ManipulationConfig(veto_enabled=True, severity_threshold=0.4)
        gate = ManipulationFilterGate(cfg)
        
        ctx_low = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, manip_push_snap=0.2, manip_pinning=0.1)
        ctx_high = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, manip_push_snap=0.5, manip_pinning=0.1)
        
        vetoed_low, _ = gate.evaluate(ctx_low)
        vetoed_high, _ = gate.evaluate(ctx_high)
        
        self.assertFalse(vetoed_low)
        self.assertTrue(vetoed_high)

    def test_oteo_config_passthrough(self):
        from backtester_app.core.engine import UnifiedBacktester, UnifiedBacktestConfig
        config = UnifiedBacktestConfig()
        config.oteo_params.score_slope = 5.0
        config.oteo_params.score_center = 0.95
        
        tester = UnifiedBacktester(config)
        self.assertEqual(tester.oteo.config.score_slope, 5.0)
        self.assertEqual(tester.oteo.config.score_center, 0.95)

    def test_rsi_cci_indicators(self):
        from app.backend.services.indicators import compute_rsi, compute_cci, compute_slope
        closes = [10.0, 10.5, 11.0, 10.8, 10.6, 11.2, 11.5, 12.0]
        rsi = compute_rsi(closes, period=5)
        self.assertIsNotNone(rsi)
        self.assertTrue(0.0 <= rsi <= 100.0)

        highs = [10.2, 10.7, 11.1, 10.9, 10.8, 11.4, 11.7, 12.1]
        lows = [9.8, 10.3, 10.8, 10.6, 10.5, 11.0, 11.3, 11.8]
        cci = compute_cci(highs, lows, closes, period=5)
        self.assertIsNotNone(cci)

        slope = compute_slope([1.0, 2.0, 3.5])
        self.assertGreater(slope, 0.0)

    def test_candle_builder(self):
        from app.backend.services.candle_builder import CandleBuilder
        builder = CandleBuilder(period_seconds=10, max_candles=5)
        # Feed ticks across multiple periods
        builder.update(100.0, 1000.0)
        builder.update(101.0, 1002.0)
        
        # This tick is in the next period (1010)
        closed = builder.update(102.0, 1011.0)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.open, 100.0)
        self.assertEqual(closed.high, 101.0)
        self.assertEqual(closed.low, 100.0)
        self.assertEqual(closed.close, 101.0)
        self.assertEqual(closed.tick_count, 2)

    def test_rsi_cci_gate_evaluation(self):
        from backtester_app.core.engine import GateContext, RSICCIConfluenceGate, RSICCIConfluenceConfig
        cfg = RSICCIConfluenceConfig(
            enabled=True,
            rsi_overbought=70.0,
            rsi_oversold=30.0,
            min_slope_magnitude=0.1
        )
        gate = RSICCIConfluenceGate(cfg)

        # 1. RSI not in extreme zone
        ctx_not_extreme = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, rsi_value=45.0, rsi_slope=0.5, cci9_value=50.0, cci9_slope=0.5)
        vetoed, reason = gate.evaluate(ctx_not_extreme)
        self.assertTrue(vetoed)
        self.assertIn("rsi_not_oversold", reason)

        # 2. Slopes not parallel
        ctx_not_parallel = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, rsi_value=25.0, rsi_slope=0.5, cci9_value=-50.0, cci9_slope=-0.5)
        vetoed, reason = gate.evaluate(ctx_not_parallel)
        self.assertTrue(vetoed)
        self.assertEqual(reason, "rsi_cci_veto_not_parallel")

        # 3. Wrong slope direction for trade type
        ctx_wrong_dir = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, rsi_value=25.0, rsi_slope=-0.5, cci9_value=-50.0, cci9_slope=-0.5)
        vetoed, reason = gate.evaluate(ctx_wrong_dir)
        self.assertTrue(vetoed)
        self.assertEqual(reason, "rsi_cci_veto_wrong_direction")

        # 4. Good confluence trade
        ctx_good = GateContext(0, 1.0, "CALL", 0.5, "random_walk", None, None, "", "LOW", "LOW", "LOW", 0, 0, 0.0, 92.0, rsi_value=25.0, rsi_slope=0.5, cci9_value=-150.0, cci9_slope=2.0)
        vetoed, reason = gate.evaluate(ctx_good)
        self.assertFalse(vetoed)

    def test_config_bridge_roundtrip_rsi_cci(self):
        from backtester_app.core.config_bridge import backtester_to_ghost_protocol, ghost_protocol_to_backtester
        config = UnifiedBacktestConfig()
        config.rsi_cci.enabled = True
        config.rsi_cci.rsi_period = 8
        config.rsi_cci.cci_period = 10
        config.rsi_cci.candle_seconds = 15
        config.rsi_cci.rsi_overbought = 75.0
        config.rsi_cci.rsi_oversold = 25.0
        config.rsi_cci.min_slope_magnitude = 0.2
        
        ghost_json = backtester_to_ghost_protocol(config)
        reconstructed_dict = ghost_protocol_to_backtester(ghost_json)
        reconstructed = UnifiedBacktestConfig.from_dict(reconstructed_dict)
        
        self.assertTrue(reconstructed.rsi_cci.enabled)
        self.assertEqual(reconstructed.rsi_cci.rsi_period, 8)
        self.assertEqual(reconstructed.rsi_cci.cci_period, 10)
        self.assertEqual(reconstructed.rsi_cci.candle_seconds, 15)
        self.assertEqual(reconstructed.rsi_cci.rsi_overbought, 75.0)
        self.assertEqual(reconstructed.rsi_cci.rsi_oversold, 25.0)
        self.assertEqual(reconstructed.rsi_cci.min_slope_magnitude, 0.2)

if __name__ == "__main__":
    unittest.main()
