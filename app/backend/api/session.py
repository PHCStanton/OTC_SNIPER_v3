"""
Phase 0 — Session API: SSID connect / disconnect / status / ssid-status.

Extracted from main.py and extended with:
  - auto-reconnect from .env saved SSIDs
  - SSID persistence to .env after successful connect
  - ssid-status endpoint (reports which SSIDs are saved)
  - explicit SSIDParseError handling with 400 responses
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import get_settings, load_env_file
from ..dependencies import get_session_manager
from ..services.ssid_extractor import CDPError, SSIDNotFoundError, extract_ssid_from_chrome
from ..session.pocket_option_session import SSIDParseError

router = APIRouter(prefix="/api/session", tags=["session"])
logger = logging.getLogger("otc_sniper.session")


# ── Request / Response models (session-specific) ──────────────────────────────

class SessionConnectRequest(BaseModel):
    """
    Connect request.

    ssid: Full 42["auth",{...}] WebSocket frame.
          Pass an empty string to auto-reconnect from saved .env value.
    demo: When ssid is empty, selects which saved SSID to use.
    """
    ssid: str = Field(default="", description='42["auth",{...}] frame or empty for auto-reconnect')
    demo: bool = Field(default=False, description="Use demo SSID when auto-reconnecting")


class SessionSsidClearRequest(BaseModel):
    """Clear a saved SSID from .env for the requested account type."""

    demo: bool = Field(default=False, description="Clear the demo SSID when true, otherwise the real SSID")


# ── .env persistence helpers ──────────────────────────────────────────────────

def _env_file_path() -> Path:
    """Return the canonical .env path for the app."""
    return get_settings().app_root / ".env"


def _persist_ssid_to_env(ssid: str, demo: bool) -> None:
    """
    Write the SSID to .env and refresh the in-memory os.environ.

    This fixes the v2 bug where .env was written but os.environ was stale
    until the next process restart.
    """
    key = "PO_SSID_DEMO" if demo else "PO_SSID_REAL"
    env_path = _env_file_path()

    # Read existing lines
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    # Replace or append the key
    new_line = f"{key}='{ssid}'"
    replaced = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            lines[i] = new_line
            replaced = True
            break

    if not replaced:
        lines.append(new_line)

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Refresh in-memory env immediately (avoids stale state until restart)
    os.environ[key] = ssid
    get_settings.cache_clear()
    logger.info("SSID persisted to .env under key %s", key)


def _clear_ssid_from_env(demo: bool) -> str:
    """Remove the saved SSID from .env and the current process environment."""
    key = "PO_SSID_DEMO" if demo else "PO_SSID_REAL"
    env_path = _env_file_path()

    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            continue
        filtered_lines.append(line)

    env_path.write_text(("\n".join(filtered_lines) + "\n") if filtered_lines else "", encoding="utf-8")
    os.environ.pop(key, None)
    get_settings.cache_clear()
    logger.info("SSID cleared from .env under key %s", key)
    return key


def _resolve_ssid(ssid: str, demo: bool) -> str:
    """
    Resolve the effective SSID to use for connection.

    If ssid is non-empty, use it directly.
    If ssid is empty, fall back to the saved .env value for the requested account type.
    Raises ValueError if no SSID is available.
    """
    if ssid.strip():
        return ssid.strip()

    # Re-read .env in case it was updated after server start
    load_env_file(_env_file_path())
    key = "PO_SSID_DEMO" if demo else "PO_SSID_REAL"
    saved = os.environ.get(key, "").strip()

    if not saved:
        account_label = "demo" if demo else "real"
        raise ValueError(
            f"No SSID provided and no saved {account_label} SSID found in .env. "
            f"Paste a valid 42[\"auth\",...] frame to connect."
        )

    return saved


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/connect")
async def connect_session(body: SessionConnectRequest) -> JSONResponse:
    """
    Connect to Pocket Option using the provided SSID.

    - If ssid is non-empty: validate and connect with it, then persist to .env.
    - If ssid is empty: auto-reconnect using the saved .env value for the
      requested account type (demo=True → PO_SSID_DEMO, demo=False → PO_SSID_REAL).

    Returns 400 on malformed SSID, 401 on auth failure, 200 on success.
    """
    sm = get_session_manager()

    try:
        effective_ssid = _resolve_ssid(body.ssid, body.demo)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error_code": "ssid_missing", "message": str(exc)},
        )

    # Validate SSID format before attempting connection (fail fast)
    try:
        from ..session.pocket_option_session import PocketOptionSession
        PocketOptionSession._parse_ssid(effective_ssid)
    except SSIDParseError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error_code": "ssid_parse_error",
                "message": str(exc),
                "hint": "SSID must be a full 42[\"auth\",{...}] WebSocket frame copied from Chrome DevTools.",
            },
        )

    try:
        state = sm.connect(effective_ssid)
    except RuntimeError as exc:
        # Connection succeeded format-wise but broker rejected auth
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error_code": "auth_failed",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Unexpected connect error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error_code": "connect_error",
                "message": str(exc),
            },
        )

    # Persist SSID to .env only after a confirmed successful connection
    try:
        _persist_ssid_to_env(effective_ssid, state.is_demo)
    except Exception as persist_exc:
        # Non-fatal: log but don't fail the connect response
        logger.warning("SSID persistence failed (non-fatal): %s", persist_exc)

    return JSONResponse(
        content={
            "ok": True,
            "connected": state.connected,
            "account_type": state.account_type,
            "is_demo": state.is_demo,
            "session_id": state.session_id,
            "balance": state.balance,
            "message": state.message,
        }
    )


@router.post("/disconnect")
async def disconnect_session() -> JSONResponse:
    """Disconnect the active Pocket Option session."""
    sm = get_session_manager()
    state = sm.disconnect()
    return JSONResponse(
        content={
            "ok": True,
            "connected": state.connected,
            "message": state.message,
        }
    )


@router.post("/clear-ssid")
async def clear_ssid(body: SessionSsidClearRequest) -> JSONResponse:
    """Clear the saved SSID for the requested account type."""
    key = _clear_ssid_from_env(body.demo)

    load_env_file(_env_file_path())
    has_demo = bool(os.environ.get("PO_SSID_DEMO", "").strip())
    has_real = bool(os.environ.get("PO_SSID_REAL", "").strip())

    return JSONResponse(
        content={
            "ok": True,
            "cleared_key": key,
            "has_demo_ssid": has_demo,
            "has_real_ssid": has_real,
            "message": f"Saved SSID cleared for {'demo' if body.demo else 'real'} account.",
        }
    )


@router.get("/status")
async def session_status() -> JSONResponse:
    """
    Return the current session state.

    Always reflects live state — never cached.
    """
    sm = get_session_manager()
    state = sm.snapshot()
    return JSONResponse(
        content={
            "ok": True,
            "connected": state.connected,
            "account_type": state.account_type,
            "is_demo": state.is_demo,
            "session_id": state.session_id,
            "balance": state.balance,
            "message": state.message,
        }
    )


@router.post("/auto-connect")
async def auto_connect_session(demo: bool = False) -> JSONResponse:
    """
    Auto-connect to Pocket Option by extracting the live SSID from Chrome via CDP.

    Requires Chrome to be running with --remote-debugging-port on the configured
    chrome_port (default 9222) and the user to be logged in to pocketoption.com.

    Steps:
      1. Query Chrome debug port for open tabs.
      2. Find the Pocket Option tab.
      3. Extract the 'ssid' cookie via CDP Network.getAllCookies.
      4. Format the SSID frame and connect via PocketOptionSession.
      5. Persist the SSID to .env on success.

    Returns 424 if Chrome is not running or no Pocket Option tab is found.
    Returns 404 if no SSID cookie is found in the Chrome session.
    Returns 401 if the SSID is found but authentication fails.
    Returns 200 on success.
    """
    settings = get_settings()
    sm = get_session_manager()

    # Step 1–4: Extract SSID from Chrome via CDP
    try:
        ssid_frame = await extract_ssid_from_chrome(
            chrome_port=settings.chrome_port,
            demo=demo,
            require_pocket_option_tab=True,
        )
    except CDPError as exc:
        logger.warning("CDP extraction failed: %s", exc)
        return JSONResponse(
            status_code=424,
            content={
                "ok": False,
                "error_code": "cdp_error",
                "message": str(exc),
                "hint": (
                    "Ensure Chrome is running with --remote-debugging-port="
                    f"{settings.chrome_port} and you are logged in to pocketoption.com."
                ),
            },
        )
    except SSIDNotFoundError as exc:
        logger.warning("SSID cookie not found: %s", exc)
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "error_code": "ssid_not_found",
                "message": str(exc),
                "hint": "Log in to pocketoption.com in the Chrome window and try again.",
            },
        )

    # Validate the extracted frame before connecting (fail fast)
    try:
        from ..session.pocket_option_session import PocketOptionSession
        PocketOptionSession._parse_ssid(ssid_frame)
    except SSIDParseError as exc:
        logger.error("Extracted SSID frame failed validation: %s", exc)
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error_code": "ssid_parse_error",
                "message": f"Extracted SSID failed format validation: {exc}",
            },
        )

    # Step 5: Connect
    try:
        state = sm.connect(ssid_frame)
    except RuntimeError as exc:
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error_code": "auth_failed",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Unexpected auto-connect error: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error_code": "connect_error",
                "message": str(exc),
            },
        )

    # Persist to .env on success (non-fatal if it fails)
    try:
        _persist_ssid_to_env(ssid_frame, state.is_demo)
    except Exception as persist_exc:
        logger.warning("SSID persistence failed (non-fatal): %s", persist_exc)

    return JSONResponse(
        content={
            "ok": True,
            "connected": state.connected,
            "account_type": state.account_type,
            "is_demo": state.is_demo,
            "session_id": state.session_id,
            "balance": state.balance,
            "message": state.message,
            "source": "cdp_auto_extract",
        }
    )


@router.get("/ssid-status")
async def ssid_status() -> JSONResponse:
    """
    Report which SSIDs are saved in .env.

    Used by the frontend to show whether auto-reconnect is available
    for demo and/or real accounts without exposing the SSID values.
    """
    # Re-read .env to pick up any changes made since server start
    load_env_file(_env_file_path())

    has_demo = bool(os.environ.get("PO_SSID_DEMO", "").strip())
    has_real = bool(os.environ.get("PO_SSID_REAL", "").strip())

    return JSONResponse(
        content={
            "ok": True,
            "has_demo_ssid": has_demo,
            "has_real_ssid": has_real,
        }
    )
