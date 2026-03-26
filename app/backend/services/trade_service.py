"""Trade execution service with background outcome tracking."""
import asyncio
import logging
from time import time as unix_time
from typing import Dict, Any

from ..brokers.base import BrokerType, TradeOrder
from ..brokers.registry import BrokerRegistry
from ..data.repository import DataRepository
from ..models.domain import TradeKind, TradeRecord
from ..models.requests import TradeExecutionRequest

logger = logging.getLogger(__name__)

class TradeService:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    async def execute_trade(self, broker_type: BrokerType, request: TradeExecutionRequest) -> Dict[str, Any]:
        """Execute a trade securely mapping it to the broker adapter"""
        adapter = BrokerRegistry.get_adapter(broker_type, account_key=request.account_key)
        
        order = TradeOrder(
            asset_id=request.asset_id,
            direction=request.direction,
            amount=request.amount,
            expiration=request.expiration,
            broker=broker_type,
        )

        result = await adapter.execute_trade(order)
        session = adapter.session_manager.snapshot()

        if not result.success:
            return {
                "success": False,
                "message": result.message,
                "trade_id": result.trade_id,
                "entry_price": result.entry_price,
                "session_id": session.session_id,
                "connection_status": adapter.get_connection_status()
            }

        trade_record = TradeRecord(
            session_id=session.session_id or 'unknown',
            asset=request.asset_id,
            direction=request.direction,
            amount=request.amount,
            expiration_seconds=request.expiration,
            broker=broker_type.value,
            kind=TradeKind.LIVE,
            success=True,
            message=result.message,
            trade_id=result.trade_id,
            entry_price=result.entry_price,
            entry_time=unix_time(),
        )

        # Warn loudly if session_id is unknown — this will bundle trades into a single file.
        if not session.session_id:
            logger.warning("Session ID is missing. Trade will be logged under 'unknown' session.")

        await self.repository.write_trade(trade_record)

        # Launch background task to check win
        asyncio.create_task(self._track_trade_outcome(trade_record, adapter, request.expiration))

        return {
            "success": True,
            "message": result.message,
            "trade_id": result.trade_id,
            "entry_price": result.entry_price,
            "session_id": session.session_id,
            "connection_status": adapter.get_connection_status()
        }

    async def _track_trade_outcome(self, trade: TradeRecord, adapter, expiration: int):
        """Background coroutine to await expiration and query the trade result."""
        # Wait for trade to expire + a small 2-second buffer
        await asyncio.sleep(expiration + 2)

        try:
            session = adapter.session_manager.current_session
            if not session or not session.is_connected:
                logger.warning("Session disconnected before checking trade %s", trade.trade_id)
                return

            if not trade.trade_id:
                logger.warning("Trade has no trade_id, cannot check outcome.")
                return

            # Fix #1: check_win is blocking — run it in a thread executor to avoid
            # blocking the asyncio event loop.
            loop = asyncio.get_event_loop()
            outcome_data = await loop.run_in_executor(None, session.check_win, trade.trade_id)

            if outcome_data is None:
                logger.warning("Could not retrieve outcome for trade %s", trade.trade_id)
                return

            trade.exit_time = unix_time()

            # Fix #2: Structured outcome parsing with explicit type checks.
            if isinstance(outcome_data, dict):
                raw_outcome = outcome_data.get("win") or outcome_data.get("result")
                trade.outcome = str(raw_outcome) if raw_outcome is not None else "unknown"
                raw_profit = outcome_data.get("profit")
                trade.profit = float(raw_profit) if raw_profit is not None else 0.0
            elif isinstance(outcome_data, (int, float)):
                # Some API versions return a numeric profit directly
                trade.outcome = "win" if float(outcome_data) > 0 else "loss"
                trade.profit = float(outcome_data)
            else:
                logger.warning(
                    "Unexpected outcome_data type %s for trade %s: %r",
                    type(outcome_data).__name__, trade.trade_id, outcome_data
                )
                trade.outcome = "unknown"
                trade.profit = 0.0

            await self.repository.update_trade(trade)
            logger.info(
                "Trade %s tracked. Outcome: %s, Profit: %s",
                trade.trade_id, trade.outcome, trade.profit
            )

        except Exception as e:
            logger.error("Error checking trade outcome for %s: %s", trade.trade_id, e)
