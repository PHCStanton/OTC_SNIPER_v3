"""JSONL-backed local repository implementation."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..models.domain import SignalRecord, TickRecord, TradeKind, TradeRecord
from .repository import DataRepository


def _to_plain_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if hasattr(value, "dict"):
        return dict(value.dict())
    if isinstance(value, dict):
        return dict(value)
    raise TypeError(f"Unsupported record type: {type(value)!r}")


class LocalFileRepository(DataRepository):
    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir).resolve()
        self._lock = threading.RLock()
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        for path in [
            self.base_dir,
            self.base_dir / 'tick_logs',
            self.base_dir / 'signals',
            self.base_dir / 'ghost_trades' / 'sessions',
            self.base_dir / 'ghost_trades' / 'stats',
            self.base_dir / 'live_trades' / 'sessions',
            self.base_dir / 'live_trades' / 'stats',
            self.base_dir / 'settings',
            self.base_dir / 'settings' / 'accounts',
            self.base_dir / 'settings' / 'brokers',
            self.base_dir / 'auth',
            self.base_dir / 'auth' / 'sessions',
            self.base_dir / 'data_output' / 'logs',
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + '\n')

    def _read_jsonl(self, path: Path) -> Iterable[Dict[str, Any]]:
        if not path.exists():
            return []

        rows: list[Dict[str, Any]] = []
        with path.open('r', encoding='utf-8') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    async def write_tick(self, tick: TickRecord) -> None:
        record = _to_plain_dict(tick)
        asset = record.get('asset')
        if not asset:
            raise ValueError('Tick record is missing asset')
        self._append_jsonl(self.base_dir / 'tick_logs' / asset / 'ticks.jsonl', record)

    async def write_signal(self, signal: SignalRecord) -> None:
        record = _to_plain_dict(signal)
        self._append_jsonl(self.base_dir / 'signals' / f"{time.strftime('%Y-%m-%d')}.jsonl", record)

    async def write_trade(self, trade: TradeRecord) -> None:
        record = _to_plain_dict(trade)
        session_id = record.get('session_id')
        if not session_id:
            raise ValueError('Trade record is missing session_id')

        kind = str(record.get('kind', TradeKind.LIVE.value))
        if kind == TradeKind.GHOST.value:
            target = self.base_dir / 'ghost_trades' / 'sessions' / f"{session_id}.jsonl"
        else:
            target = self.base_dir / 'live_trades' / 'sessions' / f"{session_id}.jsonl"
        self._append_jsonl(target, record)

    async def update_trade(self, trade: TradeRecord) -> None:
        record = _to_plain_dict(trade)
        session_id = record.get('session_id')
        if not session_id:
            raise ValueError('Trade record is missing session_id')

        trade_id = record.get('id')
        if not trade_id:
            raise ValueError('Trade record is missing id')

        kind = str(record.get('kind', TradeKind.LIVE.value))
        if kind == TradeKind.GHOST.value:
            target = self.base_dir / 'ghost_trades' / 'sessions' / f"{session_id}.jsonl"
        else:
            target = self.base_dir / 'live_trades' / 'sessions' / f"{session_id}.jsonl"

        if not target.exists():
            return

        with self._lock:
            rows = list(self._read_jsonl(target))  # Fix #10: ensure list for enumerate
            updated = False
            for i, row in enumerate(rows):
                if row.get('id') == trade_id:
                    rows[i] = record
                    updated = True
                    break

            if not updated:
                # Fix #9: Warn explicitly instead of silently returning
                logger.warning("update_trade: id %s not found in %s — skipping.", trade_id, target)
                return

            # Fix #8: open file once, write all rows in a single context
            target.write_text('', encoding='utf-8')
            with target.open('a', encoding='utf-8') as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + '\n')

    async def get_trades(self, session_id: str, limit: int) -> List[TradeRecord]:
        if not session_id:
            raise ValueError('session_id is required')
        if limit <= 0:
            raise ValueError('limit must be greater than zero')

        candidates = [
            self.base_dir / 'live_trades' / 'sessions' / f"{session_id}.jsonl",
            self.base_dir / 'ghost_trades' / 'sessions' / f"{session_id}.jsonl",
        ]

        rows: list[Dict[str, Any]] = []
        for path in candidates:
            rows.extend(self._read_jsonl(path))

        rows.sort(key=lambda item: float(item.get('timestamp', 0.0)))
        return [TradeRecord(**row) for row in rows[-limit:]]

    async def get_asset_stats(self, asset: str) -> Dict[str, Any]:
        if not asset:
            raise ValueError('asset is required')

        total_trades = 0
        wins = 0
        losses = 0
        profit = 0.0
        last_updated: float | None = None

        for directory in [self.base_dir / 'live_trades' / 'sessions', self.base_dir / 'ghost_trades' / 'sessions']:
            for file_path in directory.glob('*.jsonl'):
                for row in self._read_jsonl(file_path):
                    if str(row.get('asset', '')).upper() != asset.upper():
                        continue
                    total_trades += 1
                    outcome = str(row.get('outcome', '')).lower()
                    if outcome == 'win':
                        wins += 1
                    elif outcome == 'loss':
                        losses += 1
                    profit += float(row.get('profit', 0.0) or 0.0)
                    last_updated = max(last_updated or 0.0, float(row.get('timestamp', 0.0)))

        win_rate = (wins / total_trades) if total_trades else 0.0
        return {
            'asset': asset,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'profit': profit,
            'last_updated': last_updated,
        }
