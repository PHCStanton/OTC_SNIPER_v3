"""Dependency helpers for the FastAPI app."""

from __future__ import annotations

from functools import lru_cache

from .brokers.registry import BrokerRegistry
from .config import get_settings
from .data.local_store import LocalFileRepository
from .data.repository import DataRepository
from .session.manager import SessionManager


@lru_cache(maxsize=1)
def get_data_repository() -> DataRepository:
    settings = get_settings()
    return LocalFileRepository(settings.data_dir)


@lru_cache(maxsize=1)
def get_session_manager() -> SessionManager:
    return SessionManager()


def get_broker_registry() -> BrokerRegistry:
    return BrokerRegistry
