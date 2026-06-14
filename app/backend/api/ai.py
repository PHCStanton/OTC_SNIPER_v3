"""FastAPI router for advisory-only AI endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from pydantic import BaseModel, Field

from ..models.ai_models import AIChatRequest, AIChatResponse, AIImageRequest, AIImageResponse, AIStatusResponse, AIUsage
from ..services.ai_service import get_ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger("otc_sniper.ai")


@router.get("/status", response_model=AIStatusResponse)
async def ai_status() -> AIStatusResponse:
    return get_ai_service().status()


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(request: AIChatRequest) -> AIChatResponse:
    service = get_ai_service()
    status = service.status()
    if not status.enabled:
        raise HTTPException(status_code=503, detail=status.reason or "AI is unavailable.")

    try:
        result = await service.chat(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("AI chat failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    usage = AIUsage(**result.usage) if result.usage else None
    return AIChatResponse(provider=result.provider, model=result.model, response=result.text, usage=usage)


@router.post("/analyze-image", response_model=AIImageResponse)
async def ai_analyze_image(request: AIImageRequest) -> AIImageResponse:
    service = get_ai_service()
    status = service.status()
    if not status.enabled:
        raise HTTPException(status_code=503, detail=status.reason or "AI is unavailable.")

    try:
        result = await service.analyze_image(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("AI image analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    usage = AIUsage(**result.usage) if result.usage else None
    return AIImageResponse(provider=result.provider, model=result.model, analysis=result.text, usage=usage)


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=15000, description="Text to synthesize")
    voice_id: str | None = Field(None, description="Grok voice id (eve, ara, rex, sal, leo or custom)")
    language: str = Field("en", description="BCP-47 language code or 'auto'")
    speed: float = Field(1.0, ge=0.7, le=1.5)
    profile_key: str | None = Field(None, description="Optional AI profile to resolve voice from")
    output_format: dict[str, Any] | None = None


@router.post("/speak")
async def ai_speak(request: SpeakRequest) -> Response:
    """
    Native Grok TTS proxy.
    Returns raw audio (default MP3). Use in <audio> element after proxying.
    Respects active AI profile voice settings when profile_key or no explicit voice_id.
    """
    service = get_ai_service()
    status = service.status()
    if not status.enabled:
        raise HTTPException(status_code=503, detail=status.reason or "AI is unavailable.")

    voice_config: dict[str, Any] = {}
    if request.profile_key:
        try:
            from ..services.ai_config import get_effective_voice_for_feature
            voice_config = get_effective_voice_for_feature(request.profile_key)
        except Exception:
            pass

    if request.voice_id:
        voice_config["provider"] = "grok"
        voice_config["voiceId"] = request.voice_id
    if request.language:
        voice_config["language"] = request.language
    if request.speed is not None:
        voice_config["speed"] = request.speed

    try:
        audio_bytes = await service.text_to_speech(request.text, voice_config or None)
    except RuntimeError as exc:
        # e.g. non-grok provider requested
        logger.info("Falling back or error in TTS: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Grok TTS failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="TTS generation failed") from exc

    # Default to audio/mpeg for MP3; client can inspect or we can improve with content-type from response later
    return Response(content=audio_bytes, media_type="audio/mpeg")