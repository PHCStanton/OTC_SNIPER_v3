"""API request models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectBrokerRequest(BaseModel):
    ssid: str = Field(min_length=1)


class TradeExecutionRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    amount: float = Field(gt=0)
    expiration: int = Field(gt=0)
    account_key: str = "primary"
