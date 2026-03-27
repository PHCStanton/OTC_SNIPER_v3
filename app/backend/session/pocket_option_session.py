"""Pocket Option SSID session manager."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import asyncio
from typing import Optional, Tuple, Callable


class SSIDParseError(ValueError):
    pass


class SessionConnectionError(RuntimeError):
    pass


class PocketOptionSession:
    _tick_callback: Optional[Callable[[str, float, float], None]] = None
    _original_set_csv: Optional[Callable] = None  # Fix #8: typed annotation

    @classmethod
    def set_tick_callback(cls, callback: Callable[[str, float, float], None]):
        """Inject a global callback for all PO ticks."""
        cls._tick_callback = callback
        cls._apply_hooks()

    @classmethod
    def _apply_hooks(cls):
        """Monkey-patch the PO API global_value to capture ticks."""
        try:
            import pocketoptionapi.global_value as gv
            if cls._original_set_csv is None:
                cls._original_set_csv = gv.set_csv
                
                def hooked_set_csv(key, value, path=None):
                    # Call original first
                    res = cls._original_set_csv(key, value, path)
                    
                    # If it's a price update, notify our callback
                    if cls._tick_callback and isinstance(value, list) and len(value) > 0:
                        tick = value[0]
                        if 'price' in tick:
                            try:
                                asset = str(key)
                                price = float(tick['price'])
                                ts = float(tick['time'])
                                # Fix #6: use get_running_loop — safe from non-async thread
                                # Fix #5: default-arg lambda to avoid closure stale-variable bug
                                loop = asyncio.get_running_loop()
                                loop.call_soon_threadsafe(
                                    lambda a=asset, p=price, t=ts: asyncio.ensure_future(
                                        cls._tick_callback(a, p, t), loop=loop
                                    )
                                )
                            except RuntimeError:
                                # No running loop — broker connected before app started, skip
                                pass
                            except Exception as hook_err:
                                # Fix #7: log instead of silently swallowing
                                logging.getLogger("PocketOptionSession").warning(
                                    "Tick hook error for %s: %s", key, hook_err
                                )
                    return res
                
                gv.set_csv = hooked_set_csv
                logging.getLogger("PocketOptionSession").info("Broker tick hooks applied successfully.")
        except ImportError:
            pass

    def __init__(self, ssid: str, timeout: int = 15):
        if not ssid or not isinstance(ssid, str):
            raise SSIDParseError("SSID must be a non-empty string")

        self.logger = logging.getLogger(self.__class__.__name__)
        self.timeout = timeout
        self._raw_ssid = ssid
        self._session_data = self._parse_ssid(ssid)
        self._is_demo = bool(self._session_data.get("isDemo", 0))
        self._api = None
        self._connected = False
        self._balance = None

    @staticmethod
    def _parse_ssid(ssid: str) -> dict:
        if not ssid.startswith("42["):
            raise SSIDParseError("SSID must start with '42['")

        try:
            payload = json.loads(ssid[2:])
        except json.JSONDecodeError as exc:
            raise SSIDParseError(f"SSID JSON is malformed: {exc}") from exc

        if not isinstance(payload, list) or len(payload) < 2:
            raise SSIDParseError("SSID must be a JSON array with at least 2 elements")
        if payload[0] != "auth":
            raise SSIDParseError(f"SSID first element must be 'auth', got {payload[0]!r}")

        session_payload = payload[1]
        if not isinstance(session_payload, dict):
            raise SSIDParseError("SSID auth payload must be a dictionary")

        missing = [field for field in ("session", "isDemo") if field not in session_payload]
        if missing:
            raise SSIDParseError(f"SSID missing required fields: {missing}")

        return session_payload

    @property
    def is_demo(self) -> bool:
        return self._is_demo

    @property
    def account_type(self) -> str:
        return "DEMO" if self._is_demo else "REAL"

    @property
    def session_id(self) -> str:
        source = str(self._session_data.get("session") or self._raw_ssid)
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]

    @property
    def is_connected(self) -> bool:
        return bool(self._connected and self._api and self._api.check_connect())

    def connect(self) -> Tuple[bool, str]:
        if self.is_connected:
            return True, f"Already connected to {self.account_type}"

        try:
            from pocketoptionapi.stable_api import PocketOption
            import pocketoptionapi.global_value as global_value
        except ImportError as exc:
            msg = f"Pocket Option API dependency unavailable: {exc}"
            self.logger.error(msg)
            return False, msg

        try:
            # Reset relevant globals manually (reset_all() not available in this API version)
            global_value.websocket_is_connected = False
            global_value.balance = None
            global_value.balance_updated = None
            global_value.result = None
            global_value.order_data = {}
            global_value.SSID = self._raw_ssid
            global_value.DEMO = self._is_demo

            self._api = PocketOption(self._raw_ssid, self._is_demo)
            if not self._api.connect():
                self._connected = False
                return False, "Failed to start WebSocket connection"

            start = time.time()
            while time.time() - start < self.timeout:
                if self._api.check_connect():
                    self._connected = True
                    break
                time.sleep(0.25)

            if not self._connected:
                self._api = None
                return False, f"Connection timeout after {self.timeout}s"

            balance_start = time.time()
            while time.time() - balance_start < 20:
                balance = self._api.get_balance()
                if balance is not None:
                    self._balance = balance
                    return True, f"Connected to {self.account_type}. Balance: ${balance:,.2f}"
                time.sleep(0.25)

            try:
                self.disconnect()
            except Exception as disc_exc:
                self.logger.warning("Cleanup disconnect after auth failure: %s", disc_exc)
            return False, "Authentication failed — no balance received"
        except Exception as exc:
            try:
                self.disconnect()
            except Exception as disc_exc:
                self.logger.warning("Cleanup disconnect after connection error: %s", disc_exc)
            msg = f"Connection failed: {exc}"
            self.logger.error(msg)
            return False, msg

    def disconnect(self) -> bool:
        try:
            try:
                import pocketoptionapi.global_value as global_value
            except ImportError:
                global_value = None

            if self._api and self._connected:
                try:
                    self._api.disconnect()
                except Exception as exc:
                    self.logger.warning("API disconnect error: %s", exc)

            if global_value is not None:
                # Reset relevant globals manually (reset_all() not available in this API version)
                global_value.websocket_is_connected = False
                global_value.balance = None
                global_value.balance_updated = None
                global_value.result = None
                global_value.order_data = {}
                global_value.SSID = None
                global_value.DEMO = None

            self._api = None
            self._connected = False
            self._balance = None
            return True
        except Exception as exc:
            self.logger.error("Disconnect error: %s", exc)
            return False

    def switch_account(self, new_ssid: str) -> Tuple[bool, str]:
        new_data = self._parse_ssid(new_ssid)
        old_type = self.account_type
        new_type = "DEMO" if bool(new_data.get("isDemo", 0)) else "REAL"

        self.disconnect()
        self._raw_ssid = new_ssid
        self._session_data = new_data
        self._is_demo = bool(new_data.get("isDemo", 0))

        success, message = self.connect()
        if success:
            return True, f"Switched from {old_type} to {new_type}. {message}"
        return False, f"Switch failed: {message}"

    def get_balance(self) -> Optional[float]:
        if not self.is_connected or self._api is None:
            return None

        try:
            balance = self._api.get_balance()
            if balance is not None:
                self._balance = balance
            return self._balance
        except Exception as exc:
            self.logger.warning("get_balance() error: %s", exc)
            return self._balance

    def buy(self, amount, active, action, expirations):
        if not self.is_connected or self._api is None:
            raise SessionConnectionError("Not connected")
        return self._api.buy(amount, active, action, expirations)

    def buy_advanced(self, amount, active, action, expirations, on_new_candle=False):
        if not self.is_connected or self._api is None:
            raise SessionConnectionError("Not connected")
        return self._api.buy_advanced(amount, active, action, expirations, on_new_candle)

    def get_candles(self, active, timeframe, count):
        if not self.is_connected or self._api is None:
            raise SessionConnectionError("Not connected")
        return self._api.get_candles(active, timeframe, count)

    def check_win(self, order_id):
        if not self.is_connected or self._api is None:
            raise SessionConnectionError("Not connected")
        return self._api.check_win(order_id)

    def __enter__(self):
        success, message = self.connect()
        if not success:
            raise SessionConnectionError(message)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self.is_connected else "disconnected"
        return f"<PocketOptionSession {self.account_type} [{status}]>"
