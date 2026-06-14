"""
Streaming Service — OTC SNIPER v3
Orchestrates live market data enrichment and real-time emissions.
"""
import logging
import time
import asyncio
from typing import Dict, Any

from .perf_monitor import PerformanceMonitor

from .ai_review import AIReviewService
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
        self.oteo_ai_enabled = False
        self.oteo_ai_execution_mode = "advisory"
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
        
        # Telemetry and Bounded Queue (Phase 0/1)
        self.perf_monitor = PerformanceMonitor(sio_server)
        self._tick_queue = asyncio.Queue(maxsize=500)
        self.perf_monitor.set_queue(self._tick_queue)
        self._loop = None
        self._consumer_task = None
        # Phase 4: AI Review Service (attached externally when AI is enabled)
        self._ai_review: AIReviewService | None = None

    def _clear_level3_state(self, *, reset_classifiers: bool) -> None:
        """Clear cached Level 3 regime state."""
        self._last_regime.clear()
        if reset_classifiers:
            self._regime_classifiers.clear()
        ai_review = getattr(self, "_ai_review", None)
        if ai_review:
            ai_review.clear_all()

    def attach_ai_review(self, ai_service: object, interval: int = 300) -> None:
        """
        Attach the AI Review Service to the streaming pipeline.
        Called from main.py during app startup when AI is enabled.
        """
        self._ai_review = AIReviewService(ai_service, interval_seconds=interval)  # type: ignore[arg-type]
        logger.info("AI Review Service attached (interval: %ds)", interval)

    def update_runtime_settings(
        self,
        *,
        level2_enabled: bool | None = None,
        level3_enabled: bool | None = None,
        oteo_ai_enabled: bool | None = None,
        oteo_ai_execution_mode: str | None = None,
        auto_ghost_enabled: bool | None = None,
        auto_ghost_amount: float | None = None,
        auto_ghost_expiration_seconds: int | None = None,
        auto_ghost_max_concurrent_trades: int | None = None,
        auto_ghost_per_asset_cooldown_seconds: int | None = None,
        auto_ghost_max_session_trades: int | None = None,
        auto_ghost_max_drawdown_amount: float | None = None,
        auto_ghost_drawdown_cooldown_seconds: int | None = None,
        auto_ghost_minimum_payout_pct: float | None = None,
        auto_ghost_manipulation_severity_threshold: float | None = None,
        auto_ghost_block_on_manipulation: bool | None = None,
        auto_ghost_min_confidence_enabled: bool | None = None,
        auto_ghost_min_confidence: float | None = None,
        auto_ghost_max_confidence_enabled: bool | None = None,
        auto_ghost_max_confidence: float | None = None,
        auto_ghost_max_trades_per_timeframe: int | None = None,
        auto_ghost_timeframe_seconds: int | None = None,
        auto_ghost_min_zscore_enabled: bool | None = None,
        auto_ghost_min_zscore: float | None = None,
        auto_ghost_max_zscore_enabled: bool | None = None,
        auto_ghost_max_zscore: float | None = None,
        auto_ghost_allowed_regimes: list[str] | None = None,
        auto_ghost_require_regime_stable: bool | None = None,
    ) -> dict[str, Any]:
        previous_level3_enabled = self.level3_enabled
        if level2_enabled is not None:
            self.level2_enabled = bool(level2_enabled)
        if level3_enabled is not None:
            self.level3_enabled = bool(level3_enabled) and self.level2_enabled
        if oteo_ai_enabled is not None:
            self.oteo_ai_enabled = bool(oteo_ai_enabled)
        elif not hasattr(self, "oteo_ai_enabled"):
            self.oteo_ai_enabled = False
        if oteo_ai_execution_mode is not None:
            self.oteo_ai_execution_mode = str(oteo_ai_execution_mode)
        elif not hasattr(self, "oteo_ai_execution_mode"):
            self.oteo_ai_execution_mode = "advisory"
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
            manipulation_severity_threshold=auto_ghost_manipulation_severity_threshold,
            block_on_manipulation=auto_ghost_block_on_manipulation,
            min_confidence_enabled=auto_ghost_min_confidence_enabled,
            min_confidence=auto_ghost_min_confidence,
            max_confidence_enabled=auto_ghost_max_confidence_enabled,
            max_confidence=auto_ghost_max_confidence,
            max_trades_per_timeframe=auto_ghost_max_trades_per_timeframe,
            timeframe_seconds=auto_ghost_timeframe_seconds,
            min_zscore_enabled=auto_ghost_min_zscore_enabled,
            min_zscore=auto_ghost_min_zscore,
            max_zscore_enabled=auto_ghost_max_zscore_enabled,
            max_zscore=auto_ghost_max_zscore,
            allowed_regimes=auto_ghost_allowed_regimes,
            require_regime_stable=auto_ghost_require_regime_stable,
            oteo_ai_enabled=self.oteo_ai_enabled,
            oteo_ai_execution_mode=self.oteo_ai_execution_mode,
        )
        return {
            "oteo_level2_enabled": self.level2_enabled,
            "oteo_level3_enabled": self.level3_enabled,
            "oteo_ai_enabled": self.oteo_ai_enabled,
            "oteo_ai_execution_mode": self.oteo_ai_execution_mode,
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
            if self._ai_review:
                self._ai_review.clear_asset(asset)
            logger.info("Cleaned up engines for removed asset: %s", asset)

        self._allowed_assets = new_set
        logger.info("Allowed assets updated (%d): %s", len(new_set), sorted(new_set))

    def start(self) -> None:
        self._streaming_active = True
        self._loop = asyncio.get_running_loop()
        self.perf_monitor.start()
        self.tick_logger.start()
        self._consumer_task = asyncio.create_task(self._tick_consumer_loop())
        if self.level3_enabled and self._ai_review:
            self._ai_review.start()
        logger.info("StreamingService started — tick processing enabled")

    def stop(self) -> None:
        self._streaming_active = False
        self.perf_monitor.stop()
        self.tick_logger.stop()
        if self._consumer_task:
            self._consumer_task.cancel()
            self._consumer_task = None
        if self._ai_review:
            self._ai_review.stop()
            self._ai_review.clear_all()
        
        # Drain the queue
        while not self._tick_queue.empty():
            try:
                self._tick_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
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

    def process_tick(self, asset: str, price: float, timestamp: float, source: str = "pocket_option") -> None:
        """
        Main entry point for incoming ticks from the broker thread.
        Pushes the tick to the internal asyncio Queue thread-safely.
        """
        if not self._streaming_active:
            return
        if asset not in self._allowed_assets:
            return

        loop = self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(self._enqueue_tick_inner, asset, price, timestamp, source)

    def _enqueue_tick_inner(self, asset: str, price: float, timestamp: float, source: str) -> None:
        if self._tick_queue.full():
            try:
                self._tick_queue.get_nowait()
                self.perf_monitor.record_drop()
            except asyncio.QueueEmpty:
                pass
        
        try:
            self._tick_queue.put_nowait((asset, price, timestamp, source))
        except Exception as e:
            logger.error("Failed to enqueue tick for %s: %s", asset, e)

    async def _tick_consumer_loop(self):
        """Background loop consuming ticks from the queue and processing them."""
        while self._streaming_active:
            try:
                tick = await self._tick_queue.get()
                asset, price, timestamp, source = tick
                
                start_time = time.time()
                try:
                    await self._process_tick_inner(asset, price, timestamp, source)
                except Exception as proc_err:
                    logger.error("Error processing tick for %s: %s", asset, proc_err)
                
                duration = time.time() - start_time
                self.perf_monitor.record_tick(duration)
                
                self._tick_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                logger.error("Error in tick consumer loop: %s", loop_err)
                await asyncio.sleep(0.01)

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
            enriched_result["oteo_ai_enabled"] = self.oteo_ai_enabled
            enriched_result["oteo_ai_execution_mode"] = self.oteo_ai_execution_mode
            if self.level3_enabled and regime is not None:
                enriched_result["regime"] = regime
                enriched_result = apply_level3_policy(enriched_result, market_context, regime)
            
            # Apply manipulation severity penalty to OTEO score
            if manipulation:
                max_severity = max(manipulation.values()) if manipulation.values() else 0.0
                if max_severity > 0.0:
                    penalty = max_severity * 20.0
                    enriched_result["oteo_score"] = round(max(0.0, enriched_result["oteo_score"] - penalty), 1)
                    
                    # Dynamic confidence / actionability downgrade
                    if enriched_result["oteo_score"] <= 55.0:  # min actionable floor
                        enriched_result["confidence"] = "LOW"
                        enriched_result["actionable"] = False
                    elif enriched_result["oteo_score"] < 70.0 and enriched_result["confidence"] == "HIGH":
                        enriched_result["confidence"] = "MEDIUM"
                        
                    enriched_result["manipulation_penalty"] = round(penalty, 1)
 
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
                "oteo_ai_enabled": enriched_result["oteo_ai_enabled"],
                "oteo_ai_execution_mode": enriched_result["oteo_ai_execution_mode"],
                "level2_score_adjustment": enriched_result["level2_score_adjustment"],
                "level2_suppressed_reason": enriched_result["level2_suppressed_reason"],
                "level3_score_adjustment": enriched_result.get("level3_score_adjustment", 0.0),
                "level3_suppressed_reason": enriched_result.get("level3_suppressed_reason"),
                "manipulation_penalty": enriched_result.get("manipulation_penalty", 0.0),
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
                "oteo_ai_enabled": self.oteo_ai_enabled,
                "oteo_ai_execution_mode": self.oteo_ai_execution_mode,
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

        if self.sio:
            room = f"market_data:{asset}"
            await self.sio.emit("market_data", payload, room=room)
            self.perf_monitor.record_emit()
            
            # Emit warmup status
            self._tick_counts[asset] += 1
            count = self._tick_counts[asset]
            if count % 10 == 0 or count == 50:
                await self.sio.emit("warmup_status", {
                    "asset": asset,
                    "ready": count >= 50,
                    "ticks_received": count
                }, room=room)

        # Asynchronously write to tick log and process signals (post-emit)
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
                "oteo_ai_enabled": oteo_result.get("oteo_ai_enabled", False),
                "regime_label": oteo_result.get("regime_label"),
                "regime_confidence": oteo_result.get("regime_confidence"),
                "regime_stable": oteo_result.get("regime_stable"),
                "market_context": oteo_result["market_context"],
                "manip": bool(manipulation),
                "manipulation_penalty": oteo_result.get("manipulation_penalty", 0.0),
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

            # Phase 4: Push snapshot to AI review loop when regime data is available
            if self.level3_enabled and self._ai_review and regime is not None:
                mc = oteo_result.get("market_context") or {}
                di_spread = abs(float(mc.get("plus_di") or 0.0) - float(mc.get("minus_di") or 0.0))
                ag_status = self.auto_ghost.status
                self._ai_review.push_snapshot(asset, {
                    "asset": asset,
                    "regime_label": regime.get("regime_label"),
                    "regime_confidence": regime.get("regime_confidence"),
                    "regime_stable": regime.get("regime_stable"),
                    "regime_persistence": regime.get("regime_persistence"),
                    "regime_prior": regime.get("regime_prior"),
                    "regime_detail": regime.get("regime_detail"),
                    "adx": mc.get("adx"),
                    "adx_slope": mc.get("adx_slope"),
                    "di_spread": round(di_spread, 1),
                    "cci": mc.get("cci"),
                    "cci_state": mc.get("cci_state"),
                    "cci_divergence": mc.get("cci_divergence"),
                    "atr": mc.get("atr"),
                    "nearest_structure_atr": mc.get("nearest_structure_atr"),
                    "tick_health": mc.get("tick_health"),
                    "tick_frequency": mc.get("tick_frequency"),
                    "manipulation": manipulation,
                    "recent_win_rate": ag_status.get("auto_ghost_session_wins", 0) / max(1, ag_status.get("auto_ghost_session_trades", 1)) * 100.0,
                    "recent_trade_count": ag_status.get("auto_ghost_session_trades", 0),
                    "session_pnl": ag_status.get("auto_ghost_session_pnl", 0.0),
                    "condition_stats": self.auto_ghost.get_condition_stats(),
                })

    def clear_detector_buffers(self, asset: str) -> None:
        """Clear manipulation detector buffers (used on focus switch)."""
        if asset in self._manip_engines:
            self._manip_engines[asset].velocities.clear()
            self._manip_engines[asset].price_history.clear()
            logger.debug("Cleared detector buffers for %s", asset)
