"""
Tick Logger — OTC SNIPER v3
Asynchronous JSONL logging for live ticks.
"""
import aiofiles
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)

_DATED_TICK_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")


class TickLogger:
    """
    Logs raw price ticks to JSONL files, scoped by asset and date.
    Files are stored in: data/tick_logs/{asset}/{YYYY-MM-DD}.jsonl
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Fix #9: track created dirs so we avoid per-tick blocking mkdir calls
        self._created_dirs: Set[str] = set()

    async def write_tick(self, asset: str, tick_data: Dict[str, Any]) -> None:
        """
        Write a tick record to the appropriate JSONL file.
        """
        date_str = datetime.fromtimestamp(tick_data.get("t", datetime.now().timestamp())).strftime("%Y-%m-%d")
        asset_dir = self.base_dir / asset
        # Fix #9: only call mkdir once per asset directory
        if asset not in self._created_dirs:
            asset_dir.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(asset)
        
        target_file = asset_dir / f"{date_str}.jsonl"
        
        line = json.dumps(tick_data, ensure_ascii=False) + "\n"
        
        async with aiofiles.open(target_file, mode="a", encoding="utf-8") as f:
            await f.write(line)

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
            # Fix #10: log instead of silently failing — corrupt JSONL should be visible
            logger.warning("Failed to load recent ticks for %s from %s: %s", asset, files[0], e)

        return ticks
