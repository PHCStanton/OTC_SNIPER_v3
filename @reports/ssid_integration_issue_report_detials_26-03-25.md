# OTC SNIPER v3: SSID Integration Issue Report

**Date:** 2026-03-25  
**Topic:** Connection architecture between Pocket Option WebSocket API and Chrome Session active authentication  
**Status:** Architecture Design / Pending Implementation

---

## 1. The Issue Summary

The core requirement of OTC SNIPER v3 is to establish a persistent, authenticated WebSocket connection to the Pocket Option API. This connection requires a valid `ssid` (Session ID) tied to a logged-in User Account.

Currently, the `netstat_chrome_session.bat` script successfully opens a persistent Chrome session enabling the user to authenticate with Pocket Option. However, the v3 backend server (`main.py`) relies on manual transmission of the `ssid`. The testing utility `test_ssid_fixed.py` perfectly validates these SSIDs, but relies on keyboard input or a static `pocket_option_config.json` file. 

**The missing link:** There is no automated bridge in the v3 architecture that programmatically extracts the live `ssid` from the running Chrome session (Port 9222) and feeds it into the FastAPI WebSocket connection payload.

## 2. Involved Files & Scripts

### Current Pipeline
*   **`netstat_chrome_session.bat` / `netstat_chrome_session.py`**
    Starts the Chrome instance using `--remote-debugging-port=9222` and sets the User Data Directory. This guarantees Chrome exposes its state via the Chrome DevTools Protocol (CDP).
*   **`test_ssid_fixed.py`**
    A testing script confirming that creating a `PocketOption` instance with a valid 32-character hexadecimal SSID generates a successful WebSocket connection and balance readout. It requires manual input.
*   **`app/backend/session/pocket_option_session.py`**
    The v3 backend class responsible for maintaining the Pocket Option state, managing global resets, and passing the SSID string into the `PocketOption` API library.
*   **`app/backend/main.py` & `app/backend/api/session.py`**
    The FastAPI application exposing the `POST /api/session/connect` endpoint, which currently expects the raw `ssid` string formatted as a JSON payload from a frontend or Swagger UI.

### Legacy Context
*   **`legacy_reference/backend_reuse/data_streaming/ops.py`**
    In v2, an "Ops Layer" handled starting/stopping Chrome and executing a "Collector" script which actively managed the SSID extraction. This layer has not yet been ported to v3.
*   **`ssid_integration_package/`**
    Contains backward-compatible wrappers and documentation, but lacks the automated Chrome CDP scraping mechanism.

## 3. Analysis & Evaluation

**The Frontend vs. Backend Extraction Dilemma:**

The user raised a valid point: *"Whether we launch the Session in the Frontend or in the Backend, the Server still needs to process the SSID that is relevant to the Chrome Session that is running."*

*   **Frontend Approach:** A Chrome Extension or Desktop App (Electron) could read the cookies natively and send them to the backend. However, if the user operates only a Web UI hitting a remote backend, standard sandboxed browser JS *cannot* read `pocketoption.com` cross-site cookies due to strict CSP/CORS security.
*   **Backend Approach (Recommended):** Because the backend runs on the same machine running `netstat_chrome_session.bat` (localhost), the backend can use standard HTTP requests to tap directly into Chrome's DevTools Protocol (`http://127.0.0.1:9222`). This bypasses all browser security sandboxes, extracting the cookie cleanly and autonomously.

## 4. Proposed Recommendation: The Automated CDP Extractor

To eliminate manual copy-pasting and ensure the server is always synced with the living Chrome session, we recommend building an **Automated CDP (Chrome DevTools Protocol) Extractor** natively into the v3 FastAPI backend.

### The Architecture:

1.  **New Service: `app/backend/services/ssid_extractor.py`**
    *   A lightweight, dependency-free utility using Python's built-in `urllib` and `websockets` (or `aiohttp` websockets, since FastAPI is async).
    *   It will query `http://127.0.0.1:9222/json/list` to locate the active `pocketoption.com` tab.
    *   It will connect to that tab's `webSocketDebuggerUrl`.
    *   It will dispatch the CDP JSON-RPC command: `{"id": 1, "method": "Network.getAllCookies"}`.
    *   It parses the result, isolating the cookie where `name == "ssid"` and `domain == ".pocketoption.com"`.

2.  **Payload Formatter:**
    *   The raw 32-character hex cookie must be wrapped into the protocol string expected by `PocketOptionSession`:
        `42["auth",{"session":"<RAW_SSID>","isDemo":<1_OR_0>,"uid":0,"platform":2,"isFastHistory":true,"isOptimized":true}]`
    *   This logic will be encapsulated defensively to fail loudly if the Chrome session is closed or logged out.

3.  **New API Endpoint: `POST /api/session/auto-connect`**
    *   A new endpoint in the FastAPI application.
    *   Instead of accepting an `"ssid"` payload from the client, this endpoint requires *no payload*.
    *   When triggered, it invokes `ssid_extractor.py`, formatting the payload, and passing it directly into the `PocketOptionSession.connect()` flow.

### Next Steps for Execution:

1.  Create `app/backend/services/ssid_extractor.py`.
2.  Add required websocket libraries to `environment.yml` or `requirements.txt` if not already present.
3.  Implement the `/api/session/auto-connect` route.
4.  Optionally port the Chrome Start/Stop ops endpoints from v2 to natively manage the Chrome lifecycle directly via the Swagger UI or Frontend.

By adopting this backend-first programmatic extraction, the system becomes highly decoupled from frontend limitations while maintaining a direct, secure line to the user's authenticating browser instance.
