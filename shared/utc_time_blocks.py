"""UTC 4-hour time-block dimension for condition patterns and Bayesian features.

REV2 A1 — clock origin is 22:00 UTC (OTC rollover). This matches the
backtest engine (`calculate_time_offsets`) and the documented pockets:

  block 0 → 22:00-02:00  (rollover, historically weaker)
  block 5 → 18:00-22:00  (historically stronger)

Blocks are 0..5 inclusive. All timestamps are Unix epoch, interpreted as UTC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Union

UTC_4H_ORIGIN_HOUR = 22
UTC_4H_BLOCK_HOURS = 4
UTC_4H_BLOCK_COUNT = 6
SECONDS_PER_DAY = 86400.0

PathLikeUnix = Union[int, float]


def utc_4h_block(timestamp: PathLikeUnix) -> int:
    """Return the 4-hour UTC block index (0..5) for a Unix timestamp."""
    dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    mins_today = dt.hour * 60 + dt.minute
    offset_mins = (mins_today - UTC_4H_ORIGIN_HOUR * 60) % (24 * 60)
    return int((offset_mins // 60) // UTC_4H_BLOCK_HOURS)


def utc_4h_label(block: int) -> str:
    """Human-readable window for a 4-hour block, e.g. ``18:00-22:00``."""
    idx = int(block) % UTC_4H_BLOCK_COUNT
    start = (UTC_4H_ORIGIN_HOUR + idx * UTC_4H_BLOCK_HOURS) % 24
    end = (start + UTC_4H_BLOCK_HOURS) % 24
    return f"{start:02d}:00-{end:02d}:00"


def utc_hour(timestamp: PathLikeUnix) -> int:
    """Clock hour 0..23 in UTC."""
    return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).hour


def trade_entry_unix(trade: Mapping[str, Any]) -> Optional[float]:
    """Best-effort Unix timestamp from a ghost/live trade record. None if absent."""
    for key in ("entry_time", "timestamp", "entry_time_epoch"):
        raw = trade.get(key)
        parsed = _as_unix(raw)
        if parsed is not None:
            return parsed
    ctx = trade.get("entry_context")
    if isinstance(ctx, Mapping):
        for key in ("timestamp", "entry_time"):
            parsed = _as_unix(ctx.get(key))
            if parsed is not None:
                return parsed
    return None


def _as_unix(raw: Any) -> Optional[float]:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return value
