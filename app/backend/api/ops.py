"""
Phase 0 — Ops Layer: Chrome lifecycle endpoints.

Ported and simplified from QuFLX-v2 backend/services/gateway/routes/ops.py.

Security model (identical to v2):
  - QFLX_ENABLE_OPS=1 must be set in .env
  - Requests must originate from 127.0.0.1 / ::1
  - Optional QFLX_OPS_TOKEN header for extra protection

Chrome spawn flags deliberately omit --disable-web-security and
--allow-running-insecure-content (security improvement over v2).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from ..config import get_settings

router = APIRouter(prefix="/api/ops", tags=["ops"])
logger = logging.getLogger("otc_sniper.ops")

# ── In-process Chrome registry ────────────────────────────────────────────────
_ops_lock = asyncio.Lock()

_chrome_entry: Dict[str, Any] = {
    "proc": None,
    "pid": None,
    "started_at": None,
    "last_error": None,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _json_error(
    *,
    status_code: int,
    error_code: str,
    error_message: str,
    user_message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "ok": False,
        "error_code": error_code,
        "error_message": error_message,
        "user_message": user_message,
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def _client_host(request: Request) -> str:
    if request.client is None:
        return ""
    return request.client.host or ""


def _is_local_client(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "testclient"}


def _check_dev_gate(
    request: Request, ops_token: Optional[str]
) -> Optional[JSONResponse]:
    """Enforce ops security: env flag + localhost-only + optional token."""
    if not get_settings().enable_ops:
        return _json_error(
            status_code=403,
            error_code="ops_disabled",
            error_message="QFLX_ENABLE_OPS is not enabled",
            user_message="Ops controls are disabled. Set QFLX_ENABLE_OPS=1 in .env to enable.",
        )

    host = _client_host(request)
    if not _is_local_client(host):
        return _json_error(
            status_code=403,
            error_code="ops_local_only",
            error_message=f"Ops endpoints are local-only. client_host={host}",
            user_message="Ops controls are only accessible from the local machine.",
        )

    expected_token = os.getenv("QFLX_OPS_TOKEN", "").strip()
    if expected_token:
        provided = (ops_token or "").strip()
        if provided != expected_token:
            return _json_error(
                status_code=403,
                error_code="ops_token_required",
                error_message="Missing or invalid ops token",
                user_message="A valid ops token is required to use local controls.",
            )

    return None


def _is_port_open(host: str, port: int, timeout_s: float = 0.4) -> bool:
    """Probe whether a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except Exception:
        return False


def _find_chrome_executable() -> Optional[str]:
    """
    Locate the Chrome executable.

    Resolution order:
      1. CHROME_PATH env var (set in .env or environment)
      2. config.chrome_executable (same source, already parsed)
      3. PATH shutil.which
      4. Well-known Windows install locations
    """
    settings = get_settings()

    # 1. Explicit override from config / env
    if settings.chrome_executable:
        from pathlib import Path
        p = Path(settings.chrome_executable)
        if p.exists():
            return str(p)
        logger.warning("CHROME_PATH set to %r but file not found — falling back to auto-detect", settings.chrome_executable)

    # 2. PATH
    which = shutil.which("chrome") or shutil.which("chrome.exe")
    if which:
        return which

    # 3. Windows well-known locations
    from pathlib import Path
    candidates = []
    for base_env in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        base = os.getenv(base_env)
        if base:
            candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def _cleanup_if_exited(entry: Dict[str, Any]) -> None:
    """Clear registry entry if the tracked process has already exited."""
    proc = entry.get("proc")
    if proc is None:
        return
    try:
        exited = proc.poll() is not None
    except Exception:
        exited = True
    if exited:
        entry["proc"] = None
        entry["pid"] = None


def _spawn_chrome(chrome_path: str) -> subprocess.Popen:
    """
    Spawn Chrome with remote debugging enabled.

    Security: --disable-web-security and --allow-running-insecure-content
    are intentionally excluded (improvement over v2).
    Set CHROME_INSECURE_MODE=1 in .env only if absolutely required.
    """
    settings = get_settings()
    profile_dir = settings.chrome_profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    args = [
        chrome_path,
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
        "--disable-popup-blocking",
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={settings.chrome_port}",
        f"--user-data-dir={profile_dir}",
    ]

    # Insecure mode: opt-in only, never default
    if os.getenv("CHROME_INSECURE_MODE", "").strip() == "1":
        logger.warning(
            "CHROME_INSECURE_MODE=1 — launching Chrome with --disable-web-security. "
            "Only use this in a controlled local environment."
        )
        args += ["--disable-web-security", "--allow-running-insecure-content"]

    if settings.chrome_url:
        args.append(settings.chrome_url)

    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_process(proc: subprocess.Popen) -> None:
    """Gracefully terminate, then force-kill after timeout."""
    try:
        proc.terminate()
        proc.wait(timeout=3)
        return
    except Exception:
        pass
    try:
        proc.kill()
        proc.wait(timeout=3)
    except Exception:
        pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/chrome/start")
async def start_chrome(
    request: Request,
    x_qflx_ops_token: Optional[str] = Header(default=None),
) -> JSONResponse:
    """
    Spawn Chrome with remote debugging on the configured port (default 9222).

    Idempotent: if the port is already listening, returns already_running.
    """
    gate_err = _check_dev_gate(request, x_qflx_ops_token)
    if gate_err is not None:
        return gate_err

    settings = get_settings()

    try:
        # Fast path: port already open (Chrome running externally or from a previous start)
        if _is_port_open("127.0.0.1", settings.chrome_port):
            return JSONResponse(
                content={"ok": True, "status": "already_running", "port": settings.chrome_port}
            )

        chrome_path = _find_chrome_executable()
        if not chrome_path:
            return _json_error(
                status_code=424,
                error_code="chrome_not_found",
                error_message="Chrome executable not found",
                user_message=(
                    "Chrome executable not found. "
                    "Ensure Chrome is installed or set CHROME_PATH in .env."
                ),
                details={"hint": "Set CHROME_PATH=C:\\path\\to\\chrome.exe in app/.env"},
            )

        async with _ops_lock:
            _cleanup_if_exited(_chrome_entry)
            if _chrome_entry.get("proc") is not None:
                return JSONResponse(
                    content={
                        "ok": True,
                        "status": "already_running",
                        "pid": _chrome_entry["pid"],
                        "port": settings.chrome_port,
                    }
                )

            proc = _spawn_chrome(chrome_path)
            _chrome_entry["proc"] = proc
            _chrome_entry["pid"] = proc.pid
            _chrome_entry["started_at"] = datetime.now(timezone.utc).isoformat()
            _chrome_entry["last_error"] = None

        logger.info("Chrome started — pid=%s port=%s", proc.pid, settings.chrome_port)
        return JSONResponse(
            content={
                "ok": True,
                "status": "started",
                "pid": proc.pid,
                "port": settings.chrome_port,
            }
        )

    except Exception as exc:
        logger.error("Chrome start failed: %s", exc, exc_info=True)
        async with _ops_lock:
            _chrome_entry["last_error"] = str(exc)
        return _json_error(
            status_code=500,
            error_code="chrome_start_failed",
            error_message=str(exc),
            user_message="Failed to start Chrome. Check server logs for details.",
        )


@router.post("/chrome/stop")
async def stop_chrome(
    request: Request,
    x_qflx_ops_token: Optional[str] = Header(default=None),
) -> JSONResponse:
    """Terminate the Chrome process managed by this server."""
    gate_err = _check_dev_gate(request, x_qflx_ops_token)
    if gate_err is not None:
        return gate_err

    try:
        async with _ops_lock:
            _cleanup_if_exited(_chrome_entry)
            proc = _chrome_entry.get("proc")
            if proc is None:
                return JSONResponse(content={"ok": True, "status": "already_stopped"})

        await asyncio.to_thread(_stop_process, proc)

        async with _ops_lock:
            _chrome_entry["proc"] = None
            _chrome_entry["pid"] = None
            _chrome_entry["started_at"] = None

        logger.info("Chrome stopped")
        return JSONResponse(content={"ok": True, "status": "stopped"})

    except Exception as exc:
        logger.error("Chrome stop failed: %s", exc, exc_info=True)
        return _json_error(
            status_code=500,
            error_code="chrome_stop_failed",
            error_message=str(exc),
            user_message="Failed to stop Chrome. Check server logs for details.",
        )


@router.get("/chrome/status")
async def chrome_status(
    request: Request,
    x_qflx_ops_token: Optional[str] = Header(default=None),
) -> JSONResponse:
    """
    Probe Chrome debug port availability.

    Always probes live — never returns stale cached state.
    """
    gate_err = _check_dev_gate(request, x_qflx_ops_token)
    if gate_err is not None:
        return gate_err

    settings = get_settings()
    port_open = _is_port_open("127.0.0.1", settings.chrome_port)

    async with _ops_lock:
        _cleanup_if_exited(_chrome_entry)
        managed_pid = _chrome_entry.get("pid")
        started_at = _chrome_entry.get("started_at")
        last_error = _chrome_entry.get("last_error")

    return JSONResponse(
        content={
            "ok": True,
            "running": port_open,
            "port": settings.chrome_port,
            "managed_pid": managed_pid,
            "started_at": started_at,
            "last_error": last_error,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get("/status")
async def combined_status(
    request: Request,
    x_qflx_ops_token: Optional[str] = Header(default=None),
) -> JSONResponse:
    """
    Combined ops status: Chrome availability + active session state.

    Used by the frontend TopBar for badge rendering.
    Chrome status and session status are reported as separate fields —
    they are distinct states (Chrome running ≠ authenticated session).
    """
    gate_err = _check_dev_gate(request, x_qflx_ops_token)
    if gate_err is not None:
        return gate_err

    settings = get_settings()
    chrome_running = _is_port_open("127.0.0.1", settings.chrome_port)

    # Import here to avoid circular imports at module load time
    from ..dependencies import get_session_manager
    sm = get_session_manager()
    session_snap = sm.snapshot()

    async with _ops_lock:
        _cleanup_if_exited(_chrome_entry)
        managed_pid = _chrome_entry.get("pid")

    return JSONResponse(
        content={
            "ok": True,
            "chrome": {
                "running": chrome_running,
                "port": settings.chrome_port,
                "managed_pid": managed_pid,
            },
            "session": {
                "connected": session_snap.connected,
                "account_type": session_snap.account_type,
                "is_demo": session_snap.is_demo,
                "balance": session_snap.balance,
            },
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
