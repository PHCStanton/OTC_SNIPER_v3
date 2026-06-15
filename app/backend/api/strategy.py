from __future__ import annotations

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


class RuntimeStrategyConfigRequest(BaseModel):
    oteo_level2_enabled: bool = Field(default=False)
    oteo_level3_enabled: bool = Field(default=False)
    oteo_ai_enabled: bool = Field(default=False)
    oteo_ai_execution_mode: str = Field(default="advisory")
    auto_ghost_enabled: bool = Field(default=False)
    auto_ghost_amount: float = Field(default=1.0, gt=0)
    auto_ghost_expiration_seconds: int = Field(default=60, ge=5, le=3600)
    auto_ghost_max_concurrent_trades: int = Field(default=3, ge=1, le=20)
    auto_ghost_per_asset_cooldown_seconds: int = Field(default=30, ge=0, le=3600)
    auto_ghost_max_session_trades: int = Field(default=100, ge=1, le=10000)
    auto_ghost_max_drawdown_amount: float = Field(default=0.0, ge=0)
    auto_ghost_drawdown_cooldown_seconds: int = Field(default=300, ge=0, le=36000)
    auto_ghost_minimum_payout: float = Field(default=0.88, ge=0.0, le=1.0)
    auto_ghost_manipulation_severity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    auto_ghost_block_on_manipulation: bool = Field(default=True)
    auto_ghost_min_confidence_enabled: bool = Field(default=False)
    auto_ghost_min_confidence: float | None = Field(default=None)
    auto_ghost_max_confidence_enabled: bool = Field(default=False)
    auto_ghost_max_confidence: float | None = Field(default=None)
    auto_ghost_max_trades_per_timeframe: int = Field(default=0, ge=0, le=100)
    auto_ghost_timeframe_seconds: int = Field(default=0, ge=0, le=3600)
    auto_ghost_min_zscore_enabled: bool = Field(default=False)
    auto_ghost_min_zscore: float | None = Field(default=None)
    auto_ghost_max_zscore_enabled: bool = Field(default=False)
    auto_ghost_max_zscore: float | None = Field(default=None)
    auto_ghost_regime_gate_enabled: bool = Field(default=False)
    auto_ghost_allowed_regimes: list[str] | None = Field(default=None)
    auto_ghost_require_regime_stable: bool = Field(default=False)


@router.get("/runtime-config")
async def get_runtime_config(request: Request) -> JSONResponse:
    streaming_service = request.app.state.streaming_service
    return JSONResponse(
        content={
            "ok": True,
            "oteo_level2_enabled": streaming_service.level2_enabled,
            "oteo_level3_enabled": streaming_service.level3_enabled,
            "oteo_ai_enabled": streaming_service.oteo_ai_enabled,
            "oteo_ai_execution_mode": streaming_service.oteo_ai_execution_mode,
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
            oteo_ai_enabled=body.oteo_ai_enabled,
            oteo_ai_execution_mode=body.oteo_ai_execution_mode,
            auto_ghost_enabled=body.auto_ghost_enabled,
            auto_ghost_amount=body.auto_ghost_amount,
            auto_ghost_expiration_seconds=body.auto_ghost_expiration_seconds,
            auto_ghost_max_concurrent_trades=body.auto_ghost_max_concurrent_trades,
            auto_ghost_per_asset_cooldown_seconds=body.auto_ghost_per_asset_cooldown_seconds,
            auto_ghost_max_session_trades=body.auto_ghost_max_session_trades,
            auto_ghost_max_drawdown_amount=body.auto_ghost_max_drawdown_amount,
            auto_ghost_drawdown_cooldown_seconds=body.auto_ghost_drawdown_cooldown_seconds,
            auto_ghost_minimum_payout_pct=body.auto_ghost_minimum_payout * 100.0,
            auto_ghost_manipulation_severity_threshold=body.auto_ghost_manipulation_severity_threshold,
            auto_ghost_block_on_manipulation=body.auto_ghost_block_on_manipulation,
            auto_ghost_min_confidence_enabled=body.auto_ghost_min_confidence_enabled,
            auto_ghost_min_confidence=body.auto_ghost_min_confidence,
            auto_ghost_max_confidence_enabled=body.auto_ghost_max_confidence_enabled,
            auto_ghost_max_confidence=body.auto_ghost_max_confidence,
            auto_ghost_max_trades_per_timeframe=body.auto_ghost_max_trades_per_timeframe,
            auto_ghost_timeframe_seconds=body.auto_ghost_timeframe_seconds,
            auto_ghost_min_zscore_enabled=body.auto_ghost_min_zscore_enabled,
            auto_ghost_min_zscore=body.auto_ghost_min_zscore,
            auto_ghost_max_zscore_enabled=body.auto_ghost_max_zscore_enabled,
            auto_ghost_max_zscore=body.auto_ghost_max_zscore,
            auto_ghost_regime_gate_enabled=body.auto_ghost_regime_gate_enabled,
            auto_ghost_allowed_regimes=body.auto_ghost_allowed_regimes,
            auto_ghost_require_regime_stable=body.auto_ghost_require_regime_stable,
        )
        return JSONResponse(content={"ok": True, **config})
    except Exception as exc:
        logger.error("Failed to update runtime config: %s", exc)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


@router.get("/ai-review")
async def get_ai_review(request: Request, asset: str | None = None) -> JSONResponse:
    """
    Get the latest AI regime review result.

    Query params:
        asset (optional): filter to a specific asset.

    Returns:
        {
            "available": bool,          # True when AI review service is attached
            "running": bool,            # True when the review loop is active
            "review": dict | None,      # Latest review result, or None
            "all_reviews": dict         # All per-asset reviews (when asset not specified)
        }
    """
    streaming_service = request.app.state.streaming_service
    ai_review = getattr(streaming_service, "_ai_review", None)

    if ai_review is None:
        return JSONResponse(content={
            "available": False,
            "running": False,
            "review": None,
            "all_reviews": {},
        })

    review = ai_review.get_last_review(asset)
    all_reviews = ai_review.get_all_reviews() if asset is None else {}

    return JSONResponse(content={
        "available": True,
        "running": bool(ai_review._running),
        "review": review,
        "all_reviews": all_reviews,
    })
