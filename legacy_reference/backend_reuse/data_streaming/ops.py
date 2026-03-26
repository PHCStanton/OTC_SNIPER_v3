"""
Ops Router for OTC Sniper Gateway

Provides process control endpoints for Chrome and Collector.
SECURITY: All endpoints require:
  - QFLX_ENABLE_OPS=1 environment variable
  - Localhost connection (127.0.0.1 or ::1)
  - X-QFLX-OPS-TOKEN header (if configured)

Idempotent: Start returns "already_running" if already started.
"""

import sys
import os
import asyncio
import subprocess
import socket
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

# =============================================================================
# LOGGING
# =============================================================================
logger = logging.getLogger("OTCSniper.Ops")

# =============================================================================
# CONFIG
# =============================================================================
OPS_TOKEN = os.environ.get("QFLX_OPS_TOKEN", "")
OPS_ENABLED = os.environ.get("QFLX_ENABLE_OPS", "0") == "1"
DEV_HOSTS = {"127.0.0.1", "::1", "localhost"}

# Chrome settings
CHROME_DEBUG_PORT = 9222
CHROME_USER_DATA_DIR = Path(os.environ.get(
    "QFLX_CHROME_DATA_DIR",
    str(Path(__file__).parent.parent.parent.parent / "Chrome_profile" / "debug")
))

# Chrome profile — use the SAME profile as main QuFLX-v2 gateway so sessions persist
CHROME_PROFILE_DIR = Path(__file__).parent.parent.parent.parent / "Chrome_profile"

# Collector settings — self-contained collector for ssid/web_app
# This collector lives in ssid/web_app/backend/src/collector_main.py
_BACKEND_DIR = Path(__file__).resolve().parents[1]  # ssid/web_app/backend
_COLLECTOR_ENTRY = _BACKEND_DIR / "src" / "collector_main.py"
_DATA_DIR = Path(__file__).parent.parent.parent / "data"
LOG_DIR = _DATA_DIR / "data_output" / "logs"

# ============================================================================
# MODELS
# ============================================================================

class OpStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ALREADY_RUNNING = "already_running"
    ALREADY_STOPPED = "already_stopped"
    FAILED = "failed"

class ChromeStartRequest(BaseModel):
    url: Optional[str] = None  # Target URL to open

class OpResponse(BaseModel):
    ok: bool
    status: OpStatus
    message: str
    pid: Optional[int] = None
    log_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ProcessStatus(BaseModel):
    name: str
    running: bool
    pid: Optional[int] = None
    started_at: Optional[str] = None
    last_error: Optional[str] = None
    log_path: Optional[str] = None

class StatusResponse(BaseModel):
    ok: bool
    processes: Dict[str, ProcessStatus]
    observed_at: str

# ============================================================================
# PROCESS REGISTRY
# ============================================================================

@dataclass
class ProcessRecord:
    """Tracks a managed subprocess."""
    name: str
    process: Optional[subprocess.Popen] = None
    started_at: Optional[datetime] = None
    last_error: Optional[str] = None
    log_path: Optional[Path] = None

class ProcessRegistry:
    """Thread-safe process registry with asyncio lock."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._chrome: Optional[ProcessRecord] = None
        self._collector: Optional[ProcessRecord] = None

    def _ensure_log_dir(self) -> Path:
        """Ensure log directory exists."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        return LOG_DIR

    def _get_log_path(self, name: str) -> Path:
        """Generate timestamped log path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._ensure_log_dir() / f"{name}_{timestamp}.log"

    async def is_port_open(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a port is already listening."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
            return False

    async def start_chrome(self, target_url: Optional[str] = None) -> OpResponse:
        """Start Chrome with remote debugging."""
        async with self._lock:
            # Check if already running
            if self._chrome and self._chrome.process and self._chrome.process.poll() is None:
                return OpResponse(
                    ok=True,
                    status=OpStatus.ALREADY_RUNNING,
                    message="Chrome is already running",
                    pid=self._chrome.process.pid
                )

            # Check if port 9222 is already open
            if await self.is_port_open(CHROME_DEBUG_PORT):
                return OpResponse(
                    ok=True,
                    status=OpStatus.ALREADY_RUNNING,
                    message="Chrome remote debugging port 9222 is already in use",
                    details={"port": CHROME_DEBUG_PORT}
                )

            # Find Chrome executable
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.environ.get("QFLX_CHROME_PATH", ""),
            ]
            chrome_path = None
            for path in chrome_paths:
                if path and Path(path).exists():
                    chrome_path = path
                    break

            if not chrome_path:
                return OpResponse(
                    ok=False,
                    status=OpStatus.FAILED,
                    message="Chrome executable not found. Please ensure Chrome is installed.",
                    details={"searched_paths": chrome_paths}
                )

            # Ensure user data dir exists — use same profile as main QuFLX gateway
            CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

            # Default URL
            if not target_url:
                target_url = "https://pocketoption.com"

            # Build command — A2b: removed --disable-web-security (security fix)
            # Pocket Option works without it; the flag disabled same-origin policy
            # for ALL tabs, exposing the user to cross-site attacks.
            cmd = [
                chrome_path,
                "--new-window",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--allow-running-insecure-content",
                "--remote-debugging-address=127.0.0.1",
                f"--remote-debugging-port={CHROME_DEBUG_PORT}",
                f"--user-data-dir={str(CHROME_PROFILE_DIR)}",
            ]
            if target_url:
                cmd.append(target_url)

            log_path = self._get_log_path("chrome")

            try:
                with open(log_path, "w") as log_file:
                    self._chrome = ProcessRecord(
                        name="chrome",
                        process=subprocess.Popen(
                            cmd,
                            stdout=log_file,
                            stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                        ),
                        started_at=datetime.now(),
                        log_path=log_path
                    )

                # Give it a moment to start
                await asyncio.sleep(0.5)

                # Verify it started
                if self._chrome.process.poll() is not None:
                    return OpResponse(
                        ok=False,
                        status=OpStatus.FAILED,
                        message="Chrome process exited immediately after launch",
                        details={"exit_code": self._chrome.process.poll(), "log": str(log_path)}
                    )

                logger.info(f"Chrome started with PID {self._chrome.process.pid}")
                return OpResponse(
                    ok=True,
                    status=OpStatus.RUNNING,
                    message="Chrome started successfully",
                    pid=self._chrome.process.pid,
                    log_path=str(log_path)
                )

            except Exception as e:
                logger.error(f"Failed to start Chrome: {e}")
                return OpResponse(
                    ok=False,
                    status=OpStatus.FAILED,
                    message=f"Failed to start Chrome: {str(e)}",
                    details={"error": str(e)}
                )

    async def stop_chrome(self) -> OpResponse:
        """Stop Chrome process."""
        async with self._lock:
            if not self._chrome or self._chrome.process is None or self._chrome.process.poll() is not None:
                return OpResponse(
                    ok=True,
                    status=OpStatus.ALREADY_STOPPED,
                    message="Chrome is not running"
                )

            try:
                pid = self._chrome.process.pid
                
                # Graceful terminate first
                self._chrome.process.terminate()
                
                try:
                    # FIX ISSUE-9: Use get_running_loop() instead of deprecated get_event_loop()
                    await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(None, self._chrome.process.wait),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    # Force kill if still running
                    self._chrome.process.kill()
                    self._chrome.process.wait()

                logger.info(f"Chrome (PID {pid}) stopped")
                self._chrome = None

                return OpResponse(
                    ok=True,
                    status=OpStatus.STOPPED,
                    message="Chrome stopped successfully",
                    pid=pid
                )

            except Exception as e:
                logger.error(f"Failed to stop Chrome: {e}")
                return OpResponse(
                    ok=False,
                    status=OpStatus.FAILED,
                    message=f"Failed to stop Chrome: {str(e)}"
                )

    async def start_collector(self) -> OpResponse:
        """Start the QuFLX v2 Collector."""
        async with self._lock:
            # Check if already running
            if self._collector and self._collector.process and self._collector.process.poll() is None:
                return OpResponse(
                    ok=True,
                    status=OpStatus.ALREADY_RUNNING,
                    message="Collector is already running",
                    pid=self._collector.process.pid
                )

            # Verify collector file exists
            if not _COLLECTOR_ENTRY.exists():
                return OpResponse(
                    ok=False,
                    status=OpStatus.FAILED,
                    message="Collector entry point not found",
                    details={"expected_path": str(_COLLECTOR_ENTRY)}
                )

            log_path = self._get_log_path("collector")

            try:
                with open(log_path, "w") as log_file:
                    self._collector = ProcessRecord(
                        name="collector",
                        process=subprocess.Popen(
                            [sys.executable, str(_COLLECTOR_ENTRY)],
                            stdout=log_file,
                            stderr=subprocess.STDOUT,
                            cwd=str(_COLLECTOR_ENTRY.parent),
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                        ),
                        started_at=datetime.now(),
                        log_path=log_path
                    )

                # Give it a moment to start
                await asyncio.sleep(0.5)

                # Verify it started
                if self._collector.process.poll() is not None:
                    return OpResponse(
                        ok=False,
                        status=OpStatus.FAILED,
                        message="Collector process exited immediately after launch",
                        details={"exit_code": self._collector.process.poll(), "log": str(log_path)}
                    )

                logger.info(f"Collector started with PID {self._collector.process.pid}")
                return OpResponse(
                    ok=True,
                    status=OpStatus.RUNNING,
                    message="Collector started successfully",
                    pid=self._collector.process.pid,
                    log_path=str(log_path)
                )

            except Exception as e:
                logger.error(f"Failed to start Collector: {e}")
                return OpResponse(
                    ok=False,
                    status=OpStatus.FAILED,
                    message=f"Failed to start Collector: {str(e)}",
                    details={"error": str(e)}
                )

    async def stop_collector(self) -> OpResponse:
        """Stop the Collector process."""
        async with self._lock:
            if not self._collector or self._collector.process is None or self._collector.process.poll() is not None:
                return OpResponse(
                    ok=True,
                    status=OpStatus.ALREADY_STOPPED,
                    message="Collector is not running"
                )

            try:
                pid = self._collector.process.pid
                
                # Graceful terminate first
                self._collector.process.terminate()
                
                try:
                    # FIX ISSUE-9: Use get_running_loop() instead of deprecated get_event_loop()
                    await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(None, self._collector.process.wait),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    # Force kill if still running
                    self._collector.process.kill()
                    self._collector.process.wait()

                logger.info(f"Collector (PID {pid}) stopped")
                self._collector = None

                return OpResponse(
                    ok=True,
                    status=OpStatus.STOPPED,
                    message="Collector stopped successfully",
                    pid=pid
                )

            except Exception as e:
                logger.error(f"Failed to stop Collector: {e}")
                return OpResponse(
                    ok=False,
                    status=OpStatus.FAILED,
                    message=f"Failed to stop Collector: {str(e)}"
                )

    async def get_status(self) -> StatusResponse:
        """Get status of all managed processes."""
        processes = {}

        # Chrome status
        chrome_running = bool(self._chrome and self._chrome.process and self._chrome.process.poll() is None)
        processes["chrome"] = ProcessStatus(
            name="chrome",
            running=chrome_running,
            pid=self._chrome.process.pid if chrome_running and self._chrome else None,
            started_at=self._chrome.started_at.isoformat() if chrome_running and self._chrome and self._chrome.started_at else None,
            last_error=self._chrome.last_error if self._chrome and not chrome_running else None,
            log_path=str(self._chrome.log_path) if self._chrome and self._chrome.log_path else None
        )

        # Collector status
        collector_running = bool(self._collector and self._collector.process and self._collector.process.poll() is None)
        processes["collector"] = ProcessStatus(
            name="collector",
            running=collector_running,
            pid=self._collector.process.pid if collector_running and self._collector else None,
            started_at=self._collector.started_at.isoformat() if collector_running and self._collector and self._collector.started_at else None,
            last_error=self._collector.last_error if self._collector and not collector_running else None,
            log_path=str(self._collector.log_path) if self._collector and self._collector.log_path else None
        )

        return StatusResponse(
            ok=True,
            processes=processes,
            observed_at=datetime.now().isoformat()
        )


# ============================================================================
# SECURITY GUARD
# ============================================================================

async def verify_ops_access(
    request: Request,
    x_qflx_ops_token: Optional[str] = Header(None, alias="X-QFLX-OPS-TOKEN")
) -> None:
    """Verify the request has permission to use ops endpoints."""
    # Check if ops is enabled
    if not OPS_ENABLED:
        raise HTTPException(
            status_code=403,
            detail={
                "ok": False,
                "error_code": "OPS_DISABLED",
                "error_message": "Ops endpoints are disabled",
                "user_message": "Set QFLX_ENABLE_OPS=1 to enable ops endpoints"
            }
        )

    # Check if localhost
    client_host = request.client.host if request.client else ""
    if client_host not in DEV_HOSTS:
        raise HTTPException(
            status_code=403,
            detail={
                "ok": False,
                "error_code": "REMOTE_ACCESS_DENIED",
                "error_message": f"Ops endpoints can only be accessed from localhost (got {client_host})",
                "user_message": "Ops endpoints require localhost access"
            }
        )

    # Check token if configured
    if OPS_TOKEN and x_qflx_ops_token != OPS_TOKEN:
        raise HTTPException(
            status_code=401,
            detail={
                "ok": False,
                "error_code": "INVALID_TOKEN",
                "error_message": "Invalid ops token",
                "user_message": "Invalid or missing X-QFLX-OPS-TOKEN header"
            }
        )


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/ops", tags=["Ops"])
registry = ProcessRegistry()


@router.post("/chrome/start", response_model=OpResponse)
async def chrome_start(
    request: Request,
    body: ChromeStartRequest = ChromeStartRequest()
):
    """Start Chrome with remote debugging on port 9222."""
    await verify_ops_access(request)
    return await registry.start_chrome(body.url)


@router.post("/chrome/stop", response_model=OpResponse)
async def chrome_stop(request: Request):
    """Stop the Chrome process."""
    await verify_ops_access(request)
    return await registry.stop_chrome()


@router.post("/stream/start", response_model=OpResponse)
async def stream_start(request: Request):
    """Start the QuFLX v2 Collector."""
    await verify_ops_access(request)
    return await registry.start_collector()


@router.post("/stream/stop", response_model=OpResponse)
async def stream_stop(request: Request):
    """Stop the QuFLX v2 Collector."""
    await verify_ops_access(request)
    return await registry.stop_collector()


@router.get("/status", response_model=StatusResponse)
async def get_status(request: Request):
    """Get status of all managed processes."""
    await verify_ops_access(request)
    return await registry.get_status()
