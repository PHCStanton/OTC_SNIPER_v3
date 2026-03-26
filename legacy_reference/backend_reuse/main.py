import sys
import os
import logging
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
    ).split(",")
    if origin.strip()
]

# Add project root to path to find otc_sniper package
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../tui'))
sys.path.append(PROJECT_ROOT)

# Also add PocketOptionAPI-v2
POCKET_OPTION_API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../PocketOptionAPI-v2'))
sys.path.append(POCKET_OPTION_API_PATH)

from pathlib import Path
_SRC_DIR = Path(__file__).resolve().parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
from asset_utils import normalize_asset, to_pocket_option_format
from src.settings_manager import SettingsManager
from src.trade_manager import TradeManager

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_settings_manager = SettingsManager(data_dir=_DATA_DIR)
_trade_manager = TradeManager(_settings_manager)

# Phase E3: Refactor main.py to use BrokerRegistry
try:
    from brokers.registry import BrokerRegistry
    from brokers.base import BrokerType, TradeOrder
    
    # Pre-register Pocket Option adapter (ensure it gets registered)
    try:
        from brokers.pocket_option.adapter import PocketOptionAdapter
        BrokerRegistry.register(PocketOptionAdapter)
    except ImportError as e:
        logging.warning("Could not register PocketOptionAdapter: %s", e)
        
except ImportError as e:
    logging.warning(
        "Could not import BrokerRegistry: %s — "
        "trade execution and account connectivity will be unavailable.",
        e,
    )
    BrokerRegistry = None  # type: ignore[assignment,misc]
    BrokerType = None  # type: ignore[assignment,misc]
    TradeOrder = None  # type: ignore[assignment,misc]

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebAppBackend")


class ConnectionRequest(BaseModel):
    ssid: Optional[str] = None
    demo: bool = True


class TradeRequest(BaseModel):
    asset_id: str
    direction: str  # 'call' or 'put'
    amount: float
    expiration: int = 60
    demo: bool = True


class ConnectResponse(BaseModel):
    success: bool
    message: str
    balance: Optional[float] = None
    account_type: str  # 'demo' or 'real'


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        # FIX-11: Remove dead connections instead of silently swallowing errors.
        dead: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.debug("WebSocket send failed (%s) — marking for removal", exc)
                dead.append(connection)
        for conn in dead:
            self.disconnect(conn)


manager = ConnectionManager()


# Background task to push updates every second
async def broadcast_updates():
    while True:
        if manager.active_connections:
            state = {
                "type": "update",
                "timestamp": time.time(),
                "accounts": {},
                "active_trades": _trade_manager.get_active_trades()
            }
            if BrokerRegistry:
                for account_type in ["demo", "real"]:
                    try:
                        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
                        status = adapter.get_connection_status()
                        if status == 'connected':
                            balance = await adapter.get_balance(demo=(account_type == "demo"))
                            history = await adapter.get_trade_history(limit=20)

                            # Sync active trades with history
                            for h in history:
                                if h.get("status") != "PENDING":
                                    tid = h.get("trade_id")
                                    if tid:
                                        await _trade_manager.complete_trade(tid, {
                                            "win": h.get("status") == "WIN",
                                            "profit": h.get("profit", 0)
                                        })

                            state["accounts"][account_type] = {
                                "status": status,
                                "balance": balance.demo if account_type == "demo" else balance.real,
                                "history": history
                            }
                        else:
                            state["accounts"][account_type] = {"status": status}
                    except KeyError:
                        state["accounts"][account_type] = {"status": "disconnected"}
                    except Exception as e:
                        logger.error("Error in broadcast_updates: %s", e)
                        state["accounts"][account_type] = {"status": "error"}
            
            await manager.broadcast(state)
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan — startup and shutdown."""
    logger.info("Starting up OTC Sniper Backend...")
    asyncio.create_task(broadcast_updates())
    yield
    logger.info("Shutting down...")


app = FastAPI(title="OTC Sniper Web API", lifespan=lifespan)

# CORS — A2a: restricted to known frontend origin (no wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from auth.middleware import require_role

# Mount Auth Router (E1)
try:
    from api_wrapper.auth_router import router as auth_router
    app.include_router(auth_router)
except ImportError as e:
    logger.warning(f"Could not import auth router: {e}")

# Mount Settings Router (C5)
try:
    from api_wrapper.settings_router import router as settings_router
    app.include_router(settings_router)
except ImportError as e:
    logger.warning(f"Could not import settings router: {e}")

@app.post("/api/connect", response_model=ConnectResponse, dependencies=[Depends(require_role("trader"))])
async def connect(request: ConnectionRequest):
    account_type = "demo" if request.demo else "real"

    if not BrokerRegistry:
        return ConnectResponse(
            success=False,
            message="BrokerRegistry unavailable.",
            account_type=account_type,
        )

    try:
        ssid = request.ssid
        if not ssid:
            try:
                from auth.credentials import CredentialManager
                from pathlib import Path
                _DATA_DIR = Path(__file__).resolve().parents[1] / "data"
                cred_manager = CredentialManager(data_dir=_DATA_DIR)
                creds = cred_manager.load_credentials("pocket_option", account_type)
                if creds and "ssid" in creds:
                    ssid = creds["ssid"]
            except Exception as e:
                logger.error(f"Failed to load credentials from manager: {e}")
                
        if not ssid:
            # Fallback to local get_ssid if needed, but the client should provide it or we load from credentials.py
            try:
                from otc_sniper.utils.config_loader import get_ssid
                ssid = get_ssid("DEMO" if request.demo else "REAL")
            except ImportError:
                pass
                
        if not ssid:
            return ConnectResponse(
                success=False,
                message=f"No SSID provided or found for {account_type}",
                account_type=account_type
            )

        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
        success = await adapter.connect({"ssid": ssid, "demo": str(request.demo).lower()})

        if success:
            balance = await adapter.get_balance(demo=request.demo)
            return ConnectResponse(
                success=True,
                message=f"Connected to {account_type} successfully",
                balance=balance.demo if request.demo else balance.real,
                account_type=account_type
            )
        else:
            return ConnectResponse(
                success=False,
                message=f"Connection to {account_type} failed",
                account_type=account_type
            )

    except Exception as e:
        logger.error(f"Connection error: {e}")
        return ConnectResponse(success=False, message=str(e), account_type=account_type)


@app.get("/api/assets", dependencies=[Depends(require_role("viewer"))])
async def get_assets(demo: bool = True):
    account_type = "demo" if demo else "real"
    if not BrokerRegistry:
        return []
    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
        if adapter.get_connection_status() != "connected":
            return []
        assets = await adapter.get_assets(demo=demo)
        return [{"id": a.id, "name": a.name, "payout": a.payout} for a in assets]
    except Exception as e:
        logger.error(f"Failed to get assets: {e}")
        return []


@app.post("/api/assets/refresh", dependencies=[Depends(require_role("viewer"))])
async def refresh_assets(demo: bool = True):
    account_type = "demo" if demo else "real"
    if not BrokerRegistry:
        raise HTTPException(status_code=503, detail="BrokerRegistry unavailable")

    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"{account_type.capitalize()} account not connected — connect first")

    try:
        if adapter.get_connection_status() != "connected":
            raise HTTPException(status_code=400, detail=f"{account_type.capitalize()} account not connected")

        assets = await adapter.get_assets(demo=demo)
        return {"success": True, "count": len(assets)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh assets error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh assets: {e}")


@app.post("/api/trade", dependencies=[Depends(require_role("trader"))])
async def execute_trade(request: TradeRequest):
    account_type = "demo" if request.demo else "real"
    if not BrokerRegistry:
        raise HTTPException(status_code=500, detail="BrokerRegistry unavailable")

    try:
        adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
        if adapter.get_connection_status() != "connected":
            raise HTTPException(status_code=400, detail=f"{account_type.capitalize()} account not connected")

        # Normalize asset_id — canonical format for internal use
        canonical_asset = normalize_asset(request.asset_id)

        # Enforce concurrent trade limits from settings
        allowed, reason = await _trade_manager.can_place_trade(canonical_asset)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)

        order = TradeOrder(
            asset_id=canonical_asset,
            direction=request.direction,
            amount=request.amount,
            expiration=request.expiration,
            order_type="market",
            broker=BrokerType.POCKET_OPTION
        )

        result = await adapter.execute_trade(order)

        if result.success and result.trade_id:
            await _trade_manager.register_trade(result.trade_id, {
                "asset_id": canonical_asset,
                "direction": request.direction,
                "amount": request.amount,
                "expiration": request.expiration,
                "account_type": account_type
            })

        return {"success": result.success, "message": result.message, "trade_id": result.trade_id}
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/state")
async def get_state():
    state = {}
    if BrokerRegistry:
        for account_type in ["demo", "real"]:
            try:
                adapter = BrokerRegistry.get_adapter(BrokerType.POCKET_OPTION, account_type)
                status = adapter.get_connection_status()
                state[account_type] = {"status": status}
                if status == "connected":
                    balance = await adapter.get_balance(demo=(account_type == "demo"))
                    state[account_type]["balance"] = balance.demo if account_type == "demo" else balance.real
                    history = await adapter.get_trade_history(limit=5)
                    state[account_type]["history"] = history
            except KeyError:
                state[account_type] = {"status": "disconnected"}
            except Exception as e:
                logger.error(f"Error getting state for {account_type}: {e}")
                state[account_type] = {"status": "error"}
    else:
        state = {"demo": {"status": "error"}, "real": {"status": "error"}}
    return state


@app.get("/api/trades/active", dependencies=[Depends(require_role("trader"))])
async def get_active_trades():
    return _trade_manager.get_active_trades()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
