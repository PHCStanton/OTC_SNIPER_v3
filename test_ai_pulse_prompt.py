"""
AI Pulse Prompt Contract Tests (Phase 0 — Auto-Ghost Calibration Mode Plan 26-08-26).

Verifies the Phase 0 prompt-enrichment quick wins in `streaming.py`:

- P0-1  Payout surfacing (percent units, UNAVAILABLE fallback) in asset
        summaries, trade lines, and the Minimum Payout Gate context line (C2).
- P0-2  Bayesian WP60/WP300 merged from the C2 remediation cache.
- P0-3  HTF trend verdict + tick-flow ratios (computed on demand — no cache).
- P0-4  Volatility/Liquidity readings from the market-context cache.
- P0-5  Trajectory attribution distribution section.
- P0-6  Fabricated `confidence: 85` removed at all THREE sites (both regex
        fallback outputs AND the system-prompt JSON example).
- P0-7  Rolling last-20 WR + explicit sample-size rule.
- P0-8  `bayesian_min_probability` spec-table clamp (0.50, 0.90).
"""

from __future__ import annotations

import time
import unittest
from collections import deque

from app.backend.services.auto_ghost import AutoGhostConfig
from app.backend.services.streaming import (
    StreamingService,
    _build_ai_pulse_system_msg,
    _build_pulse_asset_summary,
    _build_pulse_user_msg,
    _extract_pulse_signal_from_text,
)


def _make_streaming_service() -> StreamingService:
    """Lightweight instance bypassing heavy constructor dependencies."""
    service = object.__new__(StreamingService)
    service._market_context_engines = {}
    service._last_manip_flags = {}
    service._last_regime = {}
    service._recent_ticks = {}
    service._latest_bayesian_wp = {}
    service._payout_cache = {}
    service._payout_fail_counts = {}
    return service


class TestSystemPromptContract(unittest.TestCase):
    """P0-6 (M7): no fabricated confidence anywhere in the system prompt."""

    def test_no_fabricated_confidence_in_prompt_example(self) -> None:
        msg = _build_ai_pulse_system_msg()
        self.assertNotIn('"confidence": 85', msg)
        # The confidence key must not appear as an instructed JSON field.
        self.assertNotIn('"confidence"', msg)

    def test_min_payout_pct_suggestion_in_percent_units(self) -> None:
        msg = _build_ai_pulse_system_msg()
        self.assertIn("min_payout_pct", msg)
        # C2 unit contract: percent form, never a 0-1 fraction example.
        self.assertIn('"min_payout_pct": 87.0', msg)
        self.assertIn("PERCENT", msg)

    def test_payout_gate_instruction_present(self) -> None:
        msg = _build_ai_pulse_system_msg()
        self.assertIn("below the Minimum Payout Gate", msg)


class TestAssetSummaryContract(unittest.TestCase):
    """P0-1/P0-2/P0-3/P0-4: enriched per-asset summary sections."""

    def test_payout_rendered_in_percent(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10,
            {"adx": 22.0, "cci": -40.0, "cci_state": "neutral"},
            payout_pct=85.0, bayesian_wp=None, htf_summary=None,
        )
        self.assertIn("Payout=85.0%", line)
        # Literal 0.85-form must NEVER appear (C2 unit contract).
        self.assertNotIn("Payout=0.85", line)

    def test_payout_unavailable_marker(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10, {},
            payout_pct=None, bayesian_wp=None, htf_summary=None,
        )
        self.assertIn("Payout=UNAVAILABLE", line)

    def test_bayesian_wp_section(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10, {},
            payout_pct=85.0,
            bayesian_wp={
                "bayesian_win_probability_60s": 0.551,
                "bayesian_win_probability_300s": 0.522,
            },
            htf_summary=None,
        )
        self.assertIn("WP60=0.551", line)
        self.assertIn("WP300=0.522", line)

    def test_bayesian_wp_unavailable_when_cache_empty(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10, {},
            payout_pct=85.0, bayesian_wp=None, htf_summary=None,
        )
        self.assertIn("WP60=UNAVAILABLE", line)
        self.assertIn("WP300=UNAVAILABLE", line)

    def test_htf_verdict_and_tick_flow(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10, {},
            payout_pct=85.0, bayesian_wp=None,
            htf_summary={
                "htf_trend": "BULLISH", "trend_5m": "BULLISH",
                "trend_15m": "NEUTRAL", "tick_flow_60s": 61.5,
                "tick_flow_300s": 55.0,
            },
        )
        self.assertIn("HTF=BULLISH", line)
        self.assertIn("TickFlow60=61.5%", line)
        self.assertIn("TickFlow300=55.0%", line)

    def test_htf_unavailable_marker(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10, {},
            payout_pct=85.0, bayesian_wp=None, htf_summary=None,
        )
        self.assertIn("HTF=UNAVAILABLE", line)

    def test_volatility_liquidity_readings(self) -> None:
        line = _build_pulse_asset_summary(
            "EURUSD_otc", 1.0850, "RANGE_BOUND", 0.10,
            {"volatility_score": 72.4, "liquidity_score": 33.1},
            payout_pct=85.0, bayesian_wp=None, htf_summary=None,
        )
        self.assertIn("Volatility=72.4", line)
        self.assertIn("Liquidity=33.1", line)


class TestUserMessageContract(unittest.TestCase):
    """P0-1/P0-5/P0-7: user message sections for a seeded harness."""

    def _build_user_msg(self, trajectory_analytics: dict | None = None) -> str:
        config = AutoGhostConfig()
        rolling_stats = {"window": 20, "wins": 11, "losses": 9, "win_rate": 55.0}
        return _build_pulse_user_msg(
            config=config,
            summaries_str="- EURUSD_otc: Price=1.0850 (stubbed)",
            recent_trades_str="- Trade 1: (stubbed)",
            is_insufficient=False,
            session_trade_count=42,
            session_wins=23,
            session_losses=19,
            session_pnl=12.5,
            rolling_stats=rolling_stats,
            trajectory_analytics=trajectory_analytics or {},
            lookback_seconds=120,
        )

    def test_minimum_payout_gate_context_line_in_percent(self) -> None:
        msg = self._build_user_msg()
        # AutoGhostConfig default is 88.0 percent.
        self.assertIn(f"Minimum Payout Gate: {AutoGhostConfig().minimum_payout_pct:.1f}%", msg)
        self.assertIn("percent units", msg)
        self.assertNotIn("Minimum Payout Gate: 0.88", msg)

    def test_bayesian_floor_and_vol_liq_bands_present(self) -> None:
        msg = self._build_user_msg()
        self.assertIn("Bayesian Filter Enabled", msg)
        self.assertIn("Min Win Probability Floor", msg)
        self.assertIn("Volatility Gate:", msg)
        self.assertIn("Liquidity Gate:", msg)

    def test_rolling_window_section_and_sample_size_rule(self) -> None:
        msg = self._build_user_msg()
        self.assertIn("Rolling Last-20-Trade Win Rate: 55.0%", msg)
        self.assertIn("wins=11, losses=9", msg)
        self.assertIn("Sample-size rule", msg)
        self.assertIn("N>=20", msg)

    def test_trajectory_section_unavailable_when_empty(self) -> None:
        msg = self._build_user_msg(trajectory_analytics={})
        self.assertIn("Pulse Trajectory Attributions: UNAVAILABLE", msg)

    def test_trajectory_section_with_analytics(self) -> None:
        analytics = {
            "total_trades": 30,
            "clean_wins": 12,
            "premature_expirations": 7,
            "momentum_exhaustions": 4,
            "structural_traps": 3,
            "directional_fails": 4,
            "win_rate": 46.7,
        }
        msg = self._build_user_msg(trajectory_analytics=analytics)
        self.assertIn("Pulse Trajectory Attributions (last 30 settled AI Pulse trades)", msg)
        self.assertIn("CLEAN_WIN=12", msg)
        self.assertIn("PREMATURE_EXPIRATION=7", msg)
        self.assertIn("MOMENTUM_EXHAUSTION=4", msg)
        self.assertIn("STRUCTURAL_TRAP=3", msg)
        self.assertIn("DIRECTIONAL_FAIL=4", msg)

    def test_data_sufficiency_flag(self) -> None:
        msg = self._build_user_msg()
        self.assertIn("Data Sufficiency Flag: SUFFICIENT", msg)


class TestRegexFallbackContract(unittest.TestCase):
    """P0-6 (M7): regex fallback must not fabricate confidence."""

    def test_call_extraction_confidence_is_none(self) -> None:
        signal = _extract_pulse_signal_from_text(
            "🔥 FOCUS:\n🟢 CALL: EURUSD_otc | Target: 1.0850 | Wait: 2m",
            ["EURUSD_otc"],
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal["asset"], "EURUSD_otc")
        self.assertEqual(signal["direction"], "CALL")
        self.assertEqual(signal["target_price"], 1.0850)
        self.assertEqual(signal["wait_minutes"], 2)
        self.assertIsNone(signal["confidence"])
        self.assertNotEqual(signal.get("confidence"), 85)

    def test_put_extraction_confidence_is_none(self) -> None:
        signal = _extract_pulse_signal_from_text(
            "⚠️ AVOID:\n🔴 PUT: AUDNZD_otc | Target: 1.0900 | Wait: 1m",
            ["AUDNZD_otc"],
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal["asset"], "AUDNZD_otc")
        self.assertEqual(signal["direction"], "PUT")
        self.assertIsNone(signal["confidence"])

    def test_no_signal_text_returns_none(self) -> None:
        self.assertIsNone(
            _extract_pulse_signal_from_text("No actionable setups right now.", ["EURUSD_otc"])
        )


class TestHTFSummaryComputation(unittest.TestCase):
    """P0-3 (M5): on-demand HTF summary uses live candle/tick buffers."""

    def test_summary_from_live_buffers(self) -> None:
        service = _make_streaming_service()
        now = time.time()
        # 12 rising 1-minute candles (dict form accepted by resample_1m_candles).
        candles = [
            {
                "start_ts": int(now) - i * 60,
                "open": 1.1000 + (12 - i) * 0.0001,
                "high": 1.1000 + (12 - i) * 0.0001 + 0.0002,
                "low": 1.1000 + (12 - i) * 0.0001 - 0.0002,
                "close": 1.1000 + (12 - i) * 0.0001 + 0.0001,
            }
            for i in range(12)
        ]
        mc_stub = type("MCStub", (), {"_closed_candles": candles})()
        service._market_context_engines["EURUSD_otc"] = mc_stub
        service._recent_ticks["EURUSD_otc"] = deque(
            [{"t": now - i, "p": 1.1000 + i * 0.00001} for i in range(50)],
            maxlen=600,
        )

        summary = service._compute_pulse_htf_summary("EURUSD_otc")
        self.assertIsNotNone(summary)
        self.assertIn(summary["htf_trend"], {"BULLISH", "BEARISH", "NEUTRAL"})
        self.assertIsInstance(summary["tick_flow_60s"], float)
        self.assertIsInstance(summary["tick_flow_300s"], float)

    def test_missing_engine_returns_none(self) -> None:
        service = _make_streaming_service()
        self.assertIsNone(service._compute_pulse_htf_summary("UNKNOWN_otc"))


class TestBayesianSpecClamp(unittest.TestCase):
    """P0-8 (M6/EX-21): direct update_config path is bounded (0.50, 0.90)."""

    @staticmethod
    def _make_service():
        from app.backend.services.auto_ghost import AutoGhostService

        class _StubTradeService:
            def _get_market_context(self, asset: str) -> dict:
                return {}

            def _latest_logged_price(self, asset: str):
                return None

        return AutoGhostService(_StubTradeService(), config=AutoGhostConfig())

    def test_percent_form_value_is_clamped(self) -> None:
        service = self._make_service()
        service.update_config(bayesian_min_probability=53.5)
        self.assertEqual(service.config.bayesian_min_probability, 0.90)

    def test_below_floor_is_clamped(self) -> None:
        service = self._make_service()
        service.update_config(bayesian_min_probability=0.10)
        self.assertEqual(service.config.bayesian_min_probability, 0.50)

    def test_valid_value_passes_through(self) -> None:
        service = self._make_service()
        service.update_config(bayesian_min_probability=0.535)
        self.assertEqual(service.config.bayesian_min_probability, 0.535)


if __name__ == "__main__":
    unittest.main()


