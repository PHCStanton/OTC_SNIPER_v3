"""
Tick Logger — OTC SNIPER v3
Asynchronous JSONL logging for live ticks with memory buffering.
"""
import aiofiles
import json
import logging
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set, List, Optional

logger = logging.getLogger(__name__)

_DATED_TICK_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")


class TickLogger:
    """
    Logs raw price ticks to JSONL files, scoped by asset and date.
    Uses in-memory buffering and periodic flushing to prevent per-tick disk I/O.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._created_dirs: Set[str] = set()
        
        # Buffering state (Phase 1)
        self._buffers: Dict[str, List[str]] = {}
        self._flush_task: Optional[asyncio.Task] = None
        self._active = False

    def start(self):
        """Start the background flush loop."""
        if self._active:
            return
        self._active = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("TickLogger buffered flusher started.")

    def stop(self):
        """Stop the background flush loop and flush all pending buffers."""
        self._active = False
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None
        # Drain remaining ticks
        asyncio.create_task(self.flush_all())
        logger.info("TickLogger buffered flusher stopped and final flush scheduled.")

    async def write_tick(self, asset: str, tick_data: Dict[str, Any]) -> None:
        """
        Add a tick record to the appropriate in-memory buffer.
        """
        line = json.dumps(tick_data, ensure_ascii=False) + "\n"
        if asset not in self._buffers:
            self._buffers[asset] = []
        
        self._buffers[asset].append(line)
        
        # If buffer is large, flush immediately
        if len(self._buffers[asset]) >= 100:
            await self.flush_asset(asset)

    async def _periodic_flush(self):
        while self._active:
            try:
                await asyncio.sleep(5.0)
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in TickLogger periodic flush: %s", e)

    async def flush_all(self) -> None:
        """Flush all pending asset buffers to disk."""
        assets = list(self._buffers.keys())
        for asset in assets:
            await self.flush_asset(asset)

    async def flush_asset(self, asset: str) -> None:
        """Flush a specific asset's buffer to disk."""
        lines = self._buffers.get(asset, [])
        if not lines:
            return
        
        self._buffers[asset] = []  # Swap out buffer
        
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            asset_dir = self.base_dir / asset
            
            if asset not in self._created_dirs:
                asset_dir.mkdir(parents=True, exist_ok=True)
                self._created_dirs.add(asset)
            
            target_file = asset_dir / f"{date_str}.jsonl"
            content = "".join(lines)
            
            async with aiofiles.open(target_file, mode="a", encoding="utf-8") as f:
                await f.write(content)
        except Exception as e:
            logger.error("Failed to flush ticks for %s: %s", asset, e)
            # Re-queue on failure so we don't lose ticks
            self._buffers[asset] = lines + self._buffers[asset]

    def load_recent(self, asset: str, max_ticks: int = 300) -> list:
        """
        Synchronous helper to seed OTEO on startup.
        Reads from the most recent JSONL file for the asset.
        """
        asset_dir = self.base_dir / asset
        if not asset_dir.exists():
            return []

        files = sorted(
            [
                path
                for path in asset_dir.glob("*.jsonl")
                if _DATED_TICK_FILE_RE.match(path.name)
            ],
            reverse=True,
        )
        if not files:
            return []

        ticks = []
        try:
            # Read last file from bottom up to get most recent ticks
            with open(files[0], "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-max_ticks:]:
                    ticks.append(json.loads(line))
        except Exception as e:
            logger.warning("Failed to load recent ticks for %s from %s: %s", asset, files[0], e)

        return ticks
