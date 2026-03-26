"""
CDP SSID Extractor — OTC SNIPER v3

Extracts the live Pocket Option SSID from a running Chrome session via the
Chrome DevTools Protocol (CDP) on the configured debug port (default 9222).

Design principles:
  - Zero external dependencies: uses only stdlib urllib + websockets (already
    required by pocketoptionapi).
  - Fail fast and loud: every failure path raises a descriptive exception.
  - No silent fallbacks: if Chrome is not running or the cookie is missing,
    the caller receives a clear error, not an empty string.

Usage:
    from backend.services.ssid_extractor import extract_ssid_from_chrome
    ssid_frame = await extract_ssid_from_chrome(chrome_port=9222, demo=False)
    # Returns: '42["auth",{"session":"<hex>","isDemo":0,...}]'
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger("otc_sniper.ssid_extractor")

# Pocket Option domains to search for the SSID cookie
_PO_DOMAINS = {".pocketoption.com", "pocketoption.com", "pocket2.click", ".pocket2.click"}
_SSID_COOKIE_NAME = "ssid"

# CDP command timeout in seconds
_CDP_TIMEOUT = 8.0


class CDPError(RuntimeError):
    """Raised when the Chrome DevTools Protocol interaction fails."""


class SSIDNotFoundError(RuntimeError):
    """Raised when no valid SSID cookie is found in the Chrome session."""


# ── Chrome tab discovery ──────────────────────────────────────────────────────

def _get_chrome_tabs(chrome_port: int) -> List[Dict[str, Any]]:
    """
    Query the Chrome debug endpoint for the list of open tabs.

    Raises CDPError if Chrome is not reachable or returns unexpected data.
    """
    url = f"http://127.0.0.1:{chrome_port}/json/list"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise CDPError(
            f"Chrome debug port {chrome_port} is not reachable. "
            f"Start Chrome with --remote-debugging-port={chrome_port} first. "
            f"Detail: {exc}"
        ) from exc
    except Exception as exc:
        raise CDPError(f"Unexpected error querying Chrome tabs: {exc}") from exc

    try:
        tabs = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CDPError(f"Chrome returned invalid JSON from /json/list: {exc}") from exc

    if not isinstance(tabs, list):
        raise CDPError(f"Expected a list of tabs from Chrome, got: {type(tabs).__name__}")

    return tabs


def _find_pocket_option_tab(tabs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Return the first tab whose URL contains a Pocket Option domain.

    Returns None if no matching tab is found.
    """
    for tab in tabs:
        url = tab.get("url", "")
        for domain in _PO_DOMAINS:
            if domain.replace(".", "") in url.replace(".", ""):
                return tab
    return None


# ── CDP WebSocket interaction ─────────────────────────────────────────────────

async def _cdp_get_all_cookies(ws_url: str) -> List[Dict[str, Any]]:
    """
    Connect to a Chrome tab via its WebSocket debugger URL and retrieve all cookies.

    Uses the websockets library (already a transitive dependency via pocketoptionapi).
    Falls back to a raw asyncio reader/writer if websockets is unavailable.
    """
    try:
        import websockets  # type: ignore
    except ImportError:
        raise CDPError(
            "The 'websockets' package is required for CDP cookie extraction. "
            "Install it with: pip install websockets"
        )

    command = json.dumps({"id": 1, "method": "Network.getAllCookies"})

    try:
        async with websockets.connect(ws_url, open_timeout=_CDP_TIMEOUT) as ws:
            await ws.send(command)
            raw = await asyncio.wait_for(ws.recv(), timeout=_CDP_TIMEOUT)
    except asyncio.TimeoutError as exc:
        raise CDPError(
            f"CDP command timed out after {_CDP_TIMEOUT}s. "
            "Chrome tab may be unresponsive."
        ) from exc
    except Exception as exc:
        raise CDPError(f"CDP WebSocket error: {exc}") from exc

    try:
        response = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CDPError(f"CDP returned invalid JSON: {exc}") from exc

    if "error" in response:
        raise CDPError(f"CDP command error: {response['error']}")

    cookies: List[Dict[str, Any]] = response.get("result", {}).get("cookies", [])
    return cookies


# ── Cookie extraction and SSID formatting ────────────────────────────────────

def _extract_ssid_cookie(cookies: List[Dict[str, Any]]) -> str:
    """
    Find the Pocket Option SSID cookie value from the CDP cookie list.

    Raises SSIDNotFoundError if no matching cookie is found.
    """
    for cookie in cookies:
        name = cookie.get("name", "")
        domain = cookie.get("domain", "")
        value = cookie.get("value", "")

        if name != _SSID_COOKIE_NAME:
            continue

        # Check domain matches a known Pocket Option domain
        domain_clean = domain.lstrip(".")
        if not any(domain_clean in d or d.lstrip(".") in domain_clean for d in _PO_DOMAINS):
            continue

        if not value or len(value) < 8:
            continue

        logger.debug("Found SSID cookie: domain=%s, value_length=%d", domain, len(value))
        return value

    raise SSIDNotFoundError(
        "No valid Pocket Option SSID cookie found in the Chrome session. "
        "Ensure you are logged in to pocketoption.com in the Chrome window."
    )


def _format_ssid_frame(raw_ssid: str, demo: bool) -> str:
    """
    Wrap the raw SSID cookie value into the WebSocket auth frame format
    expected by PocketOptionSession.

    Format: 42["auth",{"session":"<raw>","isDemo":<0|1>,"uid":0,"platform":2,
                        "isFastHistory":true,"isOptimized":true}]
    """
    payload = {
        "session": raw_ssid,
        "isDemo": 1 if demo else 0,
        "uid": 0,
        "platform": 2,
        "isFastHistory": True,
        "isOptimized": True,
    }
    return f'42["auth",{json.dumps(payload, separators=(",", ":"))}]'


# ── Public API ────────────────────────────────────────────────────────────────

async def extract_ssid_from_chrome(
    chrome_port: int = 9222,
    demo: bool = False,
    require_pocket_option_tab: bool = True,
) -> str:
    """
    Extract the live Pocket Option SSID from a running Chrome session.

    Steps:
      1. Query Chrome debug port for open tabs.
      2. Locate the Pocket Option tab (if require_pocket_option_tab=True).
      3. Connect via CDP WebSocket and retrieve all cookies.
      4. Extract the 'ssid' cookie for the Pocket Option domain.
      5. Format and return the full 42["auth",{...}] frame.

    Args:
        chrome_port: Chrome remote debugging port (default 9222).
        demo: Whether to format the frame as a demo account (isDemo=1).
        require_pocket_option_tab: If True, raises CDPError when no
            Pocket Option tab is found. If False, uses the first available tab.

    Returns:
        A full 42["auth",{...}] SSID frame string.

    Raises:
        CDPError: Chrome is not reachable, tab not found, or CDP command failed.
        SSIDNotFoundError: No valid SSID cookie found in the Chrome session.
    """
    logger.info("Starting CDP SSID extraction on port %d (demo=%s)", chrome_port, demo)

    # Step 1: Get tabs
    tabs = _get_chrome_tabs(chrome_port)
    if not tabs:
        raise CDPError(
            f"Chrome debug port {chrome_port} is reachable but returned no tabs. "
            "Open a Pocket Option tab in Chrome first."
        )

    # Step 2: Find the right tab
    target_tab = _find_pocket_option_tab(tabs)

    if target_tab is None:
        if require_pocket_option_tab:
            raise CDPError(
                "No Pocket Option tab found in Chrome. "
                "Navigate to pocketoption.com and log in before using auto-connect."
            )
        # Fall back to first available tab with a debugger URL
        for tab in tabs:
            if tab.get("webSocketDebuggerUrl"):
                target_tab = tab
                break

    if target_tab is None:
        raise CDPError("No debuggable Chrome tab found.")

    ws_url = target_tab.get("webSocketDebuggerUrl")
    if not ws_url:
        raise CDPError(
            f"Chrome tab '{target_tab.get('title', 'unknown')}' has no WebSocket debugger URL. "
            "The tab may be a background page or extension."
        )

    logger.debug("Using tab: %s (%s)", target_tab.get("title"), target_tab.get("url"))

    # Step 3: Get cookies via CDP
    cookies = await _cdp_get_all_cookies(ws_url)
    logger.debug("Retrieved %d cookies from Chrome tab", len(cookies))

    # Step 4: Extract SSID cookie
    raw_ssid = _extract_ssid_cookie(cookies)

    # Step 5: Format and return
    frame = _format_ssid_frame(raw_ssid, demo=demo)
    logger.info("SSID extracted successfully (demo=%s, length=%d)", demo, len(frame))
    return frame
