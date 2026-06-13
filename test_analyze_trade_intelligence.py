import unittest
from datetime import datetime, timezone
import tempfile
import json
from pathlib import Path

# Custom exceptions to be implemented in scripts/analyze_trade_intelligence.py
# Imported locally here or mocked/tested directly.
# Since we will implement these in analyze_trade_intelligence.py, let's import them.
try:
    from scripts.analyze_trade_intelligence import (
        SchemaError,
        JoinAmbiguityError,
        MissingTickFileError,
        validate_ghost_trade,
        validate_signal,
        validate_tick,
        format_utc_datetime,
        join_trade_with_signals,
    )
except ImportError:
    # Fallback to define them for isolated test compilation if scripts hasn't been written
    # but since we write them sequentially, let's make sure they align.
    pass

class TestAnalyzeTradeIntelligence(unittest.TestCase):

    def test_format_utc_datetime(self):
        """Verify that timestamps are formatted correctly in Gregorian UTC format."""
        ts = 1776813205.044
        formatted = format_utc_datetime(ts)
        self.assertEqual(formatted, "2026-04-21 23:13:25 UTC")
        
        ts_int = 1776813205
        formatted_int = format_utc_datetime(ts_int)
        self.assertEqual(formatted_int, "2026-04-21 23:13:25 UTC")

    def test_validate_ghost_trade_valid(self):
        """Verify a valid ghost trade parsed successfully."""
        trade_data = {
            "id": "12d08c08",
            "session_id": "auto_ghost_123",
            "asset": "EURUSD_otc",
            "direction": "call",
            "entry_time": 1776813205.0,
            "entry_price": 1.1500,
            "outcome": "win",
            "oteo_score": 83.5,
            "payout_pct": 89.0,
            "exit_time": 1776813265.0,
            "exit_price": 1.1510,
            "profit": 22.25
        }
        validated = validate_ghost_trade(trade_data, "test.jsonl", 1)
        self.assertEqual(validated["asset"], "EURUSD_otc")
        self.assertEqual(validated["direction"], "CALL")
        self.assertEqual(validated["entry_time"], 1776813205.0)

    def test_validate_ghost_trade_invalid(self):
        """Verify malformed ghost trades raise SchemaError."""
        # Missing required field 'asset'
        trade_data = {
            "id": "12d08c08",
            "session_id": "auto_ghost_123",
            "direction": "call",
            "entry_time": 1776813205.0,
            "entry_price": 1.1500,
            "outcome": "win"
        }
        with self.assertRaises(SchemaError):
            validate_ghost_trade(trade_data, "test.jsonl", 1)

        # Invalid direction
        trade_data_invalid_dir = {
            "id": "12d08c08",
            "session_id": "auto_ghost_123",
            "asset": "EURUSD_otc",
            "direction": "up",
            "entry_time": 1776813205.0,
            "entry_price": 1.1500,
            "outcome": "win"
        }
        with self.assertRaises(SchemaError):
            validate_ghost_trade(trade_data_invalid_dir, "test.jsonl", 1)

    def test_validate_signal_valid(self):
        """Verify valid signals pass schema parsing."""
        signal_data = {
            "t": 1775610532.177,
            "asset": "#AAPL_otc",
            "score": 99.7,
            "dir": "CALL",
            "price": 185.7,
            "conf": "MEDIUM",
            "manip": False
        }
        validated = validate_signal(signal_data, "test.jsonl", 1)
        self.assertEqual(validated["asset"], "#AAPL_otc")
        self.assertEqual(validated["dir"], "CALL")
        self.assertEqual(validated["t"], 1775610532.177)

    def test_validate_signal_invalid(self):
        """Verify invalid signals raise SchemaError."""
        # Missing 't'
        signal_data = {
            "asset": "#AAPL_otc",
            "score": 99.7,
            "dir": "CALL",
            "price": 185.7,
            "manip": False
        }
        with self.assertRaises(SchemaError):
            validate_signal(signal_data, "test.jsonl", 1)

    def test_validate_tick_valid(self):
        """Verify valid tick passes validation."""
        tick_data = {
            "t": 1781176486.247,
            "p": 1.13977,
            "a": "EURUSD_otc",
            "b": "pocket_option"
        }
        validated = validate_tick(tick_data, "test.jsonl", 1)
        self.assertEqual(validated["a"], "EURUSD_otc")
        self.assertEqual(validated["p"], 1.13977)

    def test_validate_tick_invalid(self):
        """Verify invalid ticks raise SchemaError."""
        tick_data = {
            "t": "not-numeric",
            "p": 1.13977,
            "a": "EURUSD_otc"
        }
        with self.assertRaises(SchemaError):
            validate_tick(tick_data, "test.jsonl", 1)

    def test_join_exact_timestamp(self):
        """Verify that exact timestamp in entry_context takes absolute precedence."""
        trade = {
            "id": "trade-1",
            "asset": "EURUSD_otc",
            "direction": "CALL",
            "entry_time": 1005.0,
            "entry_price": 1.1500,
            "outcome": "win",
            "entry_context": {
                "timestamp": 1000.0,
                "oteo_score": 83.5
            }
        }
        # Signals: one nearest to entry_time (1005.0), one exactly matches entry_context.timestamp (1000.0)
        signals = [
            {"t": 1000.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 83.5, "price": 1.1495, "manip": False, "conf": "MEDIUM"},
            {"t": 1005.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 90.0, "price": 1.1500, "manip": False, "conf": "HIGH"},
        ]
        
        matched, drift = join_trade_with_signals(trade, signals, tolerance=10.0)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["t"], 1000.0)
        self.assertEqual(drift, 5.0)  # Drift relative to entry_time (1005.0 - 1000.0)

    def test_join_proximity_matching(self):
        """Verify that join matches the closest signal within tolerance when no exact match exists."""
        trade = {
            "id": "trade-1",
            "asset": "EURUSD_otc",
            "direction": "CALL",
            "entry_time": 1005.0,
            "entry_price": 1.1500,
            "outcome": "win"
        }
        signals = [
            {"t": 1001.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 80.0, "price": 1.1490, "manip": False, "conf": "MEDIUM"},
            {"t": 1004.2, "asset": "EURUSD_otc", "dir": "CALL", "score": 85.0, "price": 1.1495, "manip": False, "conf": "MEDIUM"},
            {"t": 1012.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 90.0, "price": 1.1505, "manip": False, "conf": "HIGH"},
        ]
        
        matched, drift = join_trade_with_signals(trade, signals, tolerance=5.0)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["t"], 1004.2)
        self.assertAlmostEqual(drift, 0.8)

    def test_join_out_of_tolerance(self):
        """Verify that signals outside of the tolerance window are not joined."""
        trade = {
            "id": "trade-1",
            "asset": "EURUSD_otc",
            "direction": "CALL",
            "entry_time": 1005.0,
            "entry_price": 1.1500,
            "outcome": "win"
        }
        signals = [
            {"t": 999.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 80.0, "price": 1.1490, "manip": False, "conf": "MEDIUM"},
            {"t": 1011.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 90.0, "price": 1.1505, "manip": False, "conf": "HIGH"},
        ]
        
        # Tolerance is 5s, nearest signal is 6s away (1011.0)
        matched, drift = join_trade_with_signals(trade, signals, tolerance=5.0)
        self.assertIsNone(matched)

    def test_join_ambiguity_identical_proximity(self):
        """Verify that identical time drift on two distinct matching signals raises JoinAmbiguityError."""
        trade = {
            "id": "trade-1",
            "asset": "EURUSD_otc",
            "direction": "CALL",
            "entry_time": 1000.0,
            "entry_price": 1.1500,
            "outcome": "win"
        }
        # Two signals equidistant from entry_time
        signals = [
            {"t": 998.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 80.0, "price": 1.1490, "manip": False, "conf": "MEDIUM"},
            {"t": 1002.0, "asset": "EURUSD_otc", "dir": "CALL", "score": 85.0, "price": 1.1495, "manip": False, "conf": "MEDIUM"},
        ]
        
        with self.assertRaises(JoinAmbiguityError):
            join_trade_with_signals(trade, signals, tolerance=5.0)

if __name__ == "__main__":
    unittest.main()
