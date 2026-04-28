"""API request models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ConnectBrokerRequest(BaseModel):
    ssid: str = Field(min_length=1)


class TradeExecutionRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    direction: str = Field(min_length=1)
    amount: float = Field(gt=0)
    expiration: int = Field(gt=0)
    account_key: str = "primary"
    trade_mode: str = Field(default="live", min_length=1)
    demo: bool = False
    session_id: str | None = None
    confidence: str | None = None
    oteo_score: float | None = None
    base_oteo_score: float | None = None
    level2_score_adjustment: float | None = None
    strategy_level: str | None = None
    manipulation_at_entry: dict | None = None
    entry_context: dict | None = None
    trigger_mode: str | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            normalized = value.strip().upper()
            return normalized or None

        if isinstance(value, bool):
            raise ValueError("confidence must be a string, number, or null")

        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be a string, number, or null") from exc

        if numeric > 75:
            return "HIGH"
        if numeric > 55:
            return "MEDIUM"
        return "LOW"
