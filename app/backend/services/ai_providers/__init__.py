"""Provider registry for advisory-only AI integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AIResult:
    provider: str
    model: str
    text: str
    usage: dict[str, int] | None = None
    raw: dict[str, Any] | None = None


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, *, model: str, input_items: list[dict[str, Any]]) -> AIResult:
        raise NotImplementedError


from .xai_provider import XAIProvider


def get_provider(*, api_key: str) -> AIProvider:
    if not api_key.strip():
        raise ValueError("AI provider is unavailable because GROK_API_KEY is missing.")
    return XAIProvider(api_key=api_key.strip())