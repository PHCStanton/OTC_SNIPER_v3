"""
Signal Logger — A4 (2026-03-21)
================================
Logs OTEO signals (MEDIUM and HIGH confidence) to per-session JSONL files.

Design decisions:
  - One file per gateway session. File is created on first signal.
  - LOW confidence signals are NOT logged (noise reduction).
  - Each record includes all fields needed for Ghost Trading (Phase C)
    and backtesting.
  - Errors are logged — never swallowed silently.

Integration:
  Call log_signal() from enrichment_handler() in redis_gateway.py after
  OTEO scoring, when confidence is MEDIUM or HIGH.

JSONL record format (one JSON object per line):
  {
    "t": 1711007400.123,
    "asset": "EURUSD",
    "score": 82.3,
    "dir": "PUT",
    "conf": "HIGH",
    "price": 1.08234,
    "vel": -0.000234,
    "z": 2.14,
    "maturity": 0.85,
    "manip": false,
    "broker": "pocket_option"
  }
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("SignalLogger")

# Only log signals at these confidence levels
_LOGGABLE_CONFIDENCE = {"HIGH", "MEDIUM"}


class SignalLogger:
    """
    Logs OTEO signals (MEDIUM and HIGH confidence) to per-session JSONL files.

    One file per gateway session. File is created on first signal.
    """

    def __init__(self, base_dir: Path) -> None:
        """
        Args:
            base_dir: Path to web_app/data/signals/
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Session file path — set on first log_signal() call
        self._session_path: Path | None = None
        self._session_start: float = time.time()

    def log_signal(self, signal: dict) -> None:
        """
        Append a signal record to the current session file.

        Only logs signals with confidence MEDIUM or HIGH.
        Creates the session file on first call.

        Args:
            signal: Dict matching the Signal Record Format:
                t        (float)  — Unix timestamp
                asset    (str)    — Normalized asset name
                score    (float)  — OTEO score (0–100)
                dir      (str)    — "CALL" or "PUT"
                conf     (str)    — "HIGH", "MEDIUM", or "LOW"
                price    (float)  — Price at signal time
                vel      (float)  — Velocity at signal time
                z        (float)  — Z-score at signal time
                maturity (float)  — Baseline maturity (0.0–1.0)
                manip    (bool)   — True if any manipulation flag was active
                broker   (str)    — Broker identifier
        """
        conf = signal.get("conf", "LOW")
        if conf not in _LOGGABLE_CONFIDENCE:
            return  # LOW signals are not logged

        # Create session file on first signal
        if self._session_path is None:
            self._session_path = self._new_session_path()
            logger.info("SignalLogger: session file → %s", self._session_path.name)

        try:
            with open(self._session_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(signal, separators=(",", ":")) + "\n")
        except IOError as exc:
            logger.error("SignalLogger: failed to write signal: %s", exc)
            # Re-raise so the caller knows the write failed
            raise

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _new_session_path(self) -> Path:
        """Generate a timestamped session file path."""
        ts_str = time.strftime("%Y-%m-%d_%H%M", time.localtime(self._session_start))
        filename = f"signals_{ts_str}.jsonl"
        return self.base_dir / filename
