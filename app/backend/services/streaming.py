"""
Streaming Service — OTC SNIPER v3
Orchestrates live market data enrichment and real-time emissions.
"""
import logging
import asyncio
from typing import Dict, Any
from pathlib import Path

from .oteo import OTEO
from .manipulation import ManipulationDetector
from .tick_logger import TickLogger
from .signal_logger import SignalLogger
from ..config import get_settings

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
        
        self._oteo_engines: Dict[str, OTEO] = {}
        self._manip_engines: Dict[str, ManipulationDetector] = {}
        self._tick_counts: Dict[str, int] = {}

    def _get_or_create_engines(self, asset: str) -> tuple[OTEO, ManipulationDetector]:
        if asset not in self._oteo_engines:
            logger.info("Initializing engines for asset: %s", asset)
            oteo = OTEO()
            
            # Pre-seed from historical ticks if available
            recent_ticks = self.tick_logger.load_recent(asset, max_ticks=300)
            if recent_ticks:
                for tick in recent_ticks:
                    oteo.update_tick(float(tick["p"]), timestamp=float(tick["t"]))
                logger.info("Pre-seeded OTEO for %s with %d historical ticks", asset, len(recent_ticks))
            
            self._oteo_engines[asset] = oteo
            self._manip_engines[asset] = ManipulationDetector()
            self._tick_counts[asset] = len(recent_ticks)
            
        return self._oteo_engines[asset], self._manip_engines[asset]

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
        oteo, manip_detector = self._get_or_create_engines(asset)
        
        # 1. Update engines
        oteo_result = oteo.update_tick(price, timestamp=timestamp)
        manipulation = manip_detector.update(timestamp, price)
        
        # 2. Prepare payload
        payload = {
            "asset": asset,
            "price": price,
            "timestamp": timestamp,
            "source": source,
            "manipulation": manipulation
        }
        
        is_warmed_up = isinstance(oteo_result, dict)
        if is_warmed_up:
            # Enriched data
            payload.update({
                "oteo_score": oteo_result["oteo_score"],
                "recommended": oteo_result["recommended"],
                "confidence": oteo_result["confidence"],
                "maturity": oteo_result["maturity"],
                "velocity": oteo_result["velocity"],
                "z_score": oteo_result["z_score"],
                "slow_velocity": oteo_result["slow_velocity"],
                "trend_aligned": oteo_result["trend_aligned"],
            })
        else:
            # Default warmup data
            payload.update({
                "oteo_score": 50.0,
                "recommended": "CALL",
                "confidence": "LOW",
                "maturity": 0.0,
            })

        # 3. Log tick
        await self.tick_logger.write_tick(asset, {
            "t": timestamp,
            "p": price,
            "a": asset,
            "b": source
        })

        # 4. Log signal if significant
        if is_warmed_up and oteo_result["confidence"] in ("HIGH", "MEDIUM"):
            await self.signal_logger.log_signal({
                "t": timestamp,
                "asset": asset,
                "score": oteo_result["oteo_score"],
                "dir": oteo_result["recommended"],
                "conf": oteo_result["confidence"],
                "price": price,
                "manip": bool(manipulation),
                "broker": source
            })

        # 5. Emit via Socket.IO if available
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
