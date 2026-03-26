"""High-level session manager for the active Pocket Option session."""

from __future__ import annotations

from dataclasses import asdict

from .models import SessionState
from .pocket_option_session import PocketOptionSession


class SessionManager:
    def __init__(self) -> None:
        self._session: PocketOptionSession | None = None
        self._last_message: str = "Disconnected"

    @property
    def current_session(self) -> PocketOptionSession | None:
        return self._session

    def connect(self, ssid: str) -> SessionState:
        if self._session is not None:
            self.disconnect()

        session = PocketOptionSession(ssid)
        success, message = session.connect()
        if not success:
            self._session = None
            self._last_message = message
            raise RuntimeError(message)

        self._session = session
        self._last_message = message
        return self.snapshot(message=message)

    def disconnect(self) -> SessionState:
        if self._session is None:
            self._last_message = "Disconnected"
            return self.snapshot(message=self._last_message)

        self._session.disconnect()
        self._session = None
        self._last_message = "Disconnected"
        return self.snapshot(message=self._last_message)

    def snapshot(self, message: str | None = None) -> SessionState:
        if self._session is None:
            return SessionState(False, "UNKNOWN", False, None, None, message or self._last_message)

        return SessionState(
            connected=self._session.is_connected,
            account_type=self._session.account_type,
            is_demo=self._session.is_demo,
            session_id=self._session.session_id,
            balance=self._session.get_balance(),
            message=message or self._last_message,
        )

    def status_dict(self) -> dict:
        return asdict(self.snapshot())

    def check_connected(self) -> bool:
        """Return True if a session is active and the WebSocket is live."""
        return bool(self._session and self._session.is_connected)
