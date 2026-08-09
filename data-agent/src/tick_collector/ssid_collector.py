"""
SSID Tick Collector — Persistent Pocket Option WebSocket Stream Collector

Design:
  - Uses the proven PocketOptionSession engine (wrapping pocketoptionapi).
  - Handles Engine.IO handshake, region rotation, and balance confirmation.
  - Intercepts live ticks via global_value.set_csv hook in PocketOptionSession.
  - Subscribes to requested asset tickers via session._api.change_symbol(asset, 1).
  - Normalizes and dispatches tick events to attached callbacks / GCPTickSink.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from app.backend.session.pocket_option_session import (
        PocketOptionSession,
        SSIDParseError,
        SessionConnectionError,
    )
except ImportError:
    try:
        from session.pocket_option_session import (
            PocketOptionSession,
            SSIDParseError,
            SessionConnectionError,
        )
    except ImportError:
        PocketOptionSession = None  # Handled gracefully if missing in isolation
        SSIDParseError = ValueError
        SessionConnectionError = RuntimeError

logger = logging.getLogger("data_agent.tick_collector")


def parse_ssid_payload(ssid: str, default_is_demo: bool = True) -> tuple[str, bool, int, int]:
    """Parse raw SSID string or 42["auth", {...}] payload.

    Returns:
        tuple[str, bool, int, int]: (session_token, is_demo, uid, platform)
    """
    cleaned = (ssid or "").strip()
    if not cleaned:
        return "", default_is_demo, 0, 2

    if cleaned.startswith("42"):
        try:
            raw_json = cleaned[2:]
            data = json.loads(raw_json)
            if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], dict):
                payload = data[1]
                session_token = str(payload.get("session", cleaned)).strip()
                is_demo = bool(payload.get("isDemo", 1 if default_is_demo else 0))
                uid = int(payload.get("uid", 0) or 0)
                platform = int(payload.get("platform", 2) or 2)
                return session_token, is_demo, uid, platform
        except Exception as err:
            logger.warning("Could not parse JSON payload from SSID frame: %s", err)

    return cleaned, default_is_demo, 0, 2


class SSIDTickCollector:
    """
    Persistent WebSocket Tick Collector for Pocket Option using SSID auth & PocketOptionSession.
    """

    def __init__(
        self,
        ssid: str,
        assets: Optional[List[str]] = None,
        is_demo: Optional[bool] = None,
        ws_url: str = "wss://api-us-north.po.market/socket.io/?EIO=4&transport=websocket",
        reconnect_delay_base: float = 2.0,
        max_reconnect_delay: float = 60.0,
    ):
        self.raw_ssid = ssid.strip()
        self.assets = set(assets) if assets else {"EURUSD_otc", "GBPUSD_otc", "USDJPY_otc"}
        self.ws_url = ws_url
        self.reconnect_delay_base = reconnect_delay_base
        self.max_reconnect_delay = max_reconnect_delay

        # Auto-detect is_demo from raw_ssid if not explicitly forced
        token, detected_demo, uid, platform = parse_ssid_payload(
            self.raw_ssid,
            default_is_demo=True if is_demo is None else bool(is_demo),
        )
        self.ssid = token
        self.is_demo = (1 if is_demo else 0) if is_demo is not None else (1 if detected_demo else 0)
        self._uid = uid
        self._platform = platform

        self._session: Optional[Any] = None
        self._ws: Optional[Any] = None
        self._running = False
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._tick_count = 0
        self._last_tick_time: Optional[float] = None
        self._subscribed_assets: Set[str] = set()

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback function to receive parsed tick dicts."""
        self._callbacks.append(callback)

    def _is_ws_connected(self) -> bool:
        """Connection check across PocketOptionSession and test mocks."""
        # 1. Live PocketOptionSession check
        if self._session is not None:
            try:
                if self._session.is_connected:
                    return True
            except Exception:
                pass

        # 2. Test mock / explicit _ws fallback
        ws = self._ws
        if ws is not None:
            if hasattr(ws, "closed") and isinstance(ws.closed, bool):
                return not ws.closed
            if hasattr(ws, "state"):
                try:
                    state_name = getattr(ws.state, "name", None)
                    if isinstance(state_name, str):
                        return state_name == "OPEN"
                except Exception:
                    pass
            return True

        return False

    @property
    def metrics(self) -> Dict[str, Any]:
        """Return runtime connection & tick ingestion metrics."""
        ssid_clean = (self.raw_ssid or self.ssid or "").strip()
        return {
            "running": self._running,
            "connected": self._is_ws_connected(),
            "total_ticks": self._tick_count,
            "last_tick_time": self._last_tick_time,
            "subscribed_assets": list(self._subscribed_assets),
            "is_demo": bool(self.is_demo),
            "ssid_configured": bool(ssid_clean and ssid_clean != "demo_ssid_placeholder"),
        }

    @property
    def target_ws_url(self) -> str:
        """Return dedicated WebSocket server URL depending on Demo vs Real account mode."""
        if self.is_demo:
            return "wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"
        return self.ws_url

    def _on_raw_tick(self, asset: str, price: float, ts: float) -> None:
        """Internal callback invoked by PocketOptionSession hooked_set_csv."""
        now = time.time()
        self._tick_count += 1
        self._last_tick_time = now

        tick_data = {
            "timestamp": float(ts) if ts else now,
            "asset": str(asset),
            "price": float(price),
            "dir": "neutral",
            "is_demo": self.is_demo,
            "received_at": now,
        }

        for cb in self._callbacks:
            try:
                cb(tick_data)
            except Exception as cb_err:
                logger.error("Error in tick callback for %s: %s", asset, cb_err)

    async def update_session(self, ssid: str, is_demo: Optional[bool] = None) -> None:
        """Dynamically update SSID authentication token and demo/real state.

        If currently connected, cleanly disconnects so the background start() loop
        immediately reconnects using the updated credentials.
        """
        self.raw_ssid = (ssid or "").strip()
        token, detected_demo, uid, platform = parse_ssid_payload(
            self.raw_ssid,
            default_is_demo=True if is_demo is None else bool(is_demo),
        )
        self.ssid = token
        self.is_demo = (1 if is_demo else 0) if is_demo is not None else (1 if detected_demo else 0)
        self._uid = uid
        self._platform = platform
        self._subscribed_assets.clear()
        logger.info(
            "Updated SSID session (is_demo=%s, target_url=%s). Triggering reconnect.",
            bool(self.is_demo),
            self.target_ws_url,
        )

        if self._session:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._session.disconnect)
            except Exception as err:
                logger.warning("Error disconnecting session on update: %s", err)
            self._session = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception as err:
                logger.warning("Error closing mock WS on update_session: %s", err)
            self._ws = None

    async def start(self) -> None:
        """Start the collector loop with persistent auto-reconnect using PocketOptionSession."""
        self._running = True
        attempt = 0

        logger.info(
            "Starting SSIDTickCollector (is_demo=%s) for assets: %s",
            bool(self.is_demo),
            self.assets,
        )

        loop = asyncio.get_running_loop()

        while self._running:
            try:
                ssid_clean = (self.raw_ssid or self.ssid or "").strip()
                if not ssid_clean or ssid_clean == "demo_ssid_placeholder":
                    await asyncio.sleep(2.0)
                    continue

                delay = min(self.reconnect_delay_base * (2 ** attempt), self.max_reconnect_delay)
                if attempt > 0:
                    logger.warning("Reconnecting in %.1fs (attempt %d)...", delay, attempt)
                    await asyncio.sleep(delay)

                if not self._running:
                    break

                # Prepare formatted 42["auth", ...] frame if raw session token was supplied
                formatted_ssid = self.raw_ssid
                if not formatted_ssid.startswith("42["):
                    formatted_ssid = (
                        f'42["auth",{{"session":"{self.ssid}","isDemo":{1 if self.is_demo else 0},'
                        f'"uid":{self._uid},"platform":{self._platform}}}]'
                    )

                if PocketOptionSession is not None:
                    session = PocketOptionSession(formatted_ssid, timeout=15)
                    self._session = session

                    # Hook into PocketOptionSession tick dispatch
                    PocketOptionSession.set_tick_callback(self._on_raw_tick)
                    PocketOptionSession.set_main_loop(loop)

                    logger.info(
                        "Connecting to Pocket Option via PocketOptionSession (%s)...",
                        session.account_type,
                    )
                    success, msg = await loop.run_in_executor(None, session.connect)

                    if success and session.is_connected:
                        attempt = 0
                        logger.info("Successfully connected to Pocket Option: %s", msg)

                        # Subscribe to all initial assets
                        await self._subscribe_all_assets()

                        # Keep-alive monitoring loop
                        while self._running and session.is_connected:
                            await asyncio.sleep(2.0)

                        logger.warning("Pocket Option session disconnected.")
                    else:
                        attempt += 1
                        logger.warning("Pocket Option connection failed: %s", msg)
                else:
                    logger.warning("PocketOptionSession class unavailable. Standby mode.")
                    await asyncio.sleep(5.0)

            except asyncio.CancelledError:
                logger.info("Tick collector task cancelled.")
                self._running = False
                break
            except Exception as exc:
                attempt += 1
                logger.error("Tick collector loop error: %s", exc, exc_info=False)
            finally:
                if self._session:
                    try:
                        await loop.run_in_executor(None, self._session.disconnect)
                    except Exception:
                        pass
                    self._session = None

    async def stop(self) -> None:
        """Stop the collector gracefully."""
        logger.info("Stopping SSIDTickCollector...")
        self._running = False
        if self._session:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._session.disconnect)
            except Exception as err:
                logger.warning("Error disconnecting session on stop: %s", err)
            self._session = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def _subscribe_all_assets(self) -> None:
        """Subscribe to quote streams for all configured assets via change_symbol."""
        for asset in list(self.assets):
            await self.add_asset(asset)

    async def add_asset(self, asset: str) -> bool:
        """
        Dynamically subscribe to any asset ticker symbol at runtime.

        Idempotent: uses change_symbol(asset, 1) on the live PocketOptionSession.
        """
        asset_clean = (asset or "").strip()
        if not asset_clean:
            return False

        already_tracked = asset_clean in self.assets
        self.assets.add(asset_clean)

        if self._is_ws_connected() and self._running:
            if asset_clean in self._subscribed_assets:
                logger.debug("Asset already subscribed (idempotent): %s", asset_clean)
                return True
            try:
                # 1. Live PocketOptionSession subscription via change_symbol
                if self._session and getattr(self._session, "_api", None):
                    api = self._session._api
                    if hasattr(api, "change_symbol"):
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, api.change_symbol, asset_clean, 1)
                        self._subscribed_assets.add(asset_clean)
                        logger.info("Subscribed to asset via change_symbol: %s", asset_clean)
                        return True

                # 2. Test mock / websocket fallback
                if self._ws and hasattr(self._ws, "send"):
                    sub_msg = f'42["changeSymbol", {{"asset": "{asset_clean}", "period": 60}}]'
                    await self._ws.send(sub_msg)
                    self._subscribed_assets.add(asset_clean)
                    logger.info("Subscribed to asset (mock/wire): %s", asset_clean)
                    return True

            except Exception as err:
                logger.warning("Failed subscribing to %s: %s", asset_clean, err)
        elif already_tracked:
            logger.debug("Asset already queued for subscription: %s", asset_clean)
        else:
            logger.info("Queued asset %s for subscription on connection.", asset_clean)

        return True
