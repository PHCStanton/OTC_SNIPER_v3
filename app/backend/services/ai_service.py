"""Provider-agnostic AI service layer for advisory-only analysis."""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Any

from ..config import RuntimeSettings, get_settings
from ..models.ai_models import AIChatRequest, AIContext, AIImageRequest, AIStatusResponse, AIUsage
from .ai_providers import AIProvider, AIResult, get_provider

MAX_IMAGE_BYTES = 20 * 1024 * 1024
DEFAULT_AI_MODEL = "grok-4-1-fast-non-reasoning"

SYSTEM_PROMPT = """
You are OTC SNIPER's advisory-only AI trading assistant.

Rules:
- Never execute trades, trigger actions, or modify settings.
- Never claim certainty or guarantee outcomes.
- Provide analysis only: structure, trend, support/resistance, momentum, risk context, and likely scenarios.
- Keep responses concise, practical, and clearly separated into bullet points when helpful.
- If a chart screenshot is provided, analyze the visual evidence and mention visible levels or patterns.
- If context is supplied, use it to make the analysis more relevant.
- If the context is insufficient, say so explicitly.
""".strip()


@dataclass(slots=True)
class PreparedImage:
    mime_type: str
    data_uri: str
    size_bytes: int


class AIService:
    def __init__(self, settings: RuntimeSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._provider: AIProvider | None = None

    @property
    def settings(self) -> RuntimeSettings:
        return self._settings

    @property
    def provider(self) -> AIProvider:
        if self._provider is None:
            self._provider = get_provider(api_key=self._settings.grok_api_key)
        return self._provider

    def status(self) -> AIStatusResponse:
        has_api_key = bool(self._settings.grok_api_key.strip())
        enabled = bool(self._settings.ai_enabled and has_api_key)
        reason = None
        if not has_api_key:
            reason = "GROK_API_KEY is not configured."
        elif not self._settings.ai_enabled:
            reason = "AI is disabled via AI_ENABLED=false."

        return AIStatusResponse(
            enabled=enabled,
            provider="xai",
            model=self._settings.ai_model or DEFAULT_AI_MODEL,
            has_api_key=has_api_key,
            reason=reason,
        )

    async def chat(self, request: AIChatRequest) -> AIResult:
        self._ensure_enabled()
        input_items = self._build_chat_input(request.messages, request.context)
        return await self.provider.complete(model=self._resolve_model(request.model), input_items=input_items)

    async def analyze_image(self, request: AIImageRequest) -> AIResult:
        self._ensure_enabled()
        image = self._prepare_image(request.image_base64, request.mime_type)
        input_items = self._build_image_input(request.prompt, request.context, image)
        return await self.provider.complete(model=self._resolve_model(request.model), input_items=input_items)

    def _ensure_enabled(self) -> None:
        if not self.status().enabled:
            raise RuntimeError(self.status().reason or "AI is disabled.")

    def _resolve_model(self, override: str | None = None) -> str:
        model = (override or self._settings.ai_model or DEFAULT_AI_MODEL).strip()
        return model or DEFAULT_AI_MODEL

    def _build_chat_input(self, messages: list[Any], context: AIContext | None) -> list[dict[str, Any]]:
        input_items: list[dict[str, Any]] = [self._build_system_message(context)]

        for message in messages:
            content = self._message_content(message)
            role = getattr(message, "role", None) or message.get("role")
            if not content or role not in {"system", "user", "assistant"}:
                continue
            input_items.append({"role": role, "content": [{"type": "input_text", "text": content}]})

        return input_items

    def _build_image_input(self, prompt: str, context: AIContext | None, image: PreparedImage) -> list[dict[str, Any]]:
        user_content = [
            {"type": "input_image", "image_url": image.data_uri, "detail": "high"},
            {"type": "input_text", "text": prompt},
        ]
        input_items = [self._build_system_message(context)]
        if context is not None:
            context_block = self._context_block(context)
            if context_block:
                input_items.append({"role": "system", "content": [{"type": "input_text", "text": context_block}]})
        input_items.append({"role": "user", "content": user_content})
        return input_items

    def _build_system_message(self, context: AIContext | None) -> dict[str, Any]:
        text = SYSTEM_PROMPT
        context_block = self._context_block(context)
        if context_block:
            text = f"{text}\n\nTrading context:\n{context_block}"
        return {"role": "system", "content": [{"type": "input_text", "text": text}]}

    def _context_block(self, context: AIContext | None) -> str:
        if context is None:
            return ""

        lines: list[str] = []
        if context.asset:
            lines.append(f"- Asset: {context.asset}")
        if context.balance is not None:
            lines.append(f"- Balance: {context.balance:.2f}")
        if context.session_pnl is not None:
            lines.append(f"- Session P&L: {context.session_pnl:.2f}")
        if context.win_rate is not None:
            lines.append(f"- Win rate: {context.win_rate:.2f}%")
        if context.current_streak is not None:
            lines.append(f"- Current streak: {context.current_streak}")
        if context.total_trades is not None:
            lines.append(f"- Total trades: {context.total_trades}")
        if context.account_type:
            lines.append(f"- Account type: {context.account_type}")
        return "\n".join(lines)

    def _message_content(self, message: Any) -> str:
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        return str(content).strip() if content is not None else ""

    def _prepare_image(self, image_base64: str, mime_type: str | None) -> PreparedImage:
        text = image_base64.strip()
        match = re.match(r"^data:(image/(?:png|jpeg));base64,(.+)$", text, flags=re.IGNORECASE | re.DOTALL)

        if match:
            resolved_mime = match.group(1).lower()
            base64_part = match.group(2)
        else:
            resolved_mime = (mime_type or "image/png").lower()
            base64_part = text

        if resolved_mime not in {"image/png", "image/jpeg"}:
            raise ValueError("Unsupported image format. Only PNG and JPEG are allowed.")

        try:
            raw_bytes = base64.b64decode(base64_part, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64 image payload.") from exc

        if len(raw_bytes) > MAX_IMAGE_BYTES:
            raise ValueError("Image exceeds the 20 MB size limit.")

        data_uri = f"data:{resolved_mime};base64,{base64_part}"
        return PreparedImage(mime_type=resolved_mime, data_uri=data_uri, size_bytes=len(raw_bytes))


_SERVICE: AIService | None = None


def get_ai_service() -> AIService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = AIService()
    return _SERVICE