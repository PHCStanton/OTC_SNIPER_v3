"""API response models."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    host: str
    port: int
    enable_ops: bool
    data_dir: str


class SessionStatusResponse(BaseModel):
    connected: bool
    account_type: str
    is_demo: bool
    session_id: str | None = None
    balance: float | None = None
    message: str = ""


class BrokerListResponse(BaseModel):
    brokers: list[dict]


class BrokerActionResponse(BaseModel):
    success: bool
    broker: str
    message: str
    connection_status: str | None = None


class TradeExecutionResponse(BaseModel):
    success: bool
    broker: str
    asset_id: str
    direction: str
    amount: float
    expiration: int
    message: str
    trade_id: str | None = None
    session_id: str | None = None
    entry_price: float | None = None
    connection_status: str | None = None
    trade_mode: str = "live"


class DataStatsResponse(BaseModel):
    asset: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    profit: float
    last_updated: float | None = None
