"""
PocketOptionSession — Reusable SSID Session Manager

Single source of truth for:
- SSID validation and parsing
- DEMO/REAL account detection
- WebSocket connection lifecycle
- Clean account switching
- Global state management

Usage:
    session = PocketOptionSession(ssid_string)
    success, msg = session.connect()
    
    # Switch accounts
    session.switch_account(other_ssid_string)
    
    # Context manager
    with PocketOptionSession(ssid_string) as session:
        balance = session.get_balance()
"""

import json
import time
import logging
from typing import Optional, Tuple

from pocketoptionapi.stable_api import PocketOption
import pocketoptionapi.global_value as global_value


class SSIDParseError(Exception):
    """Raised when SSID string cannot be parsed"""
    pass


class ConnectionError(Exception):
    """Raised when WebSocket connection fails"""
    pass


class PocketOptionSession:
    """
    Single-responsibility session manager for Pocket Option API.
    
    Parses SSID once, manages connection lifecycle, enables clean switching.
    """

    def __init__(self, ssid: str, timeout: int = 15):
        """
        Initialize session with SSID string.
        
        Args:
            ssid: Full SSID string (e.g., '42["auth",{"session":"...","isDemo":1,...}]')
            timeout: Connection timeout in seconds
            
        Raises:
            SSIDParseError: If SSID format is invalid
        """
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self._api = None
        self._connected = False
        self._balance = None
        
        # Parse SSID once — single source of truth
        self._raw_ssid = ssid
        self._session_data = self._parse_ssid(ssid)
        self._is_demo = bool(self._session_data.get('isDemo', 0))
        
        self.logger.info(
            f"Session initialized: {'DEMO' if self._is_demo else 'REAL'} account"
        )

    @staticmethod
    def _parse_ssid(ssid: str) -> dict:
        """
        Parse and validate SSID string. Called exactly ONCE.
        
        Args:
            ssid: Raw SSID string
            
        Returns:
            dict: Parsed auth payload
            
        Raises:
            SSIDParseError: If format is invalid
        """
        if not ssid or not isinstance(ssid, str):
            raise SSIDParseError("SSID must be a non-empty string")
        
        if not ssid.startswith('42['):
            raise SSIDParseError(
                f"SSID must start with '42['. Got: '{ssid[:20]}...'"
            )
        
        try:
            json_part = ssid[2:]  # Strip '42' prefix
            data = json.loads(json_part)
        except json.JSONDecodeError as e:
            raise SSIDParseError(f"SSID JSON is malformed: {e}")
        
        if not isinstance(data, list) or len(data) < 2:
            raise SSIDParseError("SSID must be a JSON array with at least 2 elements")
        
        if data[0] != "auth":
            raise SSIDParseError(f"SSID first element must be 'auth', got '{data[0]}'")
        
        payload = data[1]
        if not isinstance(payload, dict):
            raise SSIDParseError("SSID auth payload must be a dictionary")
        
        # Validate required fields
        required_fields = ['session', 'isDemo']
        missing = [f for f in required_fields if f not in payload]
        if missing:
            raise SSIDParseError(f"SSID missing required fields: {missing}")
        
        return payload

    @property
    def is_demo(self) -> bool:
        """Whether this is a DEMO account session"""
        return self._is_demo

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is currently connected"""
        return self._connected and self._api and self._api.check_connect()

    @property
    def account_type(self) -> str:
        """Human-readable account type"""
        return "DEMO" if self._is_demo else "REAL"

    def connect(self) -> Tuple[bool, str]:
        """
        Establish WebSocket connection to Pocket Option.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        # Guard against double-call on a live session
        if self._connected and self._api and self._api.check_connect():
            return True, f"Already connected to {self.account_type}"

        try:
            self.logger.info(f"Connecting to {self.account_type} account...")
            
            # Reset global state for clean connection
            global_value.reset_all()
            
            # Set globals that the API layer needs
            global_value.SSID = self._raw_ssid
            global_value.DEMO = self._is_demo
            
            # Create API instance
            self._api = PocketOption(self._raw_ssid)
            
            # Start connection
            connection_result = self._api.connect()
            if not connection_result:
                return False, "Failed to start WebSocket connection"
            
            # Wait for WebSocket handshake
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                if self._api.check_connect():
                    self._connected = True
                    self.logger.info("WebSocket connected")
                    break
                time.sleep(0.5)
            
            if not self._connected:
                return False, f"Connection timeout after {self.timeout}s"
            
            # Wait for balance (confirms authentication)
            balance_timeout = 20
            start_time = time.time()
            while time.time() - start_time < balance_timeout:
                balance = self._api.get_balance()
                if balance is not None:
                    self._balance = balance
                    msg = f"Connected to {self.account_type}. Balance: ${balance:,.2f}"
                    self.logger.info(msg)
                    return True, msg
                time.sleep(0.5)
            
            self._connected = False
            return False, "Authentication failed — no balance received"
            
        except Exception as e:
            self._connected = False
            error_msg = f"Connection failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def disconnect(self) -> bool:
        """
        Gracefully disconnect and reset all state.
        
        Returns:
            bool: True if successful
        """
        try:
            self.logger.info(f"Disconnecting from {self.account_type} account...")
            
            if self._api and self._connected:
                try:
                    self._api.disconnect()
                except Exception as e:
                    self.logger.warning(f"API disconnect error: {e}")
            
            # Reset ALL global state
            global_value.reset_all()
            
            self._connected = False
            self._balance = None
            self._api = None
            
            time.sleep(1)  # Allow cleanup
            self.logger.info("Disconnected and state cleared")
            return True
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            return False

    def switch_account(self, new_ssid: str) -> Tuple[bool, str]:
        """
        Switch to a different account (DEMO ↔ REAL or different user).
        
        Performs a full disconnect → state reset → reconnect cycle.
        
        Args:
            new_ssid: New SSID string to connect with
            
        Returns:
            tuple: (success: bool, message: str)
        """
        old_type = self.account_type
        
        # Parse new SSID first (fail fast before disconnecting)
        try:
            new_data = self._parse_ssid(new_ssid)
        except SSIDParseError as e:
            return False, f"Invalid new SSID: {e}"
        
        new_is_demo = bool(new_data.get('isDemo', 0))
        new_type = "DEMO" if new_is_demo else "REAL"
        
        self.logger.info(f"Switching from {old_type} to {new_type}...")
        
        # Disconnect current session
        self.disconnect()
        
        # Update internal state
        self._raw_ssid = new_ssid
        self._session_data = new_data
        self._is_demo = new_is_demo
        
        # Connect with new SSID
        success, msg = self.connect()
        
        if success:
            return True, f"Switched from {old_type} to {new_type}. {msg}"
        else:
            return False, f"Switch failed: {msg}"

    def get_balance(self) -> Optional[float]:
        """Get current account balance"""
        if not self.is_connected:
            return None
        try:
            balance = self._api.get_balance()
            if balance is not None:
                self._balance = balance
            return self._balance
        except Exception as e:
            self.logger.warning(f"get_balance() error: {e}")
            return self._balance

    def buy(self, amount, active, action, expirations):
        """Place a trade"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.buy(amount, active, action, expirations)

    def buy_advanced(self, amount, active, action, expirations, on_new_candle=False):
        """Place an advanced trade"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.buy_advanced(amount, active, action, expirations, on_new_candle)

    def get_candles(self, active, timeframe, count):
        """Get historical candles"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.get_candles(active, timeframe, count)

    def check_win(self, order_id):
        """Check if an order won or lost"""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        return self._api.check_win(order_id)

    # Context manager support
    def __enter__(self):
        success, msg = self.connect()
        if not success:
            raise ConnectionError(msg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __repr__(self):
        status = "connected" if self._connected else "disconnected"
        return f"<PocketOptionSession {self.account_type} [{status}]>"
