#!/usr/bin/env python3
"""
OTC SNIPER — Redis Streaming Gateway (port 3001)
=================================================
Replaces the legacy Flask-SocketIO streaming_server.py.

Architecture:
    QuFLX v2 Collector
        │ PUBLISH
        ▼
    Redis (localhost:6379)  ←── shared with QuFLX v2 main gateway
        │ SUBSCRIBE (market_data channel)
        ▼
    RedisPubSubListener  (quflx_redis_streaming package)
        │
        ▼
    enrichment_handler()  ← runs OTEO + ManipulationDetector per asset
        │
        ▼
    SocketIOBridge  (quflx_redis_streaming package)
        │ Socket.IO  market_data:{asset} room
        ▼
    React Frontend (port 5175)
        TradingPlatform.jsx  listens for 'market_data' event

Key design decisions:
  - One OTEO + ManipulationDetector engine pair per asset, created on first tick.
  - Engines are stored in a module-level dict — safe because this is a single-process
    async server (no threading).
  - focus_asset Socket.IO event → room join/leave (drop-in for legacy server).
  - If Redis is unavailable at startup the listener retries with exponential backoff
    (handled inside RedisPubSubListener._run_with_backoff).
  - Windows ProactorEventLoop is set at module level so uvicorn works correctly.

Usage:
    uvicorn ssid.web_app.backend.data_streaming.redis_gateway:socket_app \\
        --host 0.0.0.0 --port 3001

    Or from the ssid/web_app/backend directory:
    uvicorn data_streaming.redis_gateway:socket_app --host 0.0.0.0 --port 3001
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import os
import time
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

# ── Load environment variables from .env file ─────────────────────────────────
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parents[2] / ".env"  # ssid/web_app/.env
load_dotenv(dotenv_path=_env_path)

# ── CORS origins from environment ─────────────────────────────────────────────
_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
    ).split(",")
    if origin.strip()
]

# ── Gateway Port ──────────────────────────────────────────────────────────────
_GATEWAY_PORT = int(os.environ.get("STREAM_PORT", "3001"))

# ── Windows event loop policy (must be set before any asyncio usage) ──────────
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Path setup — allow running from any working directory ─────────────────────
_BACKEND_DIR = Path(__file__).resolve().parents[1]   # ssid/web_app/backend
_SRC_DIR = _BACKEND_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ── Analysis engines ──────────────────────────────────────────────────────────
try:
    # Add project root to path to find auth and credentials modules
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
    if PROJECT_ROOT not in sys.path:
        sys.path.append(PROJECT_ROOT)
    from oteo_indicator import OTEO
    from manipulation_detector import ManipulationDetector
    from asset_utils import normalize_asset  # FIX-2: shared normalization
    from tick_logger import TickLogger        # A3: tick logging
    from signal_logger import SignalLogger    # A4: signal logging
    _ENGINES_AVAILABLE = True
except ImportError as _import_err:
    logging.getLogger(__name__).error(
        "Could not import OTEO, ManipulationDetector, or asset_utils: %s — "
        "enrichment will be skipped and raw ticks forwarded.",
        _import_err,
    )
    OTEO = None  # type: ignore[assignment,misc]
    ManipulationDetector = None  # type: ignore[assignment,misc]
    TickLogger = None  # type: ignore[assignment,misc]
    SignalLogger = None  # type: ignore[assignment,misc]
    _ENGINES_AVAILABLE = False

    def normalize_asset(raw: str) -> str:  # type: ignore[misc]
        """Fallback no-op normalization when asset_utils import fails."""
        if not raw:
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", str(raw)).upper()

# ── Redis streaming package ───────────────────────────────────────────────────
from quflx_redis_streaming import (
    RedisClient,
    RedisConfig,
    RedisPubSubListener,
    SocketIOBridge,
    SocketIOConfig,
    StatusProbe,
)

# ── Ops router (process control endpoints) ────────────────────────────────────
from data_streaming.ops import router as ops_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("redis_gateway")

# ── Redis / Socket.IO setup ───────────────────────────────────────────────────
_redis_config = RedisConfig()   # defaults: host=localhost, port=6379, db=0
_redis_client = RedisClient(_redis_config)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=_CORS_ORIGINS,
)

_sio_config = SocketIOConfig()  # market_event="market_data", room_template="market_data:{asset}"
_bridge = SocketIOBridge(sio, _sio_config)
_status_probe = StatusProbe(_redis_client.client)

# ── Per-asset engine registry ─────────────────────────────────────────────────
# Structure: { asset_id: {"oteo": OTEO, "detector": ManipulationDetector} }
_asset_engines: Dict[str, Dict[str, Any]] = {}

# ── Per-asset tick counters for warmup tracking ───────────────────────────────
_asset_tick_counts: Dict[str, int] = {}

# ── Data directory + loggers (A3, A4) ────────────────────────────────────────
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"  # ssid/web_app/data

# Instantiate loggers only when engines are available (imports succeeded)
_tick_logger: "TickLogger | None" = (
    TickLogger(base_dir=_DATA_DIR / "tick_logs") if _ENGINES_AVAILABLE and TickLogger else None
)
_signal_logger: "SignalLogger | None" = (
    SignalLogger(base_dir=_DATA_DIR / "signals") if _ENGINES_AVAILABLE and SignalLogger else None
)

# C1: Ghost Trader
from ghost_trader import GhostTrader
_ghost_trader = GhostTrader(data_dir=_DATA_DIR)

# C5: Settings Manager
from settings_manager import SettingsManager
_settings_manager = SettingsManager(data_dir=_DATA_DIR)

# To hold current prices for checking expiries
_current_prices: Dict[str, float] = {}


def _get_or_create_engines(asset: str) -> Dict[str, Any] | None:
    """Return (or lazily create) the OTEO + ManipulationDetector pair for an asset."""
    if not _ENGINES_AVAILABLE:
        return None
    if asset not in _asset_engines:
        logger.info("Creating analysis engines for asset: %s", asset)
        oteo = OTEO()
        
        # Pre-seed from tick logs if available
        recent_ticks = []
        if _tick_logger is not None:
            recent_ticks = _tick_logger.load_recent(asset, max_ticks=300)
            if recent_ticks:
                for tick_data in recent_ticks:
                    oteo.update_tick(float(tick_data["p"]), timestamp=float(tick_data["t"]))
                logger.info("Pre-seeded OTEO for %s with %d historical ticks", asset, len(recent_ticks))
        
        _asset_engines[asset] = {
            "oteo": oteo,
            "detector": ManipulationDetector(),
        }
        _asset_tick_counts[asset] = len(recent_ticks)
    return _asset_engines[asset]


def _clear_detector_buffers(asset: str) -> None:
    """
    FIX-8 (ISSUE-5): Clear ONLY ManipulationDetector buffers on focus switch.

    Previously cleared ALL OTEO data (ticks, tick count) which forced a full
    re-warmup every time the user switched back to an asset. Now we preserve
    the OTEO tick buffer so warmup progress is retained across focus switches.

    Only ManipulationDetector buffers are cleared — they are velocity/price
    windows that could cross-contaminate if carried over from a different asset.
    """
    if asset not in _asset_engines:
        return
    detector = _asset_engines[asset].get("detector")
    if detector is None:
        return
    # Debugger BUG-B: Defensive attribute access — ManipulationDetector interface
    # may change; log a warning instead of raising AttributeError silently.
    for attr in ("velocities", "price_history"):
        buf = getattr(detector, attr, None)
        if buf is not None:
            try:
                buf.clear()
            except Exception as exc:
                logger.error("Could not clear detector.%s for %s: %s", attr, asset, exc)
                raise RuntimeError(f"ManipulationDetector buffer clear failed for {asset}") from exc
        else:
            logger.warning("ManipulationDetector has no attribute '%s' — skipping clear", attr)
    logger.info("Cleared detector buffers for asset: %s (OTEO warmup preserved)", asset)


# ── Enrichment handler and helpers ─────────────────────────────────────────────

async def _process_tick_and_signals(
    asset: str,
    tick_timestamp: float,
    price: float,
    volume: float,
    source: str,
    payload: Dict[str, Any],
    oteo_result: Any,
    manipulation: Dict[str, Any]
) -> None:
    """Helper to handle tick logging, signal logging, and ghost trade entry."""
    # A3: Log tick to JSONL file
    if _tick_logger is not None:
        try:
            _tick_logger.write_tick(asset, {
                "t": tick_timestamp,
                "p": price,
                "a": asset,
                "v": volume,
                "b": source,
            })
        except Exception as _tl_err:
            logger.error("TickLogger write failed for %s: %s", asset, _tl_err)
            raise RuntimeError(f"TickLogger write failed for {asset}") from _tl_err

    # A4: Log signal if confidence is MEDIUM or HIGH
    if _signal_logger is not None and isinstance(oteo_result, dict):
        conf = oteo_result.get("confidence", "LOW")
        if conf in ("HIGH", "MEDIUM"):
            manip_active = bool(
                manipulation and (
                    manipulation.get("push_snap") or manipulation.get("pinning")
                )
            )
            try:
                _signal_logger.log_signal({
                    "t": tick_timestamp,
                    "asset": asset,
                    "score": oteo_result["oteo_score"],
                    "dir": oteo_result["recommended"],
                    "conf": conf,
                    "price": price,
                    "vel": oteo_result.get("velocity", 0.0),
                    "z": oteo_result.get("z_score", 0.0),
                    "maturity": oteo_result.get("maturity", 1.0),
                    "manip": manip_active,
                    "broker": source,
                })
                
                # C1: Evaluate ghost trade entry (only for HIGH confidence)
                global_settings = _settings_manager.get_global()
                ghost_enabled = global_settings.get("ghost_trading", {}).get("enabled", False)
                
                if ghost_enabled and conf == "HIGH" and not payload.get("suppressed", False):
                    default_amount = global_settings.get("ghost_trading", {}).get("default_amount", 10.0)
                    _ghost_trader.default_amount = default_amount
                    
                    gt_id = _ghost_trader.on_signal(
                        asset=asset,
                        direction=oteo_result["recommended"],
                        price=price,
                        oteo_score=oteo_result["oteo_score"],
                        expiry=60,
                        confidence=conf,
                        velocity=oteo_result.get("velocity", 0.0),
                        z_score=oteo_result.get("z_score", 0.0),
                        manipulation=manipulation,
                        broker=source
                    )
                    if gt_id:
                        payload["ghost_trade_id"] = gt_id
                        await sio.emit("ghost_trade_entered", _ghost_trader.active_trades[gt_id])
                        
            except Exception as _sl_err:
                logger.error("SignalLogger/GhostTrader write failed for %s: %s", asset, _sl_err)
                raise RuntimeError(f"SignalLogger/GhostTrader write failed for {asset}") from _sl_err


async def enrichment_handler(channel: str, payload: Dict[str, Any]) -> None:
    """
    Middleware between RedisPubSubListener and SocketIOBridge.

    For market_data ticks:
      1. Normalize asset name to consistent format (FIX BUG-2)
      2. Run OTEO engine → add oteo_score, recommended, confidence fields.
      3. Run ManipulationDetector → add manipulation flags dict.
      4. Emit warmup_status every 10 ticks (or when ready).
      5. Forward enriched payload to SocketIOBridge (which emits to the
         correct asset room via Socket.IO).

    For all other channels (trading:signals, system_status):
      Pass through to SocketIOBridge unchanged.
    """
    if channel == "market_data":
        raw_asset = payload.get("asset")
        price = payload.get("price")

        if raw_asset and price is not None:
            # FIX BUG-2: Normalize asset name for consistent room matching
            asset = normalize_asset(raw_asset)
            if not asset:
                logger.warning("Could not normalize asset: %s", raw_asset)
                return

            engines = _get_or_create_engines(asset)

            # A1: extract tick timestamp for time-aware velocity
            tick_timestamp = float(payload.get("timestamp", time.time()))

            if engines:
                # A1: pass timestamp to OTEO for time-aware velocity calculation
                # OTEO scoring — returns dict once warmed up (≥50 ticks), float during warmup
                oteo_result = engines["oteo"].update_tick(float(price), timestamp=tick_timestamp)
                if isinstance(oteo_result, dict):
                    payload["oteo_score"] = oteo_result.get("oteo_score", 50.0)
                    payload["recommended"] = oteo_result.get("recommended", "CALL")
                    payload["action"] = oteo_result.get("recommended", "CALL")  # alias
                    payload["confidence"] = oteo_result.get("confidence", "LOW")
                    payload["maturity"] = oteo_result.get("maturity", 1.0)  # A1-O2
                else:
                    # Warmup period — use neutral defaults
                    payload["oteo_score"] = float(oteo_result) if oteo_result is not None else 50.0
                    payload["recommended"] = "CALL"
                    payload["action"] = "CALL"
                    payload["confidence"] = "LOW"
                    payload["maturity"] = 0.0

                # Manipulation detection
                manipulation = engines["detector"].update(tick_timestamp, float(price))
                payload["manipulation"] = manipulation
                
                # C4: Keep track of current prices for GhostTrader
                _current_prices[asset] = float(price)
                
                # C1, C4: Check expiries
                completed_trades = _ghost_trader.check_expiries(_current_prices)
                if completed_trades:
                    # Emit ghost trade completions
                    await sio.emit("ghost_trade_completed", {"trades": completed_trades})

                # B2: Manipulation-aware signal suppression
                if manipulation and isinstance(oteo_result, dict):
                    if manipulation.get("push_snap") or manipulation.get("pinning"):
                        current_conf = payload.get("confidence", "LOW")
                        if current_conf == "HIGH":
                            payload["confidence"] = "MEDIUM"
                            payload["suppressed"] = True
                            payload["suppression_reason"] = "manipulation_detected"
                            oteo_result["confidence"] = "MEDIUM"
                        elif current_conf == "MEDIUM":
                            payload["confidence"] = "LOW"
                            payload["suppressed"] = True
                            payload["suppression_reason"] = "manipulation_detected"
                            oteo_result["confidence"] = "LOW"

                # Extracted A3, A4, and C1 logic to a helper function
                await _process_tick_and_signals(
                    asset=asset,
                    tick_timestamp=tick_timestamp,
                    price=float(price),
                    volume=float(payload.get("volume", 0.0)),
                    source=payload.get("source", "pocket_option"),
                    payload=payload,
                    oteo_result=oteo_result,
                    manipulation=manipulation
                )

                # Track tick count and emit warmup status periodically
                _asset_tick_counts[asset] = _asset_tick_counts.get(asset, 0) + 1
                tick_count = _asset_tick_counts[asset]
                room = f"market_data:{asset}"

                # Update payload with normalized asset name for frontend
                payload["asset"] = asset

                # Emit warmup status every 10 ticks or when ready
                if tick_count % 10 == 0 or tick_count == 50:
                    await sio.emit(
                        "warmup_status",
                        {
                            "asset": asset,
                            "ready": tick_count >= 50,
                            "ticks_received": tick_count,
                        },
                        room=room,
                    )
            else:
                # Engines unavailable — set safe defaults so frontend doesn't break
                payload.setdefault("oteo_score", 50.0)
                payload.setdefault("recommended", "CALL")
                payload.setdefault("action", "CALL")
                payload.setdefault("manipulation", {})
                payload["asset"] = asset

    # Forward to SocketIOBridge for room-scoped Socket.IO emission
    await _bridge.handle_message(channel, payload)


# ── Listener (uses enrichment_handler instead of bridge.handle_message) ───────
_listener = RedisPubSubListener(_redis_client, enrichment_handler)


# ── Socket.IO event handlers ──────────────────────────────────────────────────

@sio.event
async def connect(sid: str, environ: dict) -> None:
    """New client connected — initialise empty session."""
    logger.info("🟢 Client connected: %s", sid)
    await sio.save_session(sid, {"rooms": []})
    await sio.emit("status", {"status": "connected"}, to=sid)


@sio.event
async def disconnect(sid: str) -> None:
    """Client disconnected — Socket.IO cleans up rooms automatically."""
    logger.info("🔴 Client disconnected: %s", sid)


@sio.event
async def focus_asset(sid: str, data: dict) -> None:
    """
    Drop-in replacement for the legacy streaming_server.py focus_asset handler.

    Translates the frontend's `focus_asset` emit into a room join/leave so the
    client only receives ticks for the selected asset.

    Also clears tick buffers for the new asset to ensure no cross-contamination
    from previous asset data.

    FIX BUG-2: Normalizes the incoming asset name to match collector format,
    ensuring the client joins the correct room regardless of how the frontend
    sends the asset ID.

    Frontend emits:  socket.emit('focus_asset', { asset: 'AUDNZDOTC' })
    Server action:   leave old market_data:{prev} room, join market_data:{asset},
                     clear tick buffers, emit warmup_status
    """
    raw_asset = data.get("asset") if isinstance(data, dict) else None
    if not raw_asset:
        logger.warning("focus_asset received with no asset field from %s", sid)
        return

    # FIX BUG-2: Normalize asset name so room matching is consistent
    asset = normalize_asset(raw_asset)
    if not asset:
        logger.warning("Could not normalize asset: %s", raw_asset)
        return

    session = await sio.get_session(sid)
    old_rooms = session.get("rooms", [])

    # Leave all previously joined asset rooms
    for old_room in old_rooms:
        await sio.leave_room(sid, old_room)

    # Join the new asset room using normalized name
    room = f"market_data:{asset}"
    await sio.enter_room(sid, room)
    await sio.save_session(sid, {"rooms": [room]})

    # FIX-8: Clear only ManipulationDetector buffers — OTEO warmup is preserved
    _clear_detector_buffers(asset)

    logger.info("🎯 %s → room %s (detector buffers cleared, OTEO preserved, normalized from '%s')", sid, room, raw_asset)
    await sio.emit("status", {"status": "focused", "asset": asset}, to=sid)

    # Emit initial warmup status for the newly focused asset
    tick_count = _asset_tick_counts.get(asset, 0)
    await sio.emit(
        "warmup_status",
        {
            "asset": asset,
            "ready": tick_count >= 50,
            "ticks_received": tick_count,
        },
        to=sid,
    )


@sio.event
async def watch_assets(sid: str, data: dict) -> None:
    """
    Join multiple asset rooms for multi-chart view.
    
    Client emits: socket.emit('watch_assets', { assets: ['EURUSD', 'AUDNZD', 'GBPJPY'] })
    Server action: leave all old rooms, join up to 9 new rooms.
    """
    raw_assets = data.get("assets", []) if isinstance(data, dict) else []
    if not raw_assets or not isinstance(raw_assets, list):
        logger.warning("watch_assets: invalid or empty assets list from %s", sid)
        return
    
    session = await sio.get_session(sid)
    for old_room in session.get("rooms", []):
        await sio.leave_room(sid, old_room)
    
    new_rooms = []
    for raw_asset in raw_assets[:9]:  # Cap at 9 for performance
        asset = normalize_asset(str(raw_asset))
        if not asset:
            continue
        room = f"market_data:{asset}"
        await sio.enter_room(sid, room)
        new_rooms.append(room)
        _clear_detector_buffers(asset)
    
    await sio.save_session(sid, {"rooms": new_rooms})
    logger.info("👁️ %s watching %d assets: %s", sid, len(new_rooms), new_rooms)


@sio.event
async def join_room(sid: str, data: dict) -> None:
    """
    Explicit room join (used by advanced consumers / monitor dashboards).

    Emits:  socket.emit('join_room', { room: 'market_data:EURUSD' })
    """
    room = data.get("room") if isinstance(data, dict) else None
    if not room:
        return

    session = await sio.get_session(sid)
    for old_room in session.get("rooms", []):
        await sio.leave_room(sid, old_room)

    await sio.enter_room(sid, room)
    await sio.save_session(sid, {"rooms": [room]})
    logger.info("📌 %s joined room %s", sid, room)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.

    Startup:  verify Redis connectivity, launch pub/sub listener task.
    Shutdown: stop listener, close Redis connection.
    """
    # Startup
    logger.info("🚀 Redis Gateway starting on port %d...", _GATEWAY_PORT)
    logger.info("   Redis: %s:%s db=%s", _redis_config.host, _redis_config.port, _redis_config.db)
    logger.info("   Channels: %s", ", ".join(_redis_config.channels))
    logger.info("   Analysis engines: %s", "enabled" if _ENGINES_AVAILABLE else "DISABLED (import failed)")

    # Quick connectivity check — non-fatal, listener will retry with backoff
    try:
        probe = await _status_probe.snapshot()
        if probe.get("redis") == "ok":
            logger.info("✅ Redis ping OK")
        else:
            logger.warning("⚠️  Redis ping failed — listener will retry automatically")
    except Exception as probe_err:
        logger.warning("⚠️  Redis probe error: %s — listener will retry automatically", probe_err)

    asyncio.create_task(_listener.start())

    # A3: Tick log cleanup task — runs every 5 minutes, moves expired files to archive/
    if _tick_logger is not None:
        async def _cleanup_loop() -> None:
            while True:
                await asyncio.sleep(300)  # every 5 minutes
                try:
                    count = _tick_logger.cleanup_expired()
                    if count > 0:
                        logger.info("TickLogger: archived %d expired file(s)", count)
                except Exception as _cl_err:
                    logger.error("TickLogger cleanup error: %s", _cl_err)
                    raise RuntimeError("TickLogger cleanup failed") from _cl_err

        asyncio.create_task(_cleanup_loop())
        logger.info("✅ Tick log cleanup task started (interval: 5 min)")

    yield  # ← application runs here

    # Shutdown
    logger.info("🛑 Redis Gateway shutting down...")
    await _listener.stop()
    await _redis_client.close()
    logger.info("✅ Shutdown complete.")


# ── FastAPI app ───────────────────────────────────────────────────────────────

_app = FastAPI(
    title="OTC SNIPER — Redis Streaming Gateway",
    description="Redis Pub/Sub → Socket.IO bridge with OTEO + ManipulationDetector enrichment",
    version="1.0.0",
    lifespan=lifespan,
)

_app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from auth.middleware import require_role
from fastapi import Depends

# Mount ops router for process control (Chrome, Collector start/stop)
# Requires QFLX_ENABLE_OPS=1 env var + localhost + optional X-QFLX-OPS-TOKEN header
# We could add dependencies=[Depends(require_role("admin"))] here, but ops router already has custom token check
_app.include_router(ops_router, dependencies=[Depends(require_role("admin"))])

# Mount Auth Router (E1)
try:
    from api_wrapper.auth_router import router as auth_router
    _app.include_router(auth_router)
except ImportError as e:
    logger.warning(f"Could not import auth router: {e}")

# Mount Settings Router (C5)
import sys
_API_WRAPPER_DIR = _BACKEND_DIR / "api_wrapper"
if str(_API_WRAPPER_DIR) not in sys.path:
    sys.path.insert(0, str(_API_WRAPPER_DIR))
try:
    from settings_router import router as settings_router
    _app.include_router(settings_router, dependencies=[Depends(require_role("admin"))])
except ImportError as e:
    logger.warning(f"Could not import settings router: {e}")

# Ghost Stats Router (C3)
from fastapi import APIRouter
from fastapi.responses import JSONResponse
ghost_router = APIRouter(prefix="/api/ghost", tags=["Ghost Trading"])
@ghost_router.get("/stats")
async def get_ghost_stats(asset: str = None):
    if asset:
        return _ghost_trader.get_asset_stats(asset)
    return _ghost_trader.get_session_stats()
@ghost_router.get("/active")
async def get_active_ghost_trades():
    return list(_ghost_trader.active_trades.values())
_app.include_router(ghost_router)

@_app.get("/status")
async def status() -> dict:
    """Redis connectivity + engine status."""
    probe = await _status_probe.snapshot()
    return {
        **probe,
        "engines_available": _ENGINES_AVAILABLE,
        "active_assets": list(_asset_engines.keys()),
        "port": _GATEWAY_PORT,
    }


@_app.get("/health")
async def health() -> dict:
    """Lightweight liveness probe."""
    return {"ok": True}


# ── ASGI app (Socket.IO wraps FastAPI) ────────────────────────────────────────
# This is the entry point for uvicorn:
#   uvicorn data_streaming.redis_gateway:socket_app --port 3001
socket_app = socketio.ASGIApp(sio, _app)
