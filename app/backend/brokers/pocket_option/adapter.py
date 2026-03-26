"""Pocket Option broker adapter for Phase 1."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from ...session.manager import SessionManager
from ..base import Asset, Balance, BrokerAdapter, BrokerType, Tick, TradeOrder, TradeResult
from ..registry import BrokerRegistry
from .assets import build_asset_list, normalize_asset, to_pocket_option_format, verify_otc_asset

logger = logging.getLogger(__name__)


class PocketOptionAdapter(BrokerAdapter):
    broker_type = BrokerType.POCKET_OPTION
    display_name = "Pocket Option"
    supports_otc = True
    supports_demo = True

    def __init__(self) -> None:
        self._session_manager = SessionManager()
        self._connection_status = "disconnected"
        self._last_error: str | None = None

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    async def connect(self, credentials: Dict[str, str]) -> bool:
        ssid = credentials.get("ssid", "").strip()
        if not ssid:
            self._connection_status = "error"
            self._last_error = "SSID is required for Pocket Option connection"
            raise ValueError(self._last_error)

        self._connection_status = "connecting"
        try:
            self._session_manager.connect(ssid)
            self._connection_status = "connected"
            self._last_error = None
            return True
        except Exception as exc:
            self._connection_status = "error"
            self._last_error = str(exc)
            logger.error("Pocket Option connection failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._session_manager.disconnect()
        self._connection_status = "disconnected"
        self._last_error = None

    async def get_assets(self, demo: bool = True) -> List[Asset]:
        return build_asset_list()

    async def subscribe_ticks(self, asset: str) -> None:
        """Starts streaming ticks for the given asset."""
        session = self._session_manager.current_session
        if session and session.is_connected and session._api:
            # period 1 = 1 second candles/ticks
            pocket_asset = to_pocket_option_format(normalize_asset(asset))
            await asyncio.get_running_loop().run_in_executor(
                None, session._api.change_symbol, pocket_asset, 1
            )
            logger.info("Subscribed to ticks for %s (%s)", asset, pocket_asset)

    async def execute_trade(self, order: TradeOrder) -> TradeResult:
        session = self._session_manager.current_session
        if session is None or not session.is_connected:
            return TradeResult(success=False, message="Not connected to Pocket Option.", broker=BrokerType.POCKET_OPTION)

        canonical = normalize_asset(order.asset_id)
        pocket_asset = to_pocket_option_format(canonical)
        if not verify_otc_asset(canonical):
            return TradeResult(
                success=False,
                message=f"Asset not in verified OTC list: {pocket_asset}",
                broker=BrokerType.POCKET_OPTION,
            )

        direction = order.direction.strip().lower()
        if direction not in {"call", "put"}:
            return TradeResult(success=False, message="Direction must be 'call' or 'put'.", broker=BrokerType.POCKET_OPTION)

        try:
            result = session.buy(order.amount, pocket_asset, direction, order.expiration)
            trade_id = None
            entry_price = None

            if isinstance(result, tuple):
                if len(result) >= 2:
                    trade_id = str(result[1])
                if len(result) >= 1 and isinstance(result[0], (int, float)):
                    entry_price = float(result[0])
            elif isinstance(result, dict):
                trade_id = str(result.get("trade_id")) if result.get("trade_id") is not None else None
                if result.get("entry_price") is not None:
                    entry_price = float(result["entry_price"])
            elif isinstance(result, bool):
                if not result:
                    return TradeResult(success=False, message="Broker returned a falsey trade result.", broker=BrokerType.POCKET_OPTION)

            return TradeResult(
                success=True,
                trade_id=trade_id,
                entry_price=entry_price,
                message="Trade submitted successfully.",
                broker=BrokerType.POCKET_OPTION,
            )
        except Exception as exc:
            self._connection_status = "error"
            self._last_error = str(exc)
            return TradeResult(success=False, message=str(exc), broker=BrokerType.POCKET_OPTION)

    async def get_balance(self, demo: bool = True) -> Balance:
        session = self._session_manager.current_session
        balance = session.get_balance() if session is not None else None
        result = Balance(broker=BrokerType.POCKET_OPTION)

        if balance is None:
            return result

        if session is not None and session.is_demo:
            result.demo = float(balance)
        else:
            result.real = float(balance)
        return result

    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        return []

    def get_connection_status(self) -> str:
        return self._connection_status


BrokerRegistry.register(PocketOptionAdapter)
