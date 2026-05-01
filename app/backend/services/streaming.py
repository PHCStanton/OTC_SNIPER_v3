"""
Streaming Service — OTC SNIPER v3
Orchestrates live market data enrichment and real-time emissions.
"""
import logging
import time
from typing import Dict, Any

from .auto_ghost import AutoGhostService
from .market_context import MarketContextEngine, Level2Config, apply_level2_policy, apply_level3_policy
from .oteo import OTEO, OTEOConfig
from .manipulation import ManipulationDetector
from .regime_classifier import RegimeClassifier
from .trade_service import TradeService
from .tick_logger import TickLogger
from .signal_logger import SignalLogger
from ..brokers.base import BrokerType
from ..brokers.registry import BrokerRegistry
from ..config import get_settings
from ..dependencies import get_data_repository

logger = logging.getLogger(__name__)

class StreamingService:
    """
    Manages per-asset analysis engines and routes data to Socket.IO.
    """

    PAYOUT_CACHE_TTL_SECONDS = 60.0

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
        self.trade_service.set_auto_ghost(self.auto_ghost)
        
        self._oteo_engines: Dict[str, OTEO] = {}
        self._market_context_engines: Dict[str, MarketContextEngine] = {}
        self._manip_engines: Dict[str, ManipulationDetector] = {}
        self._regime_classifiers: Dict[str, RegimeClassifier] = {}
        self._last_regime: Dict[str, dict[str, Any]] = {}
        self._tick_counts: Dict[str, int] = {}
        self._allowed_assets: set[str] = set()
        self._streaming_active: bool = False
        self._payout_cache: Dict[str, tuple[float, float]] = {}

    def _clear_level3_state(self, *, reset_classifiers: bool) -> None:
        """Clear cached Level 3 regime state."""
        self._last_regime.clear()
        if reset_classifiers:
            self._regime_classifiers.clear()

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
        auto_ghost_max_session_trades: int | None = None,
        auto_ghost_max_drawdown_amount: float | None = None,
        auto_ghost_drawdown_cooldown_seconds: int | None = None,
        auto_ghost_minimum_payout_pct: float | None = None,
    ) -> dict[str, Any]:
        previous_level3_enabled = self.level3_enabled
        if level2_enabled is not None:
            self.level2_enabled = bool(level2_enabled)
        if level3_enabled is not None:
            self.level3_enabled = bool(level3_enabled) and self.level2_enabled
            if previous_level3_enabled and not self.level3_enabled:
                self._clear_level3_state(reset_classifiers=False)
            elif not previous_level3_enabled and self.level3_enabled:
                self._clear_level3_state(reset_classifiers=True)
        auto_ghost_status = self.auto_ghost.update_config(
            enabled=auto_ghost_enabled,
            amount=auto_ghost_amount,
            expiration_seconds=auto_ghost_expiration_seconds,
            max_concurrent_trades=auto_ghost_max_concurrent_trades,
            per_asset_cooldown_seconds=auto_ghost_per_asset_cooldown_seconds,
            minimum_payout_pct=auto_ghost_minimum_payout_pct,
            max_session_trades=auto_ghost_max_session_trades,
            max_drawdown_amount=auto_ghost_max_drawdown_amount,
            drawdown_cooldown_seconds=auto_ghost_drawdown_cooldown_seconds,
        )
        return {
            "oteo_level2_enabled": self.level2_enabled,
            "oteo_level3_enabled": self.level3_enabled,
            **auto_ghost_status,
        }

    def update_allowed_assets(self, assets: list[str]) -> None:
        cleaned = [a.strip() for a in (assets or []) if isinstance(a, str) and a.strip()]
        new_set = set(cleaned)
        removed = self._allowed_assets - new_set

        for asset in removed:
            self._oteo_engines.pop(asset, None)
            self._market_context_engines.pop(asset, None)
            self._manip_engines.pop(asset, None)
            self._regime_classifiers.pop(asset, None)
            self._last_regime.pop(asset, None)
            self._tick_counts.pop(asset, None)
            self._payout_cache.pop(asset, None)
            logger.info("Cleaned up engines for removed asset: %s", asset)

        self._allowed_assets = new_set
        logger.info("Allowed assets updated (%d): %s", len(new_set), sorted(new_set))

    def start(self) -> None:
        self._streaming_active = True
        logger.info("StreamingService started — tick processing enabled")

    def stop(self) -> None:
        self._streaming_active = False
        self._allowed_assets.clear()
        self._oteo_engines.clear()
        self._market_context_engines.clear()
        self._manip_engines.clear()
        self._clear_level3_state(reset_classifiers=True)
        self._tick_counts.clear()
        self._payout_cache.clear()
        logger.info("StreamingService stopped — all engines cleared")

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

        if asset not in self._regime_classifiers:
            self._regime_classifiers[asset] = RegimeClassifier()
            
        return self._oteo_engines[asset], self._market_context_engines[asset], self._manip_engines[asset]

    def _resolve_asset_payout_pct(self, asset: str) -> float:
        now = time.time()
        cached = self._payout_cache.get(asset)
        if cached and (now - cached[1]) < self.PAYOUT_CACHE_TTL_SECONDS:
            return cached[0]

        try:
            adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_key="primary")
            payout_pct = float(self.trade_service._resolve_payout_pct(adapter, asset))
            self._payout_cache[asset] = (payout_pct, now)
            return payout_pct
        except Exception as exc:
            logger.debug("Failed to resolve payout for %s: %s", asset, exc)
            return 0.0

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
        if not self._streaming_active:
            return
        if asset not in self._allowed_assets:
            return

        oteo, market_context_engine, manip_detector = self._get_or_create_engines(asset)
        
        oteo_result = oteo.update_tick(price, timestamp=timestamp)
        market_context = market_context_engine.update_tick(price, timestamp=timestamp)
        manipulation = manip_detector.update(timestamp, price)
        regime = None

        if self.level3_enabled:
            candle_closed = bool(market_context.get("candle_closed", False))
            if candle_closed and market_context.get("ready"):
                classifier = self._regime_classifiers.get(asset)
                if classifier is not None:
                    regime = classifier.classify(market_context)
                    self._last_regime[asset] = regime
            if regime is None:
                regime = self._last_regime.get(asset)
        
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
            enriched_result["level2_enabled"] = self.level2_enabled
            enriched_result["level3_enabled"] = self.level3_enabled
            if self.level3_enabled and regime is not None:
                enriched_result["regime"] = regime
                enriched_result = apply_level3_policy(enriched_result, market_context, regime)
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
                "level3_enabled": enriched_result["level3_enabled"],
                "level2_score_adjustment": enriched_result["level2_score_adjustment"],
                "level2_suppressed_reason": enriched_result["level2_suppressed_reason"],
                "level3_score_adjustment": enriched_result.get("level3_score_adjustment", 0.0),
                "level3_suppressed_reason": enriched_result.get("level3_suppressed_reason"),
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
                "level3_enabled": self.level3_enabled,
                "level3_score_adjustment": 0.0,
                "level3_suppressed_reason": None,
                "market_context": market_context,
            })

        if self.level3_enabled and regime is not None:
            payload.update({
                "regime_label": regime["regime_label"],
                "regime_confidence": regime["regime_confidence"],
                "regime_stable": regime["regime_stable"],
                "regime_detail": regime["regime_detail"],
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
                "level3_score_adjustment": oteo_result.get("level3_score_adjustment"),
                "level3_suppressed_reason": oteo_result.get("level3_suppressed_reason"),
                "regime_label": oteo_result.get("regime_label"),
                "regime_confidence": oteo_result.get("regime_confidence"),
                "regime_stable": oteo_result.get("regime_stable"),
                "market_context": oteo_result["market_context"],
                "manip": bool(manipulation),
                "broker": source
            })
            payout_pct = self._resolve_asset_payout_pct(asset)
            await self.auto_ghost.consider_signal(
                asset=asset,
                price=price,
                timestamp=timestamp,
                oteo_result=oteo_result,
                manipulation=manipulation,
                payout_pct=payout_pct,
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
