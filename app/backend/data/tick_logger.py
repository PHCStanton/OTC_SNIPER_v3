"""Thin tick logger wrapper around the repository layer."""

from __future__ import annotations

from ..models.domain import TickRecord
from .repository import DataRepository


class TickLogger:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    async def write_tick(self, tick: TickRecord) -> None:
        await self.repository.write_tick(tick)
