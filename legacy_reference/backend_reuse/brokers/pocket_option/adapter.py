"""
Pocket Option Broker Adapter
============================
Wraps OTCDataManager to implement the BrokerAdapter interface.
"""
import asyncio
import logging
from typing import AsyncIterator, Dict, List

from brokers.base import (
    BrokerAdapter, BrokerType, Asset, AssetType, Tick,
    TradeOrder, TradeResult, Balance,
)
from asset_utils import normalize_asset, to_pocket_option_format

logger = logging.getLogger("PocketOptionAdapter")

try:
    import sys
    import os
    # Add project root to path to find otc_sniper package if not already
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../../tui'))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
        
    from otc_sniper.frontend.data_manager import OTCDataManager
except ImportError:
    OTCDataManager = None
    logger.warning("OTCDataManager not found. PocketOptionAdapter will not be functional.")


class PocketOptionAdapter(BrokerAdapter):
    """
    Pocket Option adapter wrapping OTCDataManager.
    """
    
    broker_type = BrokerType.POCKET_OPTION
    display_name = "Pocket Option"
    supports_otc = True
    supports_demo = True

    def __init__(self):
        self.dm = None
        self.demo = True

    async def connect(self, credentials: Dict[str, str]) -> bool:
        if OTCDataManager is None:
            logger.error("OTCDataManager is not available.")
            return False
            
        ssid = credentials.get("ssid")
        demo_str = credentials.get("demo", "true")
        self.demo = str(demo_str).lower() == "true"
        
        if not ssid:
            logger.error("SSID is required for Pocket Option connection.")
            return False
            
        self.dm = OTCDataManager(ssid=ssid, demo=self.demo, auto_connect=False)
        
        loop = asyncio.get_running_loop()
        def init_wrapper():
            thread_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(thread_loop)
            try:
                return self.dm.init()
            finally:
                if not thread_loop.is_closed():
                    thread_loop.close()
                asyncio.set_event_loop(None)
                
        success = await loop.run_in_executor(None, init_wrapper)

        # Start trade result polling after successful connection
        if success and self.dm:
            self.dm.start_polling()
            logger.info("Trade result polling started")

        return success

    async def disconnect(self) -> None:
        if self.dm:
            # OTCDataManager does not have a direct disconnect method in this setup, 
            # but we can set it to None or try to close websockets if exposed.
            pass

    async def get_assets(self, demo: bool = True) -> List[Asset]:
        if not self.dm or not self.dm.assets_loaded:
            return []
            
        po_assets = self.dm.get_otc_assets()
        assets = []
        for a in po_assets:
            asset_id = normalize_asset(a.get("name", ""))
            if not asset_id:
                continue
            assets.append(Asset(
                id=asset_id,
                name=a.get("display", asset_id),
                asset_type=AssetType.OTC,
                payout=float(a.get("payout", 0.0)),
                broker=BrokerType.POCKET_OPTION,
                raw_id=a.get("name", "")
            ))
        return assets

    async def subscribe_ticks(self, asset: str) -> AsyncIterator[Tick]:
        # Ticks are currently streamed via Redis and the separate Collector.
        # This method is a placeholder for the unified BrokerAdapter interface.
        raise NotImplementedError("subscribe_ticks is handled by Collector/Redis in v2.")
        yield Tick(timestamp=0.0, asset=asset, price=0.0)

    async def execute_trade(self, order: TradeOrder) -> TradeResult:
        if not self.dm:
            return TradeResult(success=False, message="Not connected to broker.")
            
        canonical = normalize_asset(order.asset_id)
        po_asset = to_pocket_option_format(canonical)
        
        if not self.dm.select_asset(po_asset):
            return TradeResult(success=False, message=f"Asset not found: {po_asset}")
            
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.dm.execute_trade(
                direction=order.direction.lower(),
                amount=order.amount,
                expiration=order.expiration
            )
        )
        
        return TradeResult(
            success=result.get("success", False),
            message=result.get("message", ""),
            trade_id=result.get("trade_id")
        )

    async def get_balance(self, demo: bool = True) -> Balance:
        b = Balance()
        if not self.dm or not self.dm.session:
            return b
            
        if self.demo:
            b.demo = self.dm.session.balance
        else:
            b.real = self.dm.session.balance
        return b

    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        if not self.dm:
            return []
        raw = self.dm.trade_history[-limit:] if self.dm.trade_history else []
        return [{
            "open_time": t.get("timestamp", 0),
            "asset": t.get("asset_id", t.get("asset", "")),
            "direction": t.get("direction", ""),
            "amount": t.get("amount", 0),
            "status": "WIN" if t.get("win") is True else "LOSS" if t.get("win") is False else "PENDING",
            "trade_id": t.get("trade_id", ""),
            "profit": t.get("profit", 0)
        } for t in raw]

    def get_connection_status(self) -> str:
        if not self.dm:
            return "disconnected"
        return self.dm.connection_status
