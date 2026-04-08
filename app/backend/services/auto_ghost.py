from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import time as unix_time
from typing import Any

from ..brokers.base import BrokerType
from ..models.requests import TradeExecutionRequest
from .trade_service import TradeService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AutoGhostConfig:
    enabled: bool = False
    amount: float = 1.0
    expiration_seconds: int = 60
    max_concurrent_trades: int = 3
    per_asset_cooldown_seconds: int = 30
    block_on_manipulation: bool = True
    max_session_trades: int = 100
    max_drawdown_amount: float = 0.0
    drawdown_cooldown_seconds: int = 300


class AutoGhostService:
    def __init__(self, trade_service: TradeService, config: AutoGhostConfig | None = None):
        self.trade_service = trade_service
        self.config = config or AutoGhostConfig()
        self._active_assets: set[str] = set()
        self._cooldown_until: dict[str, float] = {}
        self._session_id: str | None = None
        self._session_pnl: float = 0.0
        self._session_trade_count: int = 0
        self._session_wins: int = 0
        self._session_losses: int = 0
        self._drawdown_cooldown_until: float = 0.0
        self._session_halted: bool = False

    def update_config(
        self,
        *,
        enabled: bool | None = None,
        amount: float | None = None,
        expiration_seconds: int | None = None,
        max_concurrent_trades: int | None = None,
        per_asset_cooldown_seconds: int | None = None,
        max_session_trades: int | None = None,
        max_drawdown_amount: float | None = None,
        drawdown_cooldown_seconds: int | None = None,
    ) -> dict[str, Any]:
        previous_enabled = self.config.enabled
        self.config = AutoGhostConfig(
            enabled=self.config.enabled if enabled is None else bool(enabled),
            amount=self.config.amount if amount is None else max(0.1, float(amount)),
            expiration_seconds=self.config.expiration_seconds if expiration_seconds is None else max(5, int(expiration_seconds)),
            max_concurrent_trades=self.config.max_concurrent_trades if max_concurrent_trades is None else max(1, int(max_concurrent_trades)),
            per_asset_cooldown_seconds=(
                self.config.per_asset_cooldown_seconds
                if per_asset_cooldown_seconds is None
                else max(0, int(per_asset_cooldown_seconds))
            ),
            block_on_manipulation=self.config.block_on_manipulation,
            max_session_trades=self.config.max_session_trades if max_session_trades is None else max(1, int(max_session_trades)),
            max_drawdown_amount=self.config.max_drawdown_amount if max_drawdown_amount is None else max(0.0, float(max_drawdown_amount)),
            drawdown_cooldown_seconds=self.config.drawdown_cooldown_seconds if drawdown_cooldown_seconds is None else max(0, int(drawdown_cooldown_seconds)),
        )
        if self.config.enabled and (not previous_enabled or not self._session_id):
            self._session_id = f"auto_ghost_{int(unix_time())}"
            self._session_pnl = 0.0
            self._session_trade_count = 0
            self._session_wins = 0
            self._session_losses = 0
            self._session_halted = False
            logger.info("Started Auto-Ghost session %s", self._session_id)
        return self.status

    @property
    def status(self) -> dict[str, Any]:
        return {
            "auto_ghost_enabled": self.config.enabled,
            "auto_ghost_amount": self.config.amount,
            "auto_ghost_expiration_seconds": self.config.expiration_seconds,
            "auto_ghost_max_concurrent_trades": self.config.max_concurrent_trades,
            "auto_ghost_per_asset_cooldown_seconds": self.config.per_asset_cooldown_seconds,
            "auto_ghost_active_trades": len(self._active_assets),
            "auto_ghost_session_id": self._session_id,
            "auto_ghost_session_pnl": self._session_pnl,
            "auto_ghost_session_trades": self._session_trade_count,
            "auto_ghost_session_wins": self._session_wins,
            "auto_ghost_session_losses": self._session_losses,
            "auto_ghost_drawdown_cooldown_active": unix_time() < self._drawdown_cooldown_until,
            "auto_ghost_session_halted": self._session_halted,
        }

    def report_outcome(self, trade_id: str, outcome: str, profit: float) -> None:
        self._session_trade_count += 1
        self._session_pnl += profit
        if outcome == "win":
            self._session_wins += 1
        elif outcome == "loss":
            self._session_losses += 1

        if self.config.max_drawdown_amount > 0 and self._session_pnl <= -abs(self.config.max_drawdown_amount):
            self._drawdown_cooldown_until = unix_time() + self.config.drawdown_cooldown_seconds
            logger.warning("Ghost session drawdown limit hit (%.2f <= -%.2f). Cooling down for %ds.",
                           self._session_pnl, self.config.max_drawdown_amount, self.config.drawdown_cooldown_seconds)

    async def consider_signal(
        self,
        *,
        asset: str,
        price: float,
        timestamp: float,
        oteo_result: dict[str, Any],
        manipulation: dict[str, Any],
    ) -> dict[str, Any] | None:
        # Clean up any stale active assets whose cooldown has already expired
        now = unix_time()
        stale = [a for a in self._active_assets if now >= self._cooldown_until.get(a, 0)]
        for a in stale:
            self._active_assets.discard(a)
            logger.info("Cleaned up stale active asset: %s", a)

        if not self.config.enabled:
            return None
            
        if self._session_halted:
            return None
        if self._session_trade_count >= self.config.max_session_trades:
            return None
        if now < self._drawdown_cooldown_until:
            return None
        if oteo_result.get("recommended") not in {"CALL", "PUT"}:
            return None
        if not oteo_result.get("actionable"):
            return None
        if self.config.block_on_manipulation and manipulation:
            return None
        if asset in self._active_assets:
            return None
        if len(self._active_assets) >= self.config.max_concurrent_trades:
            return None
        if unix_time() < self._cooldown_until.get(asset, 0):
            return None

        entry_context = {
            "asset": asset,
            "price": price,
            "timestamp": timestamp,
            "recommended": oteo_result.get("recommended"),
            "confidence": oteo_result.get("confidence"),
            "oteo_score": oteo_result.get("oteo_score"),
            "base_oteo_score": oteo_result.get("base_oteo_score"),
            "base_confidence": oteo_result.get("base_confidence"),
            "pressure_pct": oteo_result.get("pressure_pct"),
            "velocity": oteo_result.get("velocity"),
            "z_score": oteo_result.get("z_score"),
            "slow_velocity": oteo_result.get("slow_velocity"),
            "stretch_alignment": oteo_result.get("stretch_alignment"),
            "level2_enabled": oteo_result.get("level2_enabled"),
            "level2_score_adjustment": oteo_result.get("level2_score_adjustment"),
            "level2_suppressed_reason": oteo_result.get("level2_suppressed_reason"),
            "market_context": oteo_result.get("market_context"),
            "manipulation": manipulation,
        }

        request = TradeExecutionRequest(
            asset_id=asset,
            direction=str(oteo_result["recommended"]).lower(),
            amount=self.config.amount,
            expiration=self.config.expiration_seconds,
            account_key="primary",
            trade_mode="ghost",
            session_id=self._session_id,
            confidence=oteo_result.get("confidence"),
            oteo_score=oteo_result.get("oteo_score"),
            base_oteo_score=oteo_result.get("base_oteo_score"),
            level2_score_adjustment=oteo_result.get("level2_score_adjustment"),
            strategy_level="level3" if oteo_result.get("level3_enabled") else "level2" if oteo_result.get("level2_enabled") else "level1",
            manipulation_at_entry=manipulation or None,
            entry_context=entry_context,
            trigger_mode="auto_ghost",
        )

        result = await self.trade_service.execute_trade(BrokerType.POCKET_OPTION, request)
        if not result.get("success"):
            logger.warning("Auto-Ghost failed for %s: %s", asset, result.get("message"))
            return result

        self._active_assets.add(asset)
        self._cooldown_until[asset] = unix_time() + self.config.expiration_seconds + self.config.per_asset_cooldown_seconds
        task = asyncio.create_task(self._release_asset(asset, self.config.expiration_seconds + 1))
        task.add_done_callback(lambda t: logger.error("_release_asset failed: %s", t.exception()) if not t.cancelled() and t.exception() else None)
        logger.info(
            "Auto-Ghost trade opened for %s (%s, %ss)",
            asset,
            oteo_result.get("recommended"),
            self.config.expiration_seconds,
        )
        return result

    async def _release_asset(self, asset: str, delay_seconds: int) -> None:
        await asyncio.sleep(max(1, delay_seconds))
        self._active_assets.discard(asset)
