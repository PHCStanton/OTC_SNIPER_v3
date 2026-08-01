"""
SSID Tick Collector — Persistent Pocket Option WebSocket Stream Collector

Design:
  - Connects to Pocket Option WebSocket servers.
  - Authenticates via session SSID token string.
  - Subscribes to requested asset tickers (e.g. EURUSD_otc, GBPUSD_otc).
  - Handles heartbeats (42["ping"], 2, 3) and auto-reconnects with exponential backoff.
  - Yields tick events to attached callbacks / queues for GCP storage & local buffering.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

try:
    import websockets
except ImportError:
    websockets = None  # Handled gracefully if missing

logger = logging.getLogger("data_agent.tick_collector")


class SSIDTickCollector:
    """
    Persistent WebSocket Tick Collector for Pocket Option using SSID auth.
    """

    def __init__(
        self,
        ssid: str,
        assets: Optional[List[str]] = None,
        is_demo: bool = True,
        ws_url: str = "wss://api-fin.po.market/socket.io/?EIO=4&transport=websocket",
        reconnect_delay_base: float = 2.0,
        max_reconnect_delay: float = 60.0,
    ):
        self.ssid = ssid.strip()
        self.assets = set(assets) if assets else {"EURUSD_otc", "GBPUSD_otc", "USDJPY_otc"}
        self.is_demo = 1 if is_demo else 0
        self.ws_url = ws_url
        self.reconnect_delay_base = reconnect_delay_base
        self.max_reconnect_delay = max_reconnect_delay

        self._ws: Optional[Any] = None
        self._running = False
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._tick_count = 0
        self._last_tick_time: Optional[float] = None
        self._subscribed_assets: Set[str] = set()

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback function to receive parsed tick dicts."""
        self._callbacks.append(callback)

    @property
    def metrics(self) -> Dict[str, Any]:
        """Return runtime connection & tick ingestion metrics."""
        return {
            "running": self._running,
            "connected": self._ws is not None and not self._ws.closed if self._ws else False,
            "total_ticks": self._tick_count,
            "last_tick_time": self._last_tick_time,
            "subscribed_assets": list(self._subscribed_assets),
        }

    async def start(self) -> None:
        """Start the collector loop with persistent auto-reconnect."""
        if websockets is None:
            raise RuntimeError("websockets package is required to run SSIDTickCollector.")

        self._running = True
        attempt = 0

        logger.info(f"Starting SSIDTickCollector for assets: {self.assets}")

        while self._running:
            try:
                delay = min(self.reconnect_delay_base * (2 ** attempt), self.max_reconnect_delay)
                if attempt > 0:
                    logger.warning(f"Reconnecting in {delay:.1f}s (attempt {attempt})...")
                    await asyncio.sleep(delay)

                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    extra_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                ) as ws:
                    self._ws = ws
                    attempt = 0  # Reset on successful connect
                    logger.info("Connected to Pocket Option WebSocket server.")

                    # Authenticate & subscribe
                    await self._send_auth(ws)
                    await self._subscribe_assets(ws)

                    # Listen loop
                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(ws, message)

            except asyncio.CancelledError:
                logger.info("Tick collector task cancelled.")
                self._running = False
                break
            except Exception as exc:
                attempt += 1
                logger.error(f"WebSocket error: {exc}", exc_info=False)
            finally:
                self._ws = None

    async def stop(self) -> None:
        """Stop the collector gracefully."""
        logger.info("Stopping SSIDTickCollector...")
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _send_auth(self, ws: Any) -> None:
        """Send authentication frame using session SSID."""
        auth_msg = f'42["auth",{{"session":"{self.ssid}","isDemo":{self.is_demo}}}]'
        await ws.send(auth_msg)
        logger.info("Sent WebSocket authentication frame.")

    async def _subscribe_assets(self, ws: Any) -> None:
        """Subscribe to quote streams for configured assets."""
        for asset in self.assets:
            sub_msg = f'42["sub", "{asset}"]'
            await ws.send(sub_msg)
            self._subscribed_assets.add(asset)
            logger.info(f"Subscribed to asset: {asset}")

    async def _handle_message(self, ws: Any, message: str) -> None:
        """Parse incoming Socket.IO frame message."""
        # Handle Engine.IO / Socket.IO ping/pong
        if message == "2":
            await ws.send("3")  # Respond with pong
            return

        if message.startswith("42"):
            try:
                raw_json = message[2:]
                data = json.loads(raw_json)
                if not isinstance(data, list) or len(data) < 2:
                    return

                event_name = data[0]
                payload = data[1]

                if event_name in ("tick", "quote", "updateStream"):
                    self._dispatch_tick(payload)
                elif event_name == "auth_success":
                    logger.info("Authentication confirmed by remote server.")
            except Exception as parse_err:
                logger.debug(f"Failed parsing message frame: {parse_err}")

    def _dispatch_tick(self, payload: Dict[str, Any]) -> None:
        """Standardize raw tick payload and dispatch to registered callbacks."""
        now = time.time()
        self._tick_count += 1
        self._last_tick_time = now

        # Normalize tick dictionary structure
        tick_data = {
            "timestamp": payload.get("time", now),
            "asset": payload.get("asset", payload.get("symbol", "UNKNOWN")),
            "price": float(payload.get("price", payload.get("close", 0.0))),
            "dir": payload.get("dir", payload.get("direction", "neutral")),
            "is_demo": self.is_demo,
            "received_at": now,
        }

        for cb in self._callbacks:
            try:
                cb(tick_data)
            except Exception as cb_err:
                logger.error(f"Error in tick callback: {cb_err}")
