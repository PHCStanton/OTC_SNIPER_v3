"""
Signal Logger — OTC SNIPER v3
Asynchronous JSONL logging for signals with memory buffering.
"""
import asyncio
import logging
import aiofiles
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SignalLogger:
    """
    Logs enriched signals to JSONL files.
    Files are stored in: data/signals/{YYYY-MM-DD}.jsonl
    Uses in-memory buffering and periodic flushing to prevent per-signal disk I/O.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._buffers: Dict[str, List[str]] = {}
        self._flush_task: Optional[asyncio.Task] = None
        self._active = False

    def start(self):
        """Start the background flush loop."""
        if self._active:
            return
        self._active = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("SignalLogger buffered flusher started.")

    def stop(self):
        """Stop the background flush loop and flush all pending buffers."""
        self._active = False
        if self._flush_task:
            self._flush_task.cancel()
            self._flush_task = None
        # Drain remaining signals
        asyncio.create_task(self.flush_all())
        logger.info("SignalLogger buffered flusher stopped and final flush scheduled.")

    async def log_signal(self, signal_data: Dict[str, Any]) -> None:
        """
        Log a signal record by placing it in an in-memory buffer.
        """
        date_str = datetime.fromtimestamp(signal_data.get("t", datetime.now().timestamp())).strftime("%Y-%m-%d")
        line = json.dumps(signal_data, ensure_ascii=False) + "\n"
        
        if date_str not in self._buffers:
            self._buffers[date_str] = []
        self._buffers[date_str].append(line)
        
        # Flush if buffer grows too large (e.g. 50 signals)
        if len(self._buffers[date_str]) >= 50:
            await self.flush_date(date_str)

    async def _periodic_flush(self):
        while self._active:
            try:
                await asyncio.sleep(5.0)
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in SignalLogger periodic flush: %s", e)

    async def flush_all(self) -> None:
        """Flush all pending date buffers to disk."""
        dates = list(self._buffers.keys())
        for date_str in dates:
            await self.flush_date(date_str)

    async def flush_date(self, date_str: str) -> None:
        """Flush a specific date's buffer to disk."""
        lines = self._buffers.get(date_str, [])
        if not lines:
            return
        
        self._buffers[date_str] = []  # Swap out buffer
        
        try:
            target_file = self.base_dir / f"{date_str}.jsonl"
            content = "".join(lines)
            
            async with aiofiles.open(target_file, mode="a", encoding="utf-8") as f:
                await f.write(content)
        except Exception as e:
            logger.error("Failed to flush signals for %s: %s", date_str, e)
            # Re-queue on failure
            self._buffers[date_str] = lines + self._buffers[date_str]
