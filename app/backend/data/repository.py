"""Abstract repository contract for local files and future Supabase storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..models.domain import SignalRecord, TickRecord, TradeRecord


class DataRepository(ABC):
    @abstractmethod
    async def write_tick(self, tick: TickRecord) -> None:
        ...

    @abstractmethod
    async def write_signal(self, signal: SignalRecord) -> None:
        ...

    @abstractmethod
    async def write_trade(self, trade: TradeRecord) -> None:
        ...

    @abstractmethod
    async def update_trade(self, trade: TradeRecord) -> None:
        ...

    @abstractmethod
    async def get_trades(self, session_id: str, limit: int) -> List[TradeRecord]:
        ...

    @abstractmethod
    async def get_asset_stats(self, asset: str) -> Dict[str, Any]:
        ...
