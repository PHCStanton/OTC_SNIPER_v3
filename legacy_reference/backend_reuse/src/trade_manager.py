"""
TradeManager — Concurrent Trade Orchestration
==============================================
Manages active trades, enforces limits from settings, and tracks results.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("TradeManager")


class TradeManager:
    """
    Manages concurrent trade execution with configurable limits.

    Features:
    - Tracks active (pending) trades
    - Enforces max_concurrent_trades from settings
    - Enforces cooldown between trades
    - Prevents duplicate same-asset trades (configurable)
    - Provides trade history with results
    """

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self._active_trades: Dict[str, Dict] = {}
        self._completed_trades: List[Dict] = []
        self._last_trade_time: float = 0
        self._lock = asyncio.Lock()

    def _get_trading_settings(self) -> Dict:
        settings = self.settings_manager.get_global()
        return settings.get("trading", {
            "max_concurrent_trades": 3,
            "default_amount": 10.0,
            "default_expiration": 60,
            "allow_same_asset_trades": False,
            "cooldown_between_trades_ms": 1000
        })

    async def can_place_trade(self, asset_id: str) -> tuple[bool, str]:
        """Check if a new trade can be placed. Returns (allowed, reason)."""
        settings = self._get_trading_settings()

        async with self._lock:
            max_concurrent = settings.get("max_concurrent_trades", 3)
            if len(self._active_trades) >= max_concurrent:
                return False, f"Maximum concurrent trades reached ({max_concurrent})"

            cooldown_ms = settings.get("cooldown_between_trades_ms", 1000)
            elapsed_ms = (time.time() - self._last_trade_time) * 1000
            if elapsed_ms < cooldown_ms:
                remaining = int(cooldown_ms - elapsed_ms)
                return False, f"Trade cooldown active ({remaining}ms remaining)"

            if not settings.get("allow_same_asset_trades", False):
                for trade in self._active_trades.values():
                    if trade.get("asset_id") == asset_id:
                        return False, f"Active trade already exists for {asset_id}"

            return True, "OK"

    async def register_trade(self, trade_id: str, trade_info: Dict) -> None:
        """Register a newly placed trade as active."""
        async with self._lock:
            self._active_trades[trade_id] = {
                **trade_info,
                "placed_at": time.time(),
                "status": "PENDING"
            }
            self._last_trade_time = time.time()

    async def complete_trade(self, trade_id: str, result: Dict) -> None:
        """Move a trade from active to completed."""
        async with self._lock:
            trade = self._active_trades.pop(trade_id, None)
            if trade:
                trade.update(result)
                trade["status"] = "WIN" if result.get("win") else "LOSS"
                trade["completed_at"] = time.time()
                self._completed_trades.append(trade)

    def get_active_trades(self) -> List[Dict]:
        return list(self._active_trades.values())

    def get_all_history(self, limit: int = 50) -> List[Dict]:
        return (list(self._active_trades.values()) + self._completed_trades)[-limit:]
