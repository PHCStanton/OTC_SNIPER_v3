"""Thin trade logger wrapper around the repository layer."""

from __future__ import annotations

from ..models.domain import TradeRecord
from .repository import DataRepository


class TradeLogger:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    async def write_trade(self, trade: TradeRecord) -> None:
        await self.repository.write_trade(trade)
