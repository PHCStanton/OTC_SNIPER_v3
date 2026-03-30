"""AI request and response models for advisory-only AI integration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AIContext(BaseModel):
    asset: str | None = None
    balance: float | None = None
    session_pnl: float | None = Field(default=None, alias="sessionPnl")
    win_rate: float | None = Field(default=None, alias="winRate")
    current_streak: int | None = Field(default=None, alias="currentStreak")
    total_trades: int | None = Field(default=None, alias="totalTrades")
    account_type: str | None = Field(default=None, alias="accountType")


class AIMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class AIChatRequest(BaseModel):
    messages: list[AIMessage] = Field(min_length=1)
    context: AIContext | None = None
    model: str | None = None


class AIImageRequest(BaseModel):
    image_base64: str = Field(min_length=1)
    prompt: str = Field(default="Analyze this chart screenshot for structure, trend, support/resistance, and risk context.")
    context: AIContext | None = None
    model: str | None = None
    mime_type: str | None = None


class AIUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AIStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    has_api_key: bool
    reason: str | None = None


class AIChatResponse(BaseModel):
    ok: bool = True
    provider: str
    model: str
    response: str
    usage: AIUsage | None = None


class AIImageResponse(BaseModel):
    ok: bool = True
    provider: str
    model: str
    analysis: str
    usage: AIUsage | None = None