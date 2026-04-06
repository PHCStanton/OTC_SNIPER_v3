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


class AutoGhostService:
    def __init__(self, trade_service: TradeService, config: AutoGhostConfig | None = None):
        self.trade_service = trade_service
        self.config = config or AutoGhostConfig()
        self._active_assets: set[str] = set()
        self._cooldown_until: dict[str, float] = {}
        self._session_id: str | None = None

    def update_config(
        self,
        *,
        enabled: bool | None = None,
        amount: float | None = None,
        expiration_seconds: int | None = None,
        max_concurrent_trades: int | None = None,
        per_asset_cooldown_seconds: int | None = None,
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
        )
        if self.config.enabled and (not previous_enabled or not self._session_id):
            self._session_id = f"auto_ghost_{int(unix_time())}"
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
        }

    async def consider_signal(
        self,
        *,
        asset: str,
        price: float,
        timestamp: float,
        oteo_result: dict[str, Any],
        manipulation: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.config.enabled:
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
        asyncio.create_task(self._release_asset(asset, self.config.expiration_seconds + 1))
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
