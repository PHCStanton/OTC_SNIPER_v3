"""
Streaming Service — OTC SNIPER v3
Orchestrates live market data enrichment and real-time emissions.
"""
import logging
from typing import Dict, Any

from .auto_ghost import AutoGhostService
from .market_context import MarketContextEngine, Level2Config, apply_level2_policy
from .oteo import OTEO, OTEOConfig
from .manipulation import ManipulationDetector
from .trade_service import TradeService
from .tick_logger import TickLogger
from .signal_logger import SignalLogger
from ..config import get_settings
from ..dependencies import get_data_repository

logger = logging.getLogger(__name__)

class StreamingService:
    """
    Manages per-asset analysis engines and routes data to Socket.IO.
    """

    def __init__(self, sio_server=None):
        self.sio = sio_server
        settings = get_settings()
        self.tick_logger = TickLogger(settings.data_dir / "tick_logs")
        self.signal_logger = SignalLogger(settings.data_dir / "signals")
        self.oteo_config = OTEOConfig()
        self.level2_config = Level2Config()
        self.level2_enabled = False
        self.level3_enabled = False
        self.trade_service = TradeService(repository=get_data_repository(), sio=sio_server)
        self.auto_ghost = AutoGhostService(self.trade_service)
        
        self._oteo_engines: Dict[str, OTEO] = {}
        self._market_context_engines: Dict[str, MarketContextEngine] = {}
        self._manip_engines: Dict[str, ManipulationDetector] = {}
        self._tick_counts: Dict[str, int] = {}

    def update_runtime_settings(
        self,
        *,
        level2_enabled: bool | None = None,
        level3_enabled: bool | None = None,
        auto_ghost_enabled: bool | None = None,
        auto_ghost_amount: float | None = None,
        auto_ghost_expiration_seconds: int | None = None,
        auto_ghost_max_concurrent_trades: int | None = None,
        auto_ghost_per_asset_cooldown_seconds: int | None = None,
    ) -> dict[str, Any]:
        if level2_enabled is not None:
            self.level2_enabled = bool(level2_enabled)
        if level3_enabled is not None:
            self.level3_enabled = bool(level3_enabled) and self.level2_enabled
        auto_ghost_status = self.auto_ghost.update_config(
            enabled=auto_ghost_enabled,
            amount=auto_ghost_amount,
            expiration_seconds=auto_ghost_expiration_seconds,
            max_concurrent_trades=auto_ghost_max_concurrent_trades,
            per_asset_cooldown_seconds=auto_ghost_per_asset_cooldown_seconds,
        )
        return {
            "oteo_level2_enabled": self.level2_enabled,
            "oteo_level3_enabled": self.level3_enabled,
            **auto_ghost_status,
        }

    def _get_or_create_engines(self, asset: str) -> tuple[OTEO, MarketContextEngine, ManipulationDetector]:
        if asset not in self._oteo_engines:
            logger.info("Initializing engines for asset: %s", asset)
            oteo = OTEO(config=self.oteo_config)
            market_context = MarketContextEngine(config=self.level2_config)
            
            recent_ticks = self.tick_logger.load_recent(asset, max_ticks=300)
            if recent_ticks:
                for tick in recent_ticks:
                    oteo.seed_tick(float(tick["p"]), timestamp=float(tick["t"]))
                    market_context.seed_tick(float(tick["p"]), timestamp=float(tick["t"]))
                logger.info("Pre-seeded OTEO for %s with %d historical ticks", asset, len(recent_ticks))
            
            self._oteo_engines[asset] = oteo
            self._market_context_engines[asset] = market_context
            self._manip_engines[asset] = ManipulationDetector()
            self._tick_counts[asset] = len(recent_ticks)
            
        return self._oteo_engines[asset], self._market_context_engines[asset], self._manip_engines[asset]

    async def process_tick(self, asset: str, price: float, timestamp: float, source: str = "pocket_option") -> None:
        """
        Main entry point for incoming ticks from the broker.
        Enriches, logs, and emits the tick data.
        """
        # Fix #2: Wrap entire body in a top-level handler so errors are visible,
        # not silently dropped in fire-and-forget asyncio.create_task calls.
        try:
            await self._process_tick_inner(asset, price, timestamp, source)
        except Exception as e:
            logger.error("process_tick error for %s @ %.5f: %s", asset, price, e)

    async def _process_tick_inner(self, asset: str, price: float, timestamp: float, source: str) -> None:
        oteo, market_context_engine, manip_detector = self._get_or_create_engines(asset)
        
        oteo_result = oteo.update_tick(price, timestamp=timestamp)
        market_context = market_context_engine.update_tick(price, timestamp=timestamp)
        manipulation = manip_detector.update(timestamp, price)
        
        payload = {
            "asset": asset,
            "price": price,
            "timestamp": timestamp,
            "source": source,
            "manipulation": manipulation
        }
        
        is_warmed_up = isinstance(oteo_result, dict)
        if is_warmed_up:
            enriched_result = apply_level2_policy(oteo_result, market_context, self.level2_enabled)
            payload.update({
                "oteo_score": enriched_result["oteo_score"],
                "recommended": enriched_result["recommended"],
                "confidence": enriched_result["confidence"],
                "maturity": enriched_result["maturity"],
                "velocity": enriched_result["velocity"],
                "pressure_pct": enriched_result["pressure_pct"],
                "z_score": enriched_result["z_score"],
                "slow_velocity": enriched_result["slow_velocity"],
                "trend_aligned": enriched_result["trend_aligned"],
                "actionable": enriched_result["actionable"],
                "stretch_alignment": enriched_result["stretch_alignment"],
                "base_oteo_score": enriched_result["base_oteo_score"],
                "base_confidence": enriched_result["base_confidence"],
                "base_actionable": enriched_result["base_actionable"],
                "level2_enabled": enriched_result["level2_enabled"],
                "level2_score_adjustment": enriched_result["level2_score_adjustment"],
                "level2_suppressed_reason": enriched_result["level2_suppressed_reason"],
                "market_context": enriched_result["market_context"],
            })
            oteo_result = enriched_result
        else:
            payload.update({
                "oteo_score": 50.0,
                "recommended": "NEUTRAL",
                "confidence": "LOW",
                "maturity": 0.0,
                "level2_enabled": self.level2_enabled,
                "market_context": market_context,
            })

        await self.tick_logger.write_tick(asset, {
            "t": timestamp,
            "p": price,
            "a": asset,
            "b": source
        })

        if is_warmed_up and oteo_result["actionable"]:
            await self.signal_logger.log_signal({
                "t": timestamp,
                "asset": asset,
                "score": oteo_result["oteo_score"],
                "dir": oteo_result["recommended"],
                "conf": oteo_result["confidence"],
                "price": price,
                "pressure_pct": oteo_result["pressure_pct"],
                "z_score": oteo_result["z_score"],
                "trend_aligned": oteo_result["trend_aligned"],
                "level2_enabled": oteo_result["level2_enabled"],
                "level2_score_adjustment": oteo_result["level2_score_adjustment"],
                "level2_suppressed_reason": oteo_result["level2_suppressed_reason"],
                "market_context": oteo_result["market_context"],
                "manip": bool(manipulation),
                "broker": source
            })
            await self.auto_ghost.consider_signal(
                asset=asset,
                price=price,
                timestamp=timestamp,
                oteo_result=oteo_result,
                manipulation=manipulation,
            )

        if self.sio:
            room = f"market_data:{asset}"
            await self.sio.emit("market_data", payload, room=room)
            
            # Emit warmup status
            self._tick_counts[asset] += 1
            count = self._tick_counts[asset]
            if count % 10 == 0 or count == 50:
                await self.sio.emit("warmup_status", {
                    "asset": asset,
                    "ready": count >= 50,
                    "ticks_received": count
                }, room=room)

    def clear_detector_buffers(self, asset: str) -> None:
        """Clear manipulation detector buffers (used on focus switch)."""
        if asset in self._manip_engines:
            self._manip_engines[asset].velocities.clear()
            self._manip_engines[asset].price_history.clear()
            logger.debug("Cleared detector buffers for %s", asset)
