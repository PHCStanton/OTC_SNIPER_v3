import shutil
import tempfile
import unittest
from pathlib import Path

from app.backend.models.domain import TradeKind, TradeRecord
from app.backend.models.requests import TradeExecutionRequest
from app.backend.services.tick_logger import TickLogger
from app.backend.services.trade_service import TradeService


class GhostTickSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_recent_ignores_non_dated_jsonl_files(self) -> None:
        asset_dir = self.temp_dir / "AUDCAD_otc"
        asset_dir.mkdir(parents=True, exist_ok=True)
        (asset_dir / "tick_log_eg_for_dev.jsonl").write_text(
            '{"t": 1775788744.737, "p": 1.00113}\n',
            encoding="utf-8",
        )
        (asset_dir / "2026-04-25.jsonl").write_text(
            '{"t": 1777116253.113, "p": 0.88874}\n',
            encoding="utf-8",
        )

        logger = TickLogger(self.temp_dir)
        recent_ticks = logger.load_recent("AUDCAD_otc", max_ticks=1)

        self.assertEqual(len(recent_ticks), 1)
        self.assertAlmostEqual(recent_ticks[0]["t"], 1777116253.113)
        self.assertAlmostEqual(recent_ticks[0]["p"], 0.88874)

    def test_resolve_ghost_entry_price_prefers_entry_context(self) -> None:
        service = object.__new__(TradeService)
        request = TradeExecutionRequest(
            asset_id="AUDCAD_otc",
            direction="call",
            amount=25.0,
            expiration=60,
            trade_mode="ghost",
            entry_context={"price": 0.88874, "timestamp": 1777116253.113},
        )

        entry_price = service._resolve_ghost_entry_price(
            request,
            {"t": 1775788744.737, "p": 1.00113},
        )

        self.assertAlmostEqual(entry_price, 0.88874)

    def test_sanitize_ghost_exit_tick_rejects_stale_ticks(self) -> None:
        service = object.__new__(TradeService)
        trade = TradeRecord(
            session_id="auto_ghost_test",
            asset="AUDCAD_otc",
            direction="call",
            amount=25.0,
            expiration_seconds=60,
            kind=TradeKind.GHOST,
            entry_time=1777116253.113,
        )

        sanitized_tick = service._sanitize_ghost_exit_tick(
            trade,
            {"t": 1775788744.737, "p": 1.00113},
        )

        self.assertIsNone(sanitized_tick)


if __name__ == "__main__":
    unittest.main()
