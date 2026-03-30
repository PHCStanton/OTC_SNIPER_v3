"""FastAPI router for advisory-only AI endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

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