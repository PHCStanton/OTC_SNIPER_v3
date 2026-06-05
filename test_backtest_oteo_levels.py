import json
import tempfile
import unittest
from pathlib import Path

from scripts.backtest_oteo_levels import (
    EXCLUSION_WIN_RATE_THRESHOLD,
    MIN_SAMPLE_SIZE,
    BacktestConfig,
    BacktestRunner,
    GhostTradeSchemaError,
    TickSchemaError,
    _breakeven_win_rate,
    _matrix_table,
    _recommendations,
    _suppression_audit,
    evaluate_expiry,
    generate_markdown_report,
    load_ghost_trades_from_file,
    load_ticks_from_file,
    reprice_ghost_trades,
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


def _fake_stack_factory():
    return _FakeOTEO(), _FakeMarketContext(), _FakeRegimeClassifier()


class BacktestTickLoadingTests(unittest.TestCase):
    def test_load_ticks_validates_required_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "ticks.jsonl"
            path.write_text(json.dumps({"t": 1.0, "p": 1.2345}) + "\n", encoding="utf-8")

            with self.assertRaises(TickSchemaError) as error:
                load_ticks_from_file(path)

        self.assertIn("missing required field 'a'", str(error.exception))

    def test_load_ticks_sorts_by_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "ticks.jsonl"
            path.write_text(
                "\n".join([
                    json.dumps({"t": 3.0, "p": 1.3, "a": "EURUSD_otc"}),
                    json.dumps({"t": 1.0, "p": 1.1, "a": "EURUSD_otc"}),
                ]) + "\n",
                encoding="utf-8",
            )

            ticks = load_ticks_from_file(path)

        self.assertEqual([tick.timestamp for tick in ticks], [1.0, 3.0])


class BacktestExpiryEvaluationTests(unittest.TestCase):
    def test_call_put_and_missing_exit_outcomes_are_explicit(self) -> None:
        ticks = [
            {"t": 0.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 15.0, "p": 1.0010, "a": "EURUSD_otc"},
            {"t": 30.0, "p": 0.9990, "a": "EURUSD_otc"},
        ]

        self.assertEqual(evaluate_expiry(ticks, 0.0, 1.0000, "CALL", 15)["outcome"], "win")
        self.assertEqual(evaluate_expiry(ticks, 0.0, 1.0000, "PUT", 15)["outcome"], "loss")
        self.assertEqual(evaluate_expiry(ticks, 0.0, 1.0000, "CALL", 60)["outcome"], "missing_exit")


class BacktestReplayTests(unittest.TestCase):
    def test_replay_keeps_level_rows_separate_for_each_expiry(self) -> None:
        runner = BacktestRunner(
            BacktestConfig(expiry_seconds=[15, 30], payout_pct=92.0),
            stack_factory=_fake_stack_factory,
        )
        ticks = [
            {"t": 0.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 1.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 16.0, "p": 1.0010, "a": "EURUSD_otc"},
            {"t": 31.0, "p": 1.0020, "a": "EURUSD_otc"},
        ]

        rows = runner.replay_asset_ticks("EURUSD_otc", ticks, date="2026-05-15")

        levels = {row["level"] for row in rows}
        expiries = {row["expiry_seconds"] for row in rows}
        self.assertEqual(levels, {"L1", "L2", "L3"})
        self.assertEqual(expiries, {15, 30})
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row["outcome"] == "win" for row in rows))

    def test_summary_totals_match_raw_rows(self) -> None:
        runner = BacktestRunner(BacktestConfig(expiry_seconds=[15], payout_pct=92.0), stack_factory=_fake_stack_factory)
        rows = runner.replay_asset_ticks(
            "EURUSD_otc",
            [
                {"t": 0.0, "p": 1.0000, "a": "EURUSD_otc"},
                {"t": 1.0, "p": 1.0000, "a": "EURUSD_otc"},
                {"t": 16.0, "p": 1.0010, "a": "EURUSD_otc"},
            ],
            date="2026-05-15",
        )

        summary = runner.summarize(rows)

        self.assertEqual(summary["overall"]["trades"], len(rows))
        self.assertEqual(summary["by_level_expiry"]["L1|15"]["wins"], 1)
        self.assertAlmostEqual(summary["by_level_expiry"]["L1|15"]["net_pl"], 0.92)


class GhostTradeRepriceTests(unittest.TestCase):
    def test_load_ghost_trades_validates_required_entry_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "auto_ghost_test.jsonl"
            path.write_text(
                json.dumps({"id": "ghost-1", "asset": "EURUSD_otc", "direction": "call", "entry_time": 1000.0}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(GhostTradeSchemaError) as error:
                load_ghost_trades_from_file(path)

        self.assertIn("missing required field 'entry_price'", str(error.exception))

    def test_reprice_ghost_trades_keeps_real_entry_and_scores_alternate_expiries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            tick_dir = root / "ticks" / "EURUSD_otc"
            tick_dir.mkdir(parents=True)
            tick_dir.joinpath("1970-01-01.jsonl").write_text(
                "\n".join([
                    json.dumps({"t": 1000.0, "p": 1.0000, "a": "EURUSD_otc"}),
                    json.dumps({"t": 1015.0, "p": 1.0010, "a": "EURUSD_otc"}),
                    json.dumps({"t": 1030.0, "p": 0.9990, "a": "EURUSD_otc"}),
                ]) + "\n",
                encoding="utf-8",
            )

            session_file = root / "sessions" / "auto_ghost_test.jsonl"
            session_file.parent.mkdir(parents=True)
            session_file.write_text(
                json.dumps(
                    {
                        "id": "trade-1",
                        "trade_id": "ghost-abc",
                        "session_id": "auto_ghost_test",
                        "asset": "EURUSD_otc",
                        "direction": "call",
                        "entry_time": 1000.0,
                        "entry_price": 1.0000,
                        "expiration_seconds": 60,
                        "outcome": "loss",
                        "payout_pct": 92.0,
                        "confidence": "HIGH",
                        "oteo_score": 88.0,
                        "strategy_level": "level3",
                    }
                ) + "\n",
                encoding="utf-8",
            )

            rows = reprice_ghost_trades([session_file], tick_root=root / "ticks", expiry_seconds=[15, 30], payout_pct=92.0)

        self.assertEqual(len(rows), 2)
        self.assertEqual([row["expiry_seconds"] for row in rows], [15, 30])
        self.assertTrue(all(row["entry_time"] == 1000.0 for row in rows))
        self.assertTrue(all(row["entry_price"] == 1.0000 for row in rows))
        self.assertEqual([row["outcome"] for row in rows], ["win", "loss"])
        self.assertEqual({row["original_expiration_seconds"] for row in rows}, {60})
        self.assertEqual({row["original_outcome"] for row in rows}, {"loss"})
        self.assertEqual({row["source_session"] for row in rows}, {"auto_ghost_test"})
        self.assertEqual({row["strategy_level"] for row in rows}, {"level3"})

    def test_reprice_ghost_trades_fails_loudly_when_matching_tick_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            session_file = root / "sessions" / "auto_ghost_test.jsonl"
            session_file.parent.mkdir(parents=True)
            session_file.write_text(
                json.dumps(
                    {
                        "id": "trade-1",
                        "session_id": "auto_ghost_test",
                        "asset": "EURUSD_otc",
                        "direction": "put",
                        "entry_time": 1000.0,
                        "entry_price": 1.0000,
                        "expiration_seconds": 60,
                    }
                ) + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(FileNotFoundError) as error:
                reprice_ghost_trades([session_file], tick_root=root / "ticks", expiry_seconds=[15], payout_pct=92.0)

        self.assertIn("Missing tick file for ghost trade", str(error.exception))
        self.assertIn("EURUSD_otc", str(error.exception))


class MarkdownReportTests(unittest.TestCase):
    """Phase 3 — deterministic tests for generate_markdown_report and helpers."""

    # ------------------------------------------------------------------
    # _breakeven_win_rate
    # ------------------------------------------------------------------
    def test_breakeven_win_rate_at_92_pct_payout(self) -> None:
        # 100 / (1 + 0.92) = 52.0833...  → rounds to 52.08
        result = _breakeven_win_rate(92.0)
        self.assertAlmostEqual(result, 52.08, places=2)

    def test_breakeven_win_rate_at_80_pct_payout(self) -> None:
        # 100 / (1 + 0.80) = 55.555...  → rounds to 55.56
        result = _breakeven_win_rate(80.0)
        self.assertAlmostEqual(result, 55.56, places=2)

    # ------------------------------------------------------------------
    # _matrix_table
    # ------------------------------------------------------------------
    def test_matrix_table_renders_win_rates_and_small_sample_warning(self) -> None:
        grouped = {
            "L1|15": {"wins": 2, "losses": 1, "win_rate": 66.67, "trades": 3, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": 0.84, "roi": 28.0},
            "L1|30": {"wins": 0, "losses": 0, "win_rate": 0.0, "trades": 0, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": 0.0, "roi": 0.0},
        }
        lines = _matrix_table(grouped, row_label="Level", col_label="Expiry (s)", payout_pct=92.0, min_sample=30)
        table_text = "\n".join(lines)

        # Header row must contain both expiry columns.
        self.assertIn("15", table_text)
        self.assertIn("30", table_text)
        # Small-sample warning must appear for n=3.
        self.assertIn("⚠️ n=3", table_text)
        # Zero-settled cell must render as em-dash.
        self.assertIn("—", table_text)

    def test_matrix_table_no_small_sample_warning_when_above_threshold(self) -> None:
        # Build a group with exactly MIN_SAMPLE_SIZE settled trades.
        wins = MIN_SAMPLE_SIZE
        grouped = {
            f"L1|15": {
                "wins": wins,
                "losses": 0,
                "win_rate": 100.0,
                "trades": wins,
                "draws": 0,
                "missing_exit": 0,
                "insufficient_data": 0,
                "net_pl": float(wins) * 0.92,
                "roi": 92.0,
            }
        }
        lines = _matrix_table(grouped, row_label="Level", col_label="Expiry (s)", payout_pct=92.0, min_sample=MIN_SAMPLE_SIZE)
        table_text = "\n".join(lines)
        self.assertNotIn("⚠️", table_text)

    # ------------------------------------------------------------------
    # _suppression_audit
    # ------------------------------------------------------------------
    def test_suppression_audit_counts_reasons_correctly(self) -> None:
        rows = [
            {"level2_suppressed_reason": "weak_adx", "level3_suppressed_reason": None},
            {"level2_suppressed_reason": "weak_adx", "level3_suppressed_reason": "dead_market"},
            {"level2_suppressed_reason": "sr_proximity", "level3_suppressed_reason": "dead_market"},
            {"level2_suppressed_reason": None, "level3_suppressed_reason": None},
        ]
        lines = _suppression_audit(rows)
        text = "\n".join(lines)

        self.assertIn("weak_adx", text)
        self.assertIn("sr_proximity", text)
        self.assertIn("dead_market", text)
        # weak_adx appears twice — must come before sr_proximity (sorted by count desc).
        self.assertLess(text.index("weak_adx"), text.index("sr_proximity"))

    def test_suppression_audit_shows_no_suppressions_message_when_empty(self) -> None:
        rows = [{"level2_suppressed_reason": None, "level3_suppressed_reason": None}]
        lines = _suppression_audit(rows)
        text = "\n".join(lines)
        self.assertIn("_No Level 2 suppressions recorded._", text)
        self.assertIn("_No Level 3 suppressions recorded._", text)

    # ------------------------------------------------------------------
    # _recommendations
    # ------------------------------------------------------------------
    def test_recommendations_flags_insufficient_sample(self) -> None:
        summary = {
            "overall": {"wins": 5, "losses": 3, "win_rate": 62.5, "trades": 8, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": 1.6, "roi": 20.0},
            "by_asset_expiry": {},
            "by_level_expiry": {},
        }
        lines = _recommendations(summary, payout_pct=92.0, min_sample=30, exclusion_threshold=45.0)
        text = "\n".join(lines)
        self.assertIn("Insufficient overall sample", text)

    def test_recommendations_flags_below_breakeven(self) -> None:
        # 40 settled trades, 40% win-rate → below 52.08% breakeven.
        summary = {
            "overall": {"wins": 16, "losses": 24, "win_rate": 40.0, "trades": 40, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": -9.28, "roi": -23.2},
            "by_asset_expiry": {},
            "by_level_expiry": {},
        }
        lines = _recommendations(summary, payout_pct=92.0, min_sample=30, exclusion_threshold=45.0)
        text = "\n".join(lines)
        self.assertIn("below breakeven", text)
        self.assertIn("🔴", text)

    def test_recommendations_positive_edge_message(self) -> None:
        # 40 settled trades, 60% win-rate → above breakeven.
        summary = {
            "overall": {"wins": 24, "losses": 16, "win_rate": 60.0, "trades": 40, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": 6.08, "roi": 15.2},
            "by_asset_expiry": {},
            "by_level_expiry": {},
        }
        lines = _recommendations(summary, payout_pct=92.0, min_sample=30, exclusion_threshold=45.0)
        text = "\n".join(lines)
        self.assertIn("positive edge", text)
        self.assertIn("✅", text)

    def test_recommendations_flags_asset_exclusion_candidate(self) -> None:
        # EURUSD_otc has 40 settled trades at 40% win-rate → exclusion candidate.
        summary = {
            "overall": {"wins": 16, "losses": 24, "win_rate": 40.0, "trades": 40, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": -9.28, "roi": -23.2},
            "by_asset_expiry": {
                "EURUSD_otc|15": {"wins": 8, "losses": 12, "win_rate": 40.0, "trades": 20, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": -4.64, "roi": -23.2},
                "EURUSD_otc|30": {"wins": 8, "losses": 12, "win_rate": 40.0, "trades": 20, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": -4.64, "roi": -23.2},
            },
            "by_level_expiry": {},
        }
        lines = _recommendations(summary, payout_pct=92.0, min_sample=30, exclusion_threshold=45.0)
        text = "\n".join(lines)
        self.assertIn("EURUSD_otc", text)
        self.assertIn("exclusion candidates", text)

    def test_recommendations_best_and_worst_expiry_ranking(self) -> None:
        # L1|15 → 70% win-rate (n=30), L1|30 → 50% win-rate (n=30).
        summary = {
            "overall": {"wins": 36, "losses": 24, "win_rate": 60.0, "trades": 60, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": 9.12, "roi": 15.2},
            "by_asset_expiry": {},
            "by_level_expiry": {
                "L1|15": {"wins": 21, "losses": 9, "win_rate": 70.0, "trades": 30, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": 10.32, "roi": 34.4},
                "L1|30": {"wins": 15, "losses": 15, "win_rate": 50.0, "trades": 30, "draws": 0, "missing_exit": 0, "insufficient_data": 0, "net_pl": -1.2, "roi": -4.0},
            },
        }
        lines = _recommendations(summary, payout_pct=92.0, min_sample=30, exclusion_threshold=45.0)
        text = "\n".join(lines)
        self.assertIn("Best expiry", text)
        self.assertIn("15s", text)
        self.assertIn("Worst expiry", text)
        self.assertIn("30s", text)

    # ------------------------------------------------------------------
    # generate_markdown_report — structural contract
    # ------------------------------------------------------------------
    def test_generate_markdown_report_contains_all_required_sections(self) -> None:
        runner = BacktestRunner(
            BacktestConfig(expiry_seconds=[15, 30], payout_pct=92.0),
            stack_factory=_fake_stack_factory,
        )
        ticks = [
            {"t": 0.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 1.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 16.0, "p": 1.0010, "a": "EURUSD_otc"},
            {"t": 31.0, "p": 1.0020, "a": "EURUSD_otc"},
        ]
        rows = runner.replay_asset_ticks("EURUSD_otc", ticks, date="2026-05-15")
        summary = runner.summarize(rows)

        report = generate_markdown_report(
            rows,
            summary,
            title="Test Report",
            payout_pct=92.0,
            generated_at="2026-05-15T00:00:00Z",
        )

        self.assertIn("# Test Report", report)
        self.assertIn("## Overall Statistics", report)
        self.assertIn("## Level × Expiry Win-Rate Matrix", report)
        self.assertIn("## Asset × Expiry Win-Rate Matrix", report)
        self.assertIn("## Regime × Expiry Win-Rate Matrix", report)
        self.assertIn("## Confidence × Expiry Win-Rate Matrix", report)
        self.assertIn("## Suppression Audit", report)
        self.assertIn("## Recommendations", report)
        self.assertIn("2026-05-15T00:00:00Z", report)
        self.assertIn("52.08%", report)  # breakeven at 92% payout

    def test_generate_markdown_report_writes_to_file(self) -> None:
        runner = BacktestRunner(
            BacktestConfig(expiry_seconds=[15], payout_pct=92.0),
            stack_factory=_fake_stack_factory,
        )
        ticks = [
            {"t": 0.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 1.0, "p": 1.0000, "a": "EURUSD_otc"},
            {"t": 16.0, "p": 1.0010, "a": "EURUSD_otc"},
        ]
        rows = runner.replay_asset_ticks("EURUSD_otc", ticks, date="2026-05-15")
        summary = runner.summarize(rows)

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_root = Path(tmp_dir) / "reports"
            report_root.mkdir()
            md_path = report_root / "test_analysis.md"
            md_path.write_text(
                generate_markdown_report(rows, summary, title="File Write Test", payout_pct=92.0),
                encoding="utf-8",
            )
            content = md_path.read_text(encoding="utf-8")

        self.assertIn("# File Write Test", content)
        self.assertIn("## Recommendations", content)


if __name__ == "__main__":
    unittest.main()
