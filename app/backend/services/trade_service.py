"""Trade execution service with background outcome tracking."""
import asyncio
import logging
from time import time as unix_time
from typing import Dict, Any
from uuid import uuid4

from ..brokers.base import BrokerType, TradeOrder
from ..brokers.registry import BrokerRegistry
from ..config import get_settings
from ..data.repository import DataRepository
from ..models.domain import TradeKind, TradeRecord
from ..models.requests import TradeExecutionRequest
from .tick_logger import TickLogger

logger = logging.getLogger(__name__)

class TradeService:
    def __init__(self, repository: DataRepository, sio=None):
        self.repository = repository
        self.sio = sio
        settings = get_settings()
        self.tick_logger = TickLogger(settings.data_dir / "tick_logs")

    def _resolve_trade_kind(self, request: TradeExecutionRequest) -> TradeKind:
        trade_mode = str(getattr(request, "trade_mode", "live") or "live").strip().lower()
        if trade_mode == "ghost" or bool(getattr(request, "demo", False)):
            return TradeKind.GHOST
        return TradeKind.LIVE

    def _latest_logged_price(self, asset: str) -> float | None:
        try:
            recent_ticks = self.tick_logger.load_recent(asset, max_ticks=1)
            if not recent_ticks:
                return None
            return float(recent_ticks[-1]["p"])
        except Exception as exc:
            logger.warning("Failed to resolve latest logged price for %s: %s", asset, exc)
            return None

    def _resolve_payout_pct(self, adapter, asset_id: str) -> float:
        session = adapter.session_manager.current_session
        if session and session.is_connected:
            try:
                payout = session.get_payout(asset_id)
                payout_value = float(payout)
                if payout_value <= 1.0:
                    payout_value *= 100.0
                if payout_value > 0:
                    return payout_value
            except Exception as exc:
                logger.debug("Falling back to default payout for %s: %s", asset_id, exc)
        return 80.0

    async def _emit_trade_result(self, trade: TradeRecord) -> None:
        if not self.sio or trade.outcome not in {"win", "loss", "void"}:
            return
        await self.sio.emit(
            "trade_result",
            {
                "trade_id": trade.trade_id,
                "asset": trade.asset,
                "direction": trade.direction,
                "outcome": trade.outcome,
                "profit": trade.profit,
                "amount": trade.amount,
                "session_id": trade.session_id,
                "expiration_seconds": trade.expiration_seconds,
                "payout_pct": trade.payout_pct,
                "kind": trade.kind.value,
                "simulated_profit": trade.simulated_profit,
            },
        )

    async def execute_trade(self, broker_type: BrokerType, request: TradeExecutionRequest) -> Dict[str, Any]:
        """Execute a trade securely mapping it to the broker adapter"""
        adapter = BrokerRegistry.get_adapter(broker_type, account_key=request.account_key)
        trade_kind = self._resolve_trade_kind(request)
        session = adapter.session_manager.snapshot()

        if trade_kind == TradeKind.GHOST:
            entry_price = self._latest_logged_price(request.asset_id)
            payout_pct = self._resolve_payout_pct(adapter, request.asset_id)
            trade_record = TradeRecord(
                session_id=request.session_id or session.session_id or "ghost-session",
                asset=request.asset_id,
                direction=request.direction,
                amount=request.amount,
                expiration_seconds=request.expiration,
                broker=broker_type.value,
                kind=TradeKind.GHOST,
                success=True,
                message="Ghost trade submitted successfully.",
                trade_id=f"ghost-{uuid4().hex[:12]}",
                entry_price=entry_price,
                entry_time=unix_time(),
                payout_pct=payout_pct,
                confidence=request.confidence,
                oteo_score=request.oteo_score,
                base_oteo_score=request.base_oteo_score,
                level2_score_adjustment=request.level2_score_adjustment,
                strategy_level=request.strategy_level,
                trigger_mode=request.trigger_mode,
                manipulation_at_entry=request.manipulation_at_entry,
                entry_context=request.entry_context,
                simulated_amount=request.amount,
            )
            await self.repository.write_trade(trade_record)
            asyncio.create_task(self._track_ghost_trade_outcome(trade_record, request.expiration))
            return {
                "success": True,
                "message": trade_record.message,
                "trade_id": trade_record.trade_id,
                "entry_price": trade_record.entry_price,
                "session_id": trade_record.session_id,
                "connection_status": adapter.get_connection_status(),
                "trade_mode": trade_kind.value,
            }
        
        order = TradeOrder(
            asset_id=request.asset_id,
            direction=request.direction,
            amount=request.amount,
            expiration=request.expiration,
            broker=broker_type,
        )

        result = await adapter.execute_trade(order)

        if not result.success:
            return {
                "success": False,
                "message": result.message,
                "trade_id": result.trade_id,
                "entry_price": result.entry_price,
                "session_id": session.session_id,
                "connection_status": adapter.get_connection_status(),
                "trade_mode": trade_kind.value,
            }

        trade_record = TradeRecord(
            session_id=request.session_id or session.session_id or 'unknown',
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
            payout_pct=self._resolve_payout_pct(adapter, request.asset_id),
            confidence=request.confidence,
            oteo_score=request.oteo_score,
            base_oteo_score=request.base_oteo_score,
            level2_score_adjustment=request.level2_score_adjustment,
            strategy_level=request.strategy_level,
            trigger_mode=request.trigger_mode,
            manipulation_at_entry=request.manipulation_at_entry,
            entry_context=request.entry_context,
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
            "connection_status": adapter.get_connection_status(),
            "trade_mode": trade_kind.value,
        }

    async def _track_ghost_trade_outcome(self, trade: TradeRecord, expiration: int) -> None:
        await asyncio.sleep(expiration + 1)

        try:
            trade.exit_time = unix_time()
            trade.exit_price = self._latest_logged_price(trade.asset)

            if trade.entry_price is None or trade.exit_price is None:
                trade.outcome = "void"
                trade.profit = 0.0
                trade.simulated_profit = 0.0
            else:
                if trade.direction.lower() == "call":
                    outcome = "win" if trade.exit_price > trade.entry_price else "loss" if trade.exit_price < trade.entry_price else "void"
                else:
                    outcome = "win" if trade.exit_price < trade.entry_price else "loss" if trade.exit_price > trade.entry_price else "void"

                trade.outcome = outcome
                if outcome == "win":
                    payout_pct = float(trade.payout_pct or 80.0)
                    profit = float(trade.amount) * (payout_pct / 100.0)
                elif outcome == "loss":
                    profit = -float(trade.amount)
                else:
                    profit = 0.0
                trade.profit = profit
                trade.simulated_profit = profit

            await self.repository.update_trade(trade)
            await self._emit_trade_result(trade)
            logger.info(
                "Ghost trade %s tracked. Outcome: %s, Profit: %s",
                trade.trade_id, trade.outcome, trade.profit
            )
        except Exception as exc:
            logger.error("Error checking ghost trade outcome for %s: %s", trade.trade_id, exc)

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
            loop = asyncio.get_running_loop()
            outcome_data = await loop.run_in_executor(None, session.check_win, trade.trade_id)

            if outcome_data is None:
                logger.warning("Could not retrieve outcome for trade %s", trade.trade_id)
                return

            trade.exit_time = unix_time()

            # Fix #2: Structured outcome parsing with explicit type checks.
            if isinstance(outcome_data, tuple) and len(outcome_data) >= 2:
                raw_profit, raw_outcome = outcome_data[0], outcome_data[1]
                trade.profit = float(raw_profit) if raw_profit is not None else 0.0
                if isinstance(raw_outcome, str) and raw_outcome.strip():
                    normalized_outcome = raw_outcome.strip().lower()
                    trade.outcome = "loss" if normalized_outcome == "loose" else normalized_outcome
                else:
                    trade.outcome = "win" if trade.profit > 0 else "loss"
            elif isinstance(outcome_data, dict):
                raw_outcome = outcome_data.get("result")
                if raw_outcome is None and "win" in outcome_data:
                    raw_outcome = outcome_data.get("win")

                if isinstance(raw_outcome, bool):
                    trade.outcome = "win" if raw_outcome else "loss"
                elif isinstance(raw_outcome, (int, float)):
                    trade.outcome = "win" if float(raw_outcome) > 0 else "loss"
                elif isinstance(raw_outcome, str) and raw_outcome.strip():
                    normalized_outcome = raw_outcome.strip().lower()
                    trade.outcome = "loss" if normalized_outcome == "loose" else normalized_outcome
                elif outcome_data.get("profit") is not None:
                    trade.outcome = "win" if float(outcome_data.get("profit", 0) or 0) > 0 else "loss"
                else:
                    trade.outcome = "unknown"

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
            await self._emit_trade_result(trade)
            logger.info(
                "Trade %s tracked. Outcome: %s, Profit: %s",
                trade.trade_id, trade.outcome, trade.profit
            )

        except Exception as e:
            logger.error("Error checking trade outcome for %s: %s", trade.trade_id, e)
