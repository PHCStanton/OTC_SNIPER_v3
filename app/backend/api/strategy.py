from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class RuntimeStrategyConfigRequest(BaseModel):
    oteo_level2_enabled: bool = Field(default=False)
    oteo_level3_enabled: bool = Field(default=False)
    auto_ghost_enabled: bool = Field(default=False)
    auto_ghost_amount: float = Field(default=1.0, gt=0)
    auto_ghost_expiration_seconds: int = Field(default=60, ge=5, le=3600)
    auto_ghost_max_concurrent_trades: int = Field(default=3, ge=1, le=20)
    auto_ghost_per_asset_cooldown_seconds: int = Field(default=30, ge=0, le=3600)
    auto_ghost_max_session_trades: int = Field(default=100, ge=1, le=10000)
    auto_ghost_max_drawdown_amount: float = Field(default=0.0, ge=0)
    auto_ghost_drawdown_cooldown_seconds: int = Field(default=300, ge=0, le=36000)
    auto_ghost_minimum_payout: float = Field(default=0.88, ge=0.0, le=1.0)


@router.get("/runtime-config")
async def get_runtime_config(request: Request) -> JSONResponse:
    streaming_service = request.app.state.streaming_service
    return JSONResponse(
        content={
            "ok": True,
            "oteo_level2_enabled": streaming_service.level2_enabled,
            "oteo_level3_enabled": streaming_service.level3_enabled,
            **streaming_service.auto_ghost.status,
        }
    )


@router.post("/runtime-config")
async def update_runtime_config(body: RuntimeStrategyConfigRequest, request: Request) -> JSONResponse:
    try:
        streaming_service = request.app.state.streaming_service
        config = streaming_service.update_runtime_settings(
            level2_enabled=body.oteo_level2_enabled,
            level3_enabled=body.oteo_level3_enabled,
            auto_ghost_enabled=body.auto_ghost_enabled,
            auto_ghost_amount=body.auto_ghost_amount,
            auto_ghost_expiration_seconds=body.auto_ghost_expiration_seconds,
            auto_ghost_max_concurrent_trades=body.auto_ghost_max_concurrent_trades,
            auto_ghost_per_asset_cooldown_seconds=body.auto_ghost_per_asset_cooldown_seconds,
            auto_ghost_max_session_trades=body.auto_ghost_max_session_trades,
            auto_ghost_max_drawdown_amount=body.auto_ghost_max_drawdown_amount,
            auto_ghost_drawdown_cooldown_seconds=body.auto_ghost_drawdown_cooldown_seconds,
            auto_ghost_minimum_payout_pct=body.auto_ghost_minimum_payout * 100.0,
        )
        return JSONResponse(content={"ok": True, **config})
    except Exception as exc:
        logger.error("Failed to update runtime config: %s", exc)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})
