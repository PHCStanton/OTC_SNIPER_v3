"""Domain records used by the backend and data layer."""

from __future__ import annotations

import time
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class TradeKind(str, Enum):
    LIVE = "live"
    GHOST = "ghost"


class TickRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: float = Field(default_factory=lambda: time.time())
    asset: str
    price: float
    volume: float = 0.0
    broker: str = "pocket_option"


class SignalRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: float = Field(default_factory=lambda: time.time())
    asset: str
    score: float
    direction: str
    confidence: str
    price: float
    velocity: float = 0.0
    z_score: float = 0.0
    maturity: float = 0.0
    manipulation: bool = False
    broker: str = "pocket_option"


class TradeRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    asset: str
    direction: str
    amount: float
    expiration_seconds: int
    broker: str = "pocket_option"
    kind: TradeKind = TradeKind.LIVE
    timestamp: float = Field(default_factory=lambda: time.time())
    success: bool = True
    message: str = ""
    trade_id: str | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    entry_time: float | None = None
    exit_time: float | None = None
    outcome: str | None = None
    profit: float | None = None
    payout_pct: float | None = None
    confidence: str | None = None
    oteo_score: float | None = None
    base_oteo_score: float | None = None
    level2_score_adjustment: float | None = None
    strategy_level: str | None = None
    trigger_mode: str | None = None
    manipulation_at_entry: dict | None = None
    entry_context: dict | None = None
    simulated_profit: float | None = None
    simulated_amount: float | None = None
