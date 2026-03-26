"""Internal session state models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SessionState:
    connected: bool
    account_type: str
    is_demo: bool
    session_id: str | None
    balance: float | None
    message: str
