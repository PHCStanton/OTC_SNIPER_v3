"""xAI/Grok provider implementation using the OpenAI-compatible Responses API."""

from __future__ import annotations

import json
from typing import Any

import httpx

from . import AIProvider, AIResult


class XAIProvider(AIProvider):
    name = "xai"

    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1", timeout_s: float = 60.0) -> None:
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_s

    async def complete(self, *, model: str, input_items: list[dict[str, Any]]) -> AIResult:
        if not self._api_key:
            raise ValueError("GROK_API_KEY is required to call the xAI provider.")

        payload = {"model": model, "input": input_items}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, headers=headers) as client:
            response = await client.post("/responses", json=payload)

        if response.status_code >= 400:
            raise RuntimeError(self._format_error(response))

        data = response.json()
        text = self._extract_text(data)
        usage = self._extract_usage(data)
        resolved_model = data.get("model", model)

        return AIResult(provider=self.name, model=resolved_model, text=text, usage=usage, raw=data)

    def _format_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"detail": response.text}

        if isinstance(payload, dict):
            detail = payload.get("error") or payload.get("detail") or payload.get("message") or payload
        else:
            detail = payload
        return f"xAI request failed ({response.status_code}): {detail}"

    def _extract_text(self, payload: dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = payload.get("output")
        if isinstance(output, list):
            chunks: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") in {"output_text", "text"}:
                            value = block.get("text") or block.get("content")
                            if isinstance(value, str) and value.strip():
                                chunks.append(value.strip())
                elif isinstance(content, str) and content.strip():
                    chunks.append(content.strip())

            if chunks:
                return "\n".join(chunks).strip()

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()

        return "No response text returned by the AI provider."

    def _extract_usage(self, payload: dict[str, Any]) -> dict[str, int] | None:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None

        result: dict[str, int] = {}
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            value = usage.get(key)
            if isinstance(value, int):
                result[key] = value
        return result or None