"""
FastAPI + Socket.IO entrypoint for OTC SNIPER v3.

Phase 0 additions:
  - ops router  (Chrome lifecycle: /api/ops/*)
  - session router (SSID connect/disconnect/status: /api/session/*)
  - check_status Socket.IO event (Chrome + session state, polled every 5 s by frontend)

The inline /api/session/* route handlers that previously lived here have been
removed — they are now owned by api/session.py (single source of truth).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

import socketio
from fastapi import FastAPI, HTTPException

from .api.ops import _is_port_open, router as ops_router
from .api.session import router as session_router
from .api.trading import router as trading_router
from .brokers.base import BrokerType
from .brokers.pocket_option.adapter import PocketOptionAdapter  # noqa: F401 — triggers registration
from .brokers.registry import BrokerRegistry
from .config import get_settings
from .dependencies import get_data_repository, get_session_manager
from .models.requests import ConnectBrokerRequest
from .models.responses import (
    BrokerActionResponse,
    BrokerListResponse,
    DataStatsResponse,
    HealthResponse,
)
from .services.streaming import StreamingService
from .session.pocket_option_session import PocketOptionSession

# ── Socket.IO setup ───────────────────────────────────────────────────────────
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
streaming_service = StreamingService(sio_server=sio)

# Hook live broker ticks into the streaming pipeline
PocketOptionSession.set_tick_callback(streaming_service.process_tick)


# ── Socket.IO event handlers ──────────────────────────────────────────────────

@sio.event
async def connect(sid, environ):
    await sio.save_session(sid, {"rooms": []})
    await sio.emit("status", {"status": "connected"}, to=sid)


@sio.event
async def focus_asset(sid, data):
    asset = data.get("asset")
    if not asset:
        return

    session = await sio.get_session(sid)
    for room in session.get("rooms", []):
        await sio.leave_room(sid, room)

    room = f"market_data:{asset}"
    await sio.enter_room(sid, room)
    await sio.save_session(sid, {"rooms": [room]})
    streaming_service.clear_detector_buffers(asset)
    await sio.emit("status", {"status": "focused", "asset": asset}, to=sid)


@sio.event
async def watch_assets(sid, data):
    assets = data.get("assets", [])
    if not assets:
        return

    session = await sio.get_session(sid)
    for room in session.get("rooms", []):
        await sio.leave_room(sid, room)

    new_rooms = []
    for asset in assets[:9]:
        room = f"market_data:{asset}"
        await sio.enter_room(sid, room)
        new_rooms.append(room)
        streaming_service.clear_detector_buffers(asset)

    await sio.save_session(sid, {"rooms": new_rooms})


@sio.event
async def check_status(sid, _data=None):
    """
    Phase 0 — Combined Chrome + session status event.

    Frontend polls this every 5 seconds to drive TopBar badge state.
    Chrome status and session status are always reported as separate fields:
      - chrome.running  → debug port 9222 is accepting connections
      - session.connected → authenticated Pocket Option WebSocket is live

    These are distinct states. Chrome running does NOT imply session connected.
    """
    settings = get_settings()

    # Probe Chrome debug port live (never stale) — reuses _is_port_open from ops.py
    chrome_running = _is_port_open("127.0.0.1", settings.chrome_port)

    # Session state from the singleton session manager
    sm = get_session_manager()
    snap = sm.snapshot()

    payload = {
        "chrome": {
            "running": chrome_running,
            "port": settings.chrome_port,
        },
        "session": {
            "connected": snap.connected,
            "account_type": snap.account_type,
            "is_demo": snap.is_demo,
            "balance": snap.balance,
        },
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    await sio.emit("status_update", payload, to=sid)


# ── FastAPI app ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    get_data_repository()
    yield


fastapi_app = FastAPI(title="OTC SNIPER v3", version="3.0.0", lifespan=lifespan)

# ── Routers ───────────────────────────────────────────────────────────────────
fastapi_app.include_router(ops_router)      # Phase 0: /api/ops/*
fastapi_app.include_router(session_router)  # Phase 0: /api/session/*
fastapi_app.include_router(trading_router)  # Phase 2: /api/trading/*

# Expose the Socket.IO-wrapped ASGI app for uvicorn
app = socketio.ASGIApp(sio, fastapi_app)


# ── Core endpoints ────────────────────────────────────────────────────────────

@fastapi_app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.version,
        host=settings.host,
        port=settings.port,
        enable_ops=settings.enable_ops,
        data_dir=str(settings.data_dir),
    )


@fastapi_app.get("/api/brokers", response_model=BrokerListResponse)
async def list_brokers() -> BrokerListResponse:
    return BrokerListResponse(brokers=BrokerRegistry.list_available())


@fastapi_app.get("/api/brokers/{broker}/assets")
async def broker_assets(broker: str, account_key: str = "primary"):
    try:
        broker_type = BrokerType(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown broker: {broker}") from exc

    try:
        adapter = BrokerRegistry.get_adapter(broker_type, account_key=account_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    assets = await adapter.get_assets()
    return {"broker": broker, "assets": [asset.__dict__ for asset in assets]}


@fastapi_app.post("/api/brokers/{broker}/connect", response_model=BrokerActionResponse)
async def broker_connect(
    broker: str,
    request: ConnectBrokerRequest,
    account_key: str = "primary",
) -> BrokerActionResponse:
    """
    Generic broker connect endpoint (kept for multi-broker future use).
    For Pocket Option, prefer POST /api/session/connect.
    """
    try:
        broker_type = BrokerType(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown broker: {broker}") from exc

    try:
        adapter = BrokerRegistry.get_adapter(broker_type, account_key=account_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        success = await adapter.connect({"ssid": request.ssid})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return BrokerActionResponse(
        success=success,
        broker=broker_type.value,
        message=adapter.session_manager.snapshot().message,
        connection_status=adapter.get_connection_status(),
    )


@fastapi_app.get("/api/stats/{asset}", response_model=DataStatsResponse)
async def asset_stats(asset: str) -> DataStatsResponse:
    repository = get_data_repository()
    stats = await repository.get_asset_stats(asset)
    return DataStatsResponse(**stats)
