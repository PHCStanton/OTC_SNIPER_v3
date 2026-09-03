"""Session loop-safety contract tests (2026-08-31 ops incident).

The PocketOption SDK captures the caller's CURRENT event loop at construction
(`stable_api.py:39`) and later calls loop.stop()/close() on it during
disconnect (`stable_api.py:84-86`). Constructing the session on the server's
RUNNING loop let a failed connect (401) stop the live uvicorn event loop
(observed: "Cannot close a running event loop" -> "Event loop stopped before
Future completed"). These tests lock the fail-fast guard + off-loop contract.
"""
from __future__ import annotations

import unittest

from app.backend.session.pocket_option_session import (
    PocketOptionSession,
    SessionConnectionError,
)

_VALID_SSID = (
    '42["auth",{"session":"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4",'
    '"isDemo":1,"uid":123456,"platform":1}]'
)


class TestSessionLoopGuard(unittest.IsolatedAsyncioTestCase):
    async def test_connect_blocked_on_running_loop(self) -> None:
        """Fail fast: connect() on a RUNNING loop thread must raise
        SessionConnectionError BEFORE the SDK can capture the server loop."""
        session = PocketOptionSession(_VALID_SSID)
        with self.assertRaises(SessionConnectionError) as ctx:
            session.connect()  # executes inside this test's RUNNING event loop
        self.assertIn("RUNNING event loop", str(ctx.exception))

    async def test_guard_raises_before_sdk_capture(self) -> None:
        """The guard fires before any SDK import/capture: no API instance is
        created and no network call is attempted."""
        session = PocketOptionSession(_VALID_SSID)
        try:
            session.connect()
        except SessionConnectionError:
            pass
        self.assertIsNone(session._api)
        self.assertFalse(session._connected)


if __name__ == "__main__":
    unittest.main()
