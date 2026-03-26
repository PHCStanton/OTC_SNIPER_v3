"""
Signal Logger — OTC SNIPER v3
Asynchronous JSONL logging for signals.
"""
import aiofiles
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class SignalLogger:
    """
    Logs enriched signals to JSONL files.
    Files are stored in: data/signals/{YYYY-MM-DD}.jsonl
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def log_signal(self, signal_data: Dict[str, Any]) -> None:
        """
        Log a signal record.
        """
        date_str = datetime.fromtimestamp(signal_data.get("t", datetime.now().timestamp())).strftime("%Y-%m-%d")
        target_file = self.base_dir / f"{date_str}.jsonl"
        
        line = json.dumps(signal_data, ensure_ascii=False) + "\n"
        
        async with aiofiles.open(target_file, mode="a", encoding="utf-8") as f:
            await f.write(line)
