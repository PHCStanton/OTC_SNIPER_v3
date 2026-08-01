"""
xAI API Provider Adapter for Hermes Agent Harness

Connects Hermes Autonomous Agent to xAI's API endpoint (https://api.x.ai/v1)
to utilize Grok reasoning models for market intelligence analysis.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("data_agent.xai_provider")


class XAIProvider:
    """
    Client wrapper for xAI API (Grok models).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.x.ai/v1",
        default_model: str = "grok-2",
        timeout_sec: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_sec = timeout_sec

    @property
    def is_configured(self) -> bool:
        """Returns True if an xAI API key is present."""
        return bool(self.api_key and len(self.api_key) > 5)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to the xAI endpoint.
        """
        if not self.is_configured:
            logger.warning("XAI_API_KEY is not configured. Returning simulated mock response.")
            return {
                "status": "mocked",
                "model": model or self.default_model,
                "content": "xAI API key not set. Hermes Agent operating in offline evaluation mode.",
            }

        target_model = model or self.default_model
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                return {
                    "status": "success",
                    "model": target_model,
                    "content": content,
                    "usage": data.get("usage", {}),
                }
        except httpx.HTTPStatusError as http_err:
            logger.error(f"xAI API HTTP status error: {http_err.response.status_code} - {http_err.response.text}")
            return {
                "status": "error",
                "error": f"HTTP {http_err.response.status_code}: {http_err.response.text}",
            }
        except Exception as exc:
            logger.error(f"xAI API request failed: {exc}")
            return {
                "status": "error",
                "error": str(exc),
            }
