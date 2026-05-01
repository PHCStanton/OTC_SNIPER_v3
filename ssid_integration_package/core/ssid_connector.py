"""
SSIDConnector — Backward-compatible wrapper around PocketOptionSession.

Existing code that uses SSIDConnector will continue to work.
New projects should use PocketOptionSession directly.
"""

import json
from ssid_integration_package.core.session import PocketOptionSession, SSIDParseError, ConnectionError


class SSIDConnector:
    """Backward-compatible wrapper. Use PocketOptionSession for new projects."""

    def __init__(self, ssid: str, demo: bool = False, timeout: int = 15):
        # Note: 'demo' parameter is ignored — isDemo is read from the SSID itself.
        # Kept for backward compatibility only.
        self._session = PocketOptionSession(ssid, timeout=timeout)
        self.is_connected = False
        self.balance = None

    def connect(self):
        """Establish connection via PocketOptionSession"""
        success, msg = self._session.connect()
        self.is_connected = success
        self.balance = self._session.get_balance()
        return success, msg

    def disconnect(self):
        """Gracefully disconnect"""
        result = self._session.disconnect()
        self.is_connected = False
        self.balance = None
        return result

    def check_connection(self):
        """Check if session is active"""
        return self._session.is_connected

    def get_balance(self):
        """Return current balance"""
        return self._session.get_balance()

    def update_balance(self):
        """Force update balance"""
        return self._session.get_balance()

    def __enter__(self):
        success, msg = self.connect()
        if not success:
            raise ConnectionError(msg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
