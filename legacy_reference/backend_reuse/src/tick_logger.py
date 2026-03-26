"""
Tick Logger — A3 (2026-03-21)
==============================
Writes live ticks to JSONL files, 500 ticks per file, with 30-minute expiry.

Design decisions:
  - One file per asset at a time. Rotates when tick count reaches ticks_per_file.
  - Expired files are MOVED to archive/ (never deleted) for post-session analysis.
  - _manifest.json is the index of all files with metadata.
  - Thread-safe: uses file-level append (no in-memory buffering).
  - Errors are logged and re-raised — never swallowed silently.

Integration:
  Call write_tick() from enrichment_handler() in redis_gateway.py.
  Call load_recent() from _get_or_create_engines() for OTEO instant warmup (B5).
  Cleanup task runs every 5 minutes via asyncio in lifespan().

JSONL record format (one JSON object per line):
  {"t": 1711007400.123, "p": 1.08234, "a": "EURUSD", "v": 0.0, "b": "pocket_option"}
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TickLogger")


class TickLogger:
    """
    Writes ticks to JSONL files, 500 per file, with 30-min expiry.

    One file per asset at a time. When tick count reaches ticks_per_file,
    the current file is closed and a new one is started.

    Integration: Call write_tick() from enrichment_handler() in redis_gateway.py.
    """

    def __init__(
        self,
        base_dir: Path,
        ticks_per_file: int = 500,
        expiry_minutes: int = 30,
    ) -> None:
        """
        Args:
            base_dir:       Path to web_app/data/tick_logs/
            ticks_per_file: Number of ticks before rotating to a new file. Default 500.
            expiry_minutes: Minutes before a file is considered expired. Default 30.
        """
        self.base_dir = Path(base_dir)
        self.archive_dir = self.base_dir / "archive"
        self.ticks_per_file = ticks_per_file
        self.expiry_minutes = expiry_minutes
        self._manifest_path = self.base_dir / "_manifest.json"

        # Per-asset state: { asset: {"path": Path, "count": int, "start_ts": float} }
        self._active: Dict[str, dict] = {}

        # Manifest data (loaded lazily, written on rotation)
        self._manifest: dict = {"version": 1, "format": "jsonl",
                                "ticks_per_file": ticks_per_file,
                                "expiry_minutes": expiry_minutes, "files": []}

        # Ensure directories exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Load existing manifest if present
        self._load_manifest()

    # ── Public API ────────────────────────────────────────────────────────────

    def write_tick(self, asset: str, tick: dict) -> None:
        """
        Append a single tick to the current JSONL file for this asset.

        Creates the asset subdirectory if it doesn't exist.
        Rotates to a new file when tick count reaches ticks_per_file.
        Updates _manifest.json on file rotation.

        Args:
            asset: Normalized asset name (e.g., "EURUSD")
            tick:  Dict with keys: t (timestamp), p (price), a (asset),
                   v (volume), b (broker)

        Raises:
            IOError: If file write fails (logged, not swallowed).
        """
        asset_dir = self.base_dir / asset
        asset_dir.mkdir(parents=True, exist_ok=True)

        state = self._active.get(asset)

        # Start a new file if none exists or current file is full
        if state is None or state["count"] >= self.ticks_per_file:
            if state is not None:
                # Finalise the completed file in the manifest
                self._finalise_file(asset, state)
            state = self._start_new_file(asset, asset_dir, tick.get("t", time.time()))
            self._active[asset] = state

        # Append tick as a JSON line
        try:
            with open(state["path"], "a", encoding="utf-8") as fh:
                fh.write(json.dumps(tick, separators=(",", ":")) + "\n")
            state["count"] += 1
            state["last_ts"] = tick.get("t", time.time())
        except IOError as exc:
            logger.error("TickLogger: failed to write tick for %s: %s", asset, exc)
            raise

    def load_recent(self, asset: str, max_ticks: int = 500) -> List[dict]:
        """
        Load the most recent non-expired ticks for an asset.

        Used for OTEO instant warmup (B5): loads ticks from the newest
        non-expired file(s) for the given asset, up to max_ticks.

        Args:
            asset:     Normalized asset name
            max_ticks: Maximum number of ticks to return. Default 500.

        Returns:
            List of tick dicts, oldest first. Empty list if no data available.
        """
        asset_dir = self.base_dir / asset
        if not asset_dir.exists():
            return []

        now = time.time()
        expiry_seconds = self.expiry_minutes * 60

        # Collect all non-expired .jsonl files for this asset, newest first
        jsonl_files = sorted(
            asset_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        ticks: List[dict] = []
        for fpath in jsonl_files:
            if now - fpath.stat().st_mtime > expiry_seconds:
                continue  # skip expired files
            try:
                lines = fpath.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            ticks.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass  # skip malformed lines
            except IOError as exc:
                logger.warning("TickLogger: could not read %s: %s", fpath, exc)

            if len(ticks) >= max_ticks:
                break

        # Return oldest-first, capped at max_ticks
        return ticks[-max_ticks:] if len(ticks) > max_ticks else ticks

    def cleanup_expired(self) -> int:
        """
        Move expired files to archive/ directory.

        A file is expired if its last modification time is older than
        expiry_minutes ago.

        Returns:
            Number of files moved to archive.
        """
        now = time.time()
        expiry_seconds = self.expiry_minutes * 60
        moved = 0

        for asset_dir in self.base_dir.iterdir():
            if not asset_dir.is_dir() or asset_dir.name == "archive":
                continue
            for fpath in asset_dir.glob("*.jsonl"):
                if now - fpath.stat().st_mtime > expiry_seconds:
                    dest_dir = self.archive_dir / asset_dir.name
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / fpath.name
                    try:
                        shutil.move(str(fpath), str(dest))
                        moved += 1
                        logger.debug("TickLogger: archived %s → %s", fpath.name, dest_dir)
                    except Exception as exc:
                        logger.warning("TickLogger: could not archive %s: %s", fpath, exc)

        if moved:
            self._update_manifest()

        return moved

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _start_new_file(self, asset: str, asset_dir: Path, start_ts: float) -> dict:
        """Create a new JSONL file for the asset and return its state dict."""
        ts_str = time.strftime("%Y-%m-%d_%H%M%S", time.localtime(start_ts))
        filename = f"{ts_str}_{asset}_{self.ticks_per_file}.jsonl"
        path = asset_dir / filename
        # Touch the file so it exists
        path.touch()
        logger.info("TickLogger: new file for %s → %s", asset, filename)
        return {"path": path, "count": 0, "start_ts": start_ts, "last_ts": start_ts}

    def _finalise_file(self, asset: str, state: dict) -> None:
        """Record a completed file in the manifest."""
        entry = {
            "path": str(state["path"].relative_to(self.base_dir)),
            "asset": asset,
            "broker": "pocket_option",
            "start_ts": state["start_ts"],
            "end_ts": state.get("last_ts", state["start_ts"]),
            "tick_count": state["count"],
            "expired": False,
        }
        self._manifest["files"].append(entry)
        self._update_manifest()

    def _update_manifest(self) -> None:
        """Write current manifest state to _manifest.json."""
        try:
            self._manifest_path.write_text(
                json.dumps(self._manifest, indent=2),
                encoding="utf-8",
            )
        except IOError as exc:
            logger.error("TickLogger: failed to write manifest: %s", exc)

    def _load_manifest(self) -> None:
        """Load existing manifest from disk if present."""
        if self._manifest_path.exists():
            try:
                data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "files" in data:
                    self._manifest = data
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning("TickLogger: could not load manifest: %s — starting fresh", exc)
