"""Thin signal logger wrapper around the repository layer."""

from __future__ import annotations

from ..models.domain import SignalRecord
from .repository import DataRepository


class SignalLogger:
    def __init__(self, repository: DataRepository):
        self.repository = repository

    async def write_signal(self, signal: SignalRecord) -> None:
        await self.repository.write_signal(signal)
