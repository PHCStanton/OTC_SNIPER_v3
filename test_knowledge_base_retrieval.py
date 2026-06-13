import os
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from app.backend.services.ai_review import (
    KnowledgeBaseLoader,
    get_score_band,
    format_patterns_for_prompt
)
from app.backend.services.auto_ghost import AutoGhostService, AutoGhostConfig


class TestKnowledgeBaseRetrieval(unittest.TestCase):
    def setUp(self):
        # Reset the singleton instance of KnowledgeBaseLoader for isolation
        KnowledgeBaseLoader._instance = None

    def test_get_score_band(self):
        self.assertEqual(get_score_band(45), "<50")
        self.assertEqual(get_score_band(55), "50-64")
        self.assertEqual(get_score_band(70), "65-74")
        self.assertEqual(get_score_band(80), "75-84")
        self.assertEqual(get_score_band(90), "85-92")
        self.assertEqual(get_score_band(95), "93+")

    def test_format_patterns_for_prompt(self):
        empty = format_patterns_for_prompt([])
        self.assertEqual(empty, "No historical matching patterns found.")

        patterns = [
            {
                "pattern_key": "EURUSD_otc|level3|85-92|RANGE_BOUND|CALL",
                "sample_size": 25,
                "win_rate_pct": 68.0,
                "expectancy": 55.4,
                "boost_candidate": True,
                "suppression_candidate": False
            }
        ]
        formatted = format_patterns_for_prompt(patterns)
        self.assertIn("EURUSD_otc|level3|85-92|RANGE_BOUND|CALL", formatted)
        self.assertIn("N=25", formatted)
        self.assertIn("WinRate=68.0%", formatted)
        self.assertIn("Expectancy=55.40", formatted)
        self.assertIn("Boost: YES", formatted)

    def test_query_top_patterns_similarity(self):
        # Setup a mock patterns list
        loader = KnowledgeBaseLoader()
        loader.patterns = [
            {
                "pattern_key": "EURUSD_otc|level3|85-92|RANGE_BOUND|CALL",
                "asset": "EURUSD_otc",
                "strategy_level": "level3",
                "oteo_score_band": "85-92",
                "regime_label": "RANGE_BOUND",
                "direction": "CALL",
                "sample_size": 15,
                "win_rate_pct": 60.0,
                "expectancy": 40.0,
                "boost_candidate": False,
                "suppression_candidate": False
            },
            {
                "pattern_key": "EURUSD_otc|level3|85-92|RANGE_BOUND|PUT",
                "asset": "EURUSD_otc",
                "strategy_level": "level3",
                "oteo_score_band": "85-92",
                "regime_label": "RANGE_BOUND",
                "direction": "PUT",
                "sample_size": 10,
                "win_rate_pct": 50.0,
                "expectancy": 20.0,
                "boost_candidate": False,
                "suppression_candidate": False
            },
            {
                "pattern_key": "GBPUSD_otc|level3|85-92|RANGE_BOUND|CALL",
                "asset": "GBPUSD_otc",
                "strategy_level": "level3",
                "oteo_score_band": "85-92",
                "regime_label": "RANGE_BOUND",
                "direction": "CALL",
                "sample_size": 30,
                "win_rate_pct": 70.0,
                "expectancy": 80.0,
                "boost_candidate": True,
                "suppression_candidate": False
            }
        ]
        loader.loaded = True

        # Query 1: Exact match with EURUSD CALL
        results = loader.query_top_patterns(
            asset="EURUSD",
            strategy_level="level3",
            oteo_score=90.0,
            regime_label="RANGE_BOUND",
            direction="CALL",
            top_n=2
        )
        self.assertEqual(len(results), 2)
        # First should be the exact EURUSD CALL match (higher similarity: matches asset, level, regime, band, direction)
        self.assertEqual(results[0]["direction"], "CALL")
        self.assertEqual(results[0]["asset"], "EURUSD_otc")

        # Query 2: Case insensitivity and _otc suffix normalization
        results_normalized = loader.query_top_patterns(
            asset="eurusd_otc",
            strategy_level="level3",
            oteo_score=90.0,
            regime_label="range_bound",
            direction="call"
        )
        self.assertEqual(results_normalized[0]["asset"], "EURUSD_otc")

    def test_lazy_loading_from_temp_file(self):
        # Create a temp file containing mock JSON patterns
        mock_data = {
            "metadata": {
                "total_patterns": 1,
                "high_confidence_patterns": 0,
                "suppression_candidates": 0,
                "boost_candidates": 0
            },
            "patterns": [
                {
                    "pattern_key": "AUDUSD_otc|level2|65-74|CHOPPY|PUT",
                    "asset": "AUDUSD_otc",
                    "strategy_level": "level2",
                    "oteo_score_band": "65-74",
                    "regime_label": "CHOPPY",
                    "direction": "PUT",
                    "sample_size": 22,
                    "win_rate_pct": 42.0,
                    "expectancy": -15.0,
                    "boost_candidate": False,
                    "suppression_candidate": True
                }
            ]
        }

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False, encoding="utf-8") as temp_file:
            json.dump(mock_data, temp_file)
            temp_file_path = temp_file.name

        try:
            loader = KnowledgeBaseLoader()
            # Mock _find_kb_path to return our temp file
            with patch.object(loader, "_find_kb_path", return_value=Path(temp_file_path)):
                loader.lazy_load()
                self.assertTrue(loader.loaded)
                self.assertEqual(len(loader.patterns), 1)
                self.assertEqual(loader.patterns[0]["asset"], "AUDUSD_otc")
                self.assertEqual(loader.metadata["total_patterns"], 1)
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    @patch("app.backend.services.ai_service.get_ai_service")
    def test_ai_confirmation_prompt_construction(self, mock_get_ai_service):
        # Setup mock AI Service
        mock_ai_service = MagicMock()
        mock_ai_service.status.return_value.enabled = True
        mock_ai_service.settings.ai_model = "test-gpt-model"
        
        # Mock res response
        mock_res = MagicMock()
        mock_res.text = "CONFIRM"
        mock_res.model = "test-gpt-model"
        
        # AsyncMock for chat call
        mock_ai_service.chat = AsyncMock(return_value=mock_res)
        mock_get_ai_service.return_value = mock_ai_service

        # Initialize AutoGhost with a dummy trade service
        mock_trade_service = MagicMock()
        service = AutoGhostService(mock_trade_service, config=AutoGhostConfig(enabled=True))

        # Setup custom patterns in KnowledgeBaseLoader
        kb_loader = KnowledgeBaseLoader.get_instance()
        kb_loader.patterns = [
            {
                "pattern_key": "EURUSD_otc|level3|85-92|RANGE_BOUND|CALL",
                "asset": "EURUSD_otc",
                "strategy_level": "level3",
                "oteo_score_band": "85-92",
                "regime_label": "RANGE_BOUND",
                "direction": "CALL",
                "sample_size": 50,
                "win_rate_pct": 62.0,
                "expectancy": 45.0,
                "boost_candidate": True,
                "suppression_candidate": False
            }
        ]
        kb_loader.loaded = True

        # Run query confirmation
        async def run_test():
            confirmed, response = await service._query_ai_confirmation(
                asset="EURUSD",
                direction="CALL",
                oteo_score=90.0,
                market_context={
                    "regime_label": "RANGE_BOUND",
                    "regime_confidence": 85,
                    "regime_stable": True,
                    "trend_direction": "UP",
                    "adx": 18.5,
                    "cci": 110.0,
                    "cci_state": "normal",
                    "nearest_structure_atr": 1.2,
                    "tick_health": "good"
                },
                manipulation={
                    "pinning": 0.75,
                    "push_snap": 0.20
                },
                strategy_level="level3"
            )
            return confirmed, response

        confirmed, response = asyncio.run(run_test())

        self.assertTrue(confirmed)
        self.assertEqual(response, "CONFIRM")

        # Verify chat request contents
        mock_ai_service.chat.assert_called_once()
        chat_req = mock_ai_service.chat.call_args[0][0]
        
        system_content = chat_req.messages[0].content
        user_content = chat_req.messages[1].content

        # Verify system prompt has manipulation taxonomy
        self.assertIn("OTC Manipulation & Microstructure Patterns", system_content)
        self.assertIn("Liquidity Sweeps / Grabs", system_content)
        self.assertIn("Pinning", system_content)

        # Verify user prompt has formatted setup, patterns, and active flags
        self.assertIn("Strategy Level: LEVEL3", user_content)
        self.assertIn("Active Manipulation: pinning (severity: 0.75), push_snap (severity: 0.20)", user_content)
        self.assertIn("Historical Context (Top Matching KB Patterns):", user_content)
        self.assertIn("EURUSD_otc|level3|85-92|RANGE_BOUND|CALL: N=50, WinRate=62.0%, Expectancy=45.00", user_content)


if __name__ == "__main__":
    unittest.main()
