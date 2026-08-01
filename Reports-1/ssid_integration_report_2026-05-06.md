# SSID Integration & Historical Candle Logic Report

**Report date:** 2026-05-06  
**Prepared for:** OTC SNIPER v3  
**Requested scope:** Delegate `.agents\Investigator.json` and `.agents\Reviewer.json`; investigate SSID integration and the implementation logic responsible for producing historical candles; provide recommendations for whether to develop this externally.  
**Report location:** `@reports/ssid_integration_report_2026-05-06.md`  
**Mode:** Read-only forensic investigation followed by documentation-only report writing. No functional code was modified.

---

## 1. Executive Summary

The SSID integration is now mostly functional for manual and backend CDP-assisted connection, but the frontend still presents the workflow as manual `.env` / DevTools copy-paste and does not expose the backend `/api/session/auto-connect` endpoint. The active v3 trading runtime does **not** currently rely on broker-provided historical candles; it produces rolling 1-minute candle context from live tick callbacks and recent tick-log replay inside `MarketContextEngine`.

The code responsible for broker historical candles is effectively outside the active v3 signal path and is risky to modify inside the current project because the runtime imports the installed PocketOptionAPI from `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi`, not the bundled `ssid_integration_package` copy. That installed API has a mutation-heavy, global-state historical-candle path with mismatched signatures, blocking waits, broad exception handling, and unclear semantics. If you want to improve historical candles, the safest recommendation is to develop and validate a standalone external candle module first, then integrate only through a narrow adapter after it proves stable.

---

## 2. Agent Delegation Record

### Delegating to @Investigator

**Task:** Perform read-only forensic analysis of SSID integration, session lifecycle, live tick routing, and historical candle/candle-generation logic.  
**Agent basis:** `.agents/Investigator.json` requires read-only root-cause analysis, exact file/line evidence, severity-rated findings, recommendations, and risk forecast.

### Delegating to @Reviewer

**Task:** Review the investigated implementation for readability, security, maintainability, separation of concerns, fail-fast validation, and explicit error handling.  
**Agent basis:** `.agents/Reviewer.json` requires constructive review of style, security, best practices, severity-rated issues, and suggestions.

---

## 3. Scope and Evidence Sources

### Project memory reviewed

- `.agent-memory/activeContext.md`
- `.agent-memory/systemPatterns.md`
- `.agent-memory/techContext.md`
- `.agent-memory/progress.md`
- `.agents/Investigator.json`
- `.agents/Reviewer.json`

### Main v3 runtime files reviewed

- `app/backend/api/session.py`
- `app/backend/services/ssid_extractor.py`
- `app/backend/session/pocket_option_session.py`
- `app/backend/session/manager.py`
- `app/backend/brokers/pocket_option/adapter.py`
- `app/backend/services/streaming.py`
- `app/backend/services/market_context.py`
- `app/backend/services/tick_logger.py`
- `app/backend/main.py`
- `app/backend/api/ops.py`
- `app/frontend/src/api/opsApi.js`
- `app/frontend/src/stores/useAuthStore.js`
- `app/frontend/src/components/auth/ConnectDialog.jsx`

### SSID integration package / installed PocketOptionAPI evidence

- `ssid_integration_package/pocketoptionapi/stable_api.py`
- `ssid_integration_package/pocketoptionapi/api.py`
- `ssid_integration_package/pocketoptionapi/ws/channels/candles.py`
- `ssid_integration_package/pocketoptionapi/ws/client.py`
- `ssid_integration_package/pocketoptionapi/ws/objects/candle.py`
- Installed runtime package path confirmed by command:
  - `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\stable_api.py`
  - `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\api.py`
  - `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\ws\channels\candles.py`
  - `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\ws\client.py`

---

## 4. Current Architecture Map

### 4.1 SSID connection flow currently implemented

```text
Chrome with remote debugging
    ↓
app/backend/api/ops.py starts Chrome on 127.0.0.1:9222
    ↓
Option A: Frontend/manual SSID connect
    app/frontend/src/components/auth/ConnectDialog.jsx
    → app/frontend/src/stores/useAuthStore.js
    → app/frontend/src/api/opsApi.js
    → POST /api/session/connect

Option B: Backend CDP auto-connect exists, but frontend does not expose it
    POST /api/session/auto-connect
    → app/backend/services/ssid_extractor.py
    → Chrome DevTools Protocol Network.getAllCookies
    → PocketOptionSession

SessionManager
    ↓
PocketOptionSession
    ↓
Installed pocketoptionapi.PocketOption
    ↓
WebSocket authentication using 42["auth", {...}]
```

### 4.2 Live tick → candle/context flow currently active

```text
PocketOptionAPI websocket tick message
    ↓
pocketoptionapi.global_value.set_csv(...)
    ↓ monkey-patched by
app/backend/session/pocket_option_session.py
    ↓
PocketOptionSession._tick_callback
    ↓
StreamingService.process_tick(...)
    ↓
StreamingService._process_tick_inner(...)
    ↓
MarketContextEngine.update_tick(...)
    ↓
1-minute rolling candle bucket + Level 2 / Level 3 market_context
    ↓
Socket.IO market_data payload + signal logger + Auto-Ghost candidate path
```

### 4.3 Broker historical candle flow currently *not* active in v3 signal path

```text
PocketOptionSession.get_candles(...)
    ↓
Installed PocketOption.get_candles(...)
    ↓
Installed PocketOptionAPI.getcandles / GetCandles
    ↓
WebSocket loadHistoryPeriod
    ↓
global history_new / history_data mutation

Status in v3 app: wrapper exists, but app search found no active call site in app/ except the wrapper itself.
```

---

## 5. SSID Integration Findings

### Strengths

1. **Fail-fast SSID parsing exists.**  
   `app/backend/session/pocket_option_session.py:104-127` validates the `42[...]` frame structure, event name, payload shape, and required `session` / `isDemo` fields before use.

2. **Manual connect and saved reconnect are implemented.**  
   `app/backend/api/session.py:144-227` resolves explicit or saved SSID values, validates format, connects, starts streaming, persists on success, and returns structured JSON.

3. **Backend CDP extraction exists.**  
   `app/backend/services/ssid_extractor.py:190-265` queries Chrome tabs, locates Pocket Option, retrieves cookies over CDP, extracts the `ssid` cookie, and formats the broker auth frame.

4. **Chrome ops are local-gated.**  
   `app/backend/api/ops.py:76-108` checks ops enabled, local client origin, and optional token before Chrome lifecycle actions.

5. **Tick callback uses thread-safe dispatch to the FastAPI loop.**  
   `app/backend/session/pocket_option_session.py:70-78` dispatches broker-thread ticks with `asyncio.run_coroutine_threadsafe(...)` and attaches a done callback for dispatch failures.

### Key SSID weaknesses

1. **Frontend does not expose backend auto-connect.**  
   Backend endpoint exists at `app/backend/api/session.py:292-410`, but frontend API exports only manual/session saved paths in `app/frontend/src/api/opsApi.js:24-31`. `ConnectDialog.jsx:194-196` still instructs the user to manually get the SSID from Chrome DevTools.

2. **Saved SSID is exposed back to the frontend in full.**  
   `app/backend/api/session.py:436-448` returns the saved SSID value. `app/frontend/src/stores/useAuthStore.js:27-34` loads it into client state, and `app/frontend/src/components/auth/ConnectDialog.jsx:150-156` displays it in a textarea. This is convenient locally but risky if the backend is ever accessible beyond the local machine.

3. **Streaming startup failure after a successful session is non-fatal.**  
   `app/backend/api/session.py:203-208` and `app/backend/api/session.py:392-397` log streaming startup failure as a warning but still return session success. This can produce a misleading state: authenticated session connected, but no ticks, no rolling candles, no signals.

4. **Tick hook installation has a silent ImportError path.**  
   `app/backend/session/pocket_option_session.py:44-89` monkey-patches `pocketoptionapi.global_value.set_csv`, but `app/backend/session/pocket_option_session.py:88-89` uses `except ImportError: pass`.

   > “This catch block swallows the error and will cause silent failures in production. Must either log + re-throw, return a proper error response, or show a user-friendly message.”

---

## 6. Historical Candle / Candle Production Deep Dive

The term **historical candles** currently refers to two different things in this project:

1. **Active v3 candle context:** candles reconstructed from live ticks and recent tick logs.
2. **Broker historical candles:** candles requested from Pocket Option through `loadHistoryPeriod`.

These are not the same implementation, and they carry different risks.

---

### 6.1 Active v3 candle production: `MarketContextEngine`

The actual v3 signal stack uses `MarketContextEngine`, not broker historical candles.

#### Evidence

- `app/backend/services/streaming.py:190-194`
  - `market_context_engine.update_tick(price, timestamp=timestamp)` is called for each accepted tick.
- `app/backend/services/market_context.py:249-265`
  - Buckets each tick into a 60-second candle window.
  - Creates `_current_candle` on first tick.
  - Updates high/low/close while the timestamp remains in the same bucket.
  - Moves the completed candle into `_closed_candles` when the bucket changes.
- `app/backend/services/market_context.py:261-265`
  - Appends the previous candle to `_closed_candles` and starts a new current candle.
- `app/backend/services/market_context.py:262-263`
  - Retains only the last `max_candles`, default 240.
- `app/backend/services/market_context.py:267-348`
  - Recomputes ADX, CCI, support/resistance pivots, and CCI divergence only when cache is empty or a candle closes.
- `app/backend/services/market_context.py:376-405`
  - Returns the `market_context` payload, including `candle_count`, `candle_closed`, ATR, ADX, CCI, structure levels, tick frequency, tick health, and divergence.

#### Current behavior

- Candle period is fixed at 60 seconds by `Level2Config.candle_seconds` in `app/backend/services/market_context.py:39-41`.
- Max rolling candle history is 240 closed candles by `Level2Config.max_candles` in `app/backend/services/market_context.py:40-41`.
- Readiness requires enough closed candles for ADX/CCI/pivots at `app/backend/services/market_context.py:327-329`.
- Tick health is computed per tick at `app/backend/services/market_context.py:350-359`.

#### Important caveat

`MarketContextEngine` is a **live tick-derived candle builder**, not a broker historical-candle provider. It does not call Pocket Option historical APIs. It cannot fill deep history on startup unless prior raw ticks exist in the local tick logs.

---

### 6.2 Startup warmup / pseudo-history: `TickLogger.load_recent`

The app attempts to seed engines from locally persisted raw ticks.

#### Evidence

- `app/backend/services/streaming.py:140-145`
  - Loads recent ticks with `self.tick_logger.load_recent(asset, max_ticks=300)`.
  - Replays each tick into OTEO and `MarketContextEngine.seed_tick(...)`.
- `app/backend/services/tick_logger.py:48-78`
  - Reads only the most recent dated JSONL file for the asset.
  - Loads the last `max_ticks`, default 300.
  - Logs corrupt-load failures as warnings.

#### Meaning

This provides short local continuity after restart, but it is not true historical candle backfill. At approximately one tick per second, 300 ticks is roughly 5 minutes of data, while the context engine requires up to 16 closed candles for readiness (`app/backend/services/market_context.py:327-329`). Therefore, Level 2/Level 3 may still need live warmup after restart.

---

### 6.3 Broker historical candles: wrapper exists but is unused in active v3 app

#### Evidence

- `app/backend/session/pocket_option_session.py:298-301`
  - Provides `get_candles(self, active, timeframe, count)` and forwards to `self._api.get_candles(...)`.
- Search across `app/` found no active call site for `get_candles(...)`, `get_candles_data(...)`, `loadHistoryPeriod`, `process_data_history`, `process_candle`, `CandleCollection`, or `history_data` except the wrapper above.

#### Meaning

Broker-provided historical candles are not part of the active v3 signal, sparkline, Auto-Ghost, or Level 2/Level 3 context path at this time.

---

### 6.4 Installed PocketOptionAPI candle behavior is materially different from bundled package code

The project contains `ssid_integration_package/pocketoptionapi/...`, but runtime imports the installed package from:

```text
C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi
```

This was confirmed by command output showing `pocketoptionapi.__file__`, `stable_api.__file__`, `api.__file__`, `candles.__file__`, and `client.__file__` all resolving to the `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi` path.

#### Runtime installed API evidence

- Installed `stable_api.py:326-408` implements `get_candles(self, active, period, start_time=None, count=6000, count_request=3)` and returns `True` / `False`, while mutating `global_value.pairs`, rather than returning a list of candles.
- Installed `stable_api.py:343-353` calls `self.api.change_symbol(active, period)` and waits for `self.api.history_new`.
- Installed `stable_api.py:365-381` calls `self.api.getcandles(active, period, time_red)` and accumulates `self.api.history_data`.
- Installed `stable_api.py:386-394` transforms `his['candles']` and `his['history']` into `c0` and `c1`.
- Installed `stable_api.py:395-403` writes data into `global_value.pairs[active]`.
- Installed `ws/channels/candles.py:25-37` sends a `loadHistoryPeriod` message with:
  - random `index`
  - `time = end_time + 7200`
  - fixed `offset_count(interval)`
  - `period = interval`

#### Bundled package copy differs

The bundled `ssid_integration_package/pocketoptionapi/stable_api.py:258-291` has a list-returning `get_candles(self, active, timeframe, count)` implementation that calls `self.api.get_candles_data(...)` and validates `[time, open, high, low, close]` rows. This is **not** the installed runtime code currently imported by the app.

#### Consequence

The v3 wrapper in `app/backend/session/pocket_option_session.py:298-301` assumes a simple `get_candles(active, timeframe, count)` call. Against the installed runtime signature, the third argument maps to `start_time`, not candle count. If the wrapper is used as-is against the installed package, it is very likely to return `True` / `False` or mutate globals rather than produce the candle list the wrapper name implies.

This is the main reason I agree with your caution: modifying or depending on this path inside the current project could destabilize the session, tick stream, and signal logic.

---

## 7. @Investigator Findings

### 7.1 Summary

The SSID/session path is operational but split between manual frontend workflow and backend CDP auto-connect. Historical candles are not integrated into the active v3 runtime; the active system builds candles from live ticks, while the broker historical-candle path is unused and risky because the installed runtime package differs from the bundled package code.

### 7.2 Critical Issues

| Severity | Finding | Evidence | Impact |
|---|---|---|---|
| HIGH | Broker historical candle wrapper is misleading against installed runtime API | `app/backend/session/pocket_option_session.py:298-301`; installed `stable_api.py:326-408` | If used, expected list-returning candle behavior may not happen; global mutation / boolean return can break callers. |
| HIGH | Saved SSID is exposed to frontend in full | `app/backend/api/session.py:436-448`; `useAuthStore.js:27-34`; `ConnectDialog.jsx:150-156` | SSID is an authentication secret. Safe only under strict local assumptions; dangerous if backend/frontend are exposed. |
| HIGH | Tick hook installation can fail silently on ImportError | `app/backend/session/pocket_option_session.py:88-89` | No tick callback means no live candles, no OTEO, no Level 2/3 context, and no clear user-facing reason. |
| MEDIUM | Frontend lacks auto-connect despite backend CDP implementation | Backend `app/backend/api/session.py:292-410`; frontend `opsApi.js:24-31`; `ConnectDialog.jsx:194-196` | User still performs manual SSID workflow even though backend automation exists. |
| MEDIUM | Streaming startup is non-fatal after connection success | `app/backend/api/session.py:203-208`; `app/backend/api/session.py:392-397` | UI can show connected while live tick/candle stream is dead. |
| MEDIUM | Tick-log warmup is shallow relative to context readiness | `streaming.py:140-145`; `tick_logger.py:48-78`; `market_context.py:327-329` | Reconnect/restart may not warm enough candles for Level 2/3 readiness. |
| LOW | Live candle engine is single-timeframe only | `market_context.py:39-41` | Limits strategy context to 1-minute candles unless extended later. |

### 7.3 Detailed Findings

#### Finding I-1 — HIGH — Historical candle wrapper does not match installed runtime semantics

**Evidence:**

```text
app/backend/session/pocket_option_session.py:298-301
298 |     def get_candles(self, active, timeframe, count):
299 |         if not self.is_connected or self._api is None:
300 |             raise SessionConnectionError("Not connected")
301 |         return self._api.get_candles(active, timeframe, count)
```

Installed runtime evidence:

```text
C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi\stable_api.py:326-408
326 |     def get_candles(self, active, period, start_time=None, count=6000, count_request=3):
...
395 |             if active in global_value.pairs:
396 |                 global_value.pairs[active]['history'] = c1
...
404 |             return True
...
408 |             return False
```

**Explanation:** The v3 wrapper passes `(active, timeframe, count)`, but the installed runtime API interprets the third argument as `start_time`, not `count`. The installed method also mutates `global_value.pairs` and returns `True` / `False`, not candle rows.

**Why it matters:** Any future feature that calls `PocketOptionSession.get_candles(...)` expecting candle arrays will likely behave incorrectly or fail downstream.

**Recommendation:** @Architect should define a narrow candle provider contract first. @Coder should not wire this wrapper into the main runtime until the external provider is validated.

---

#### Finding I-2 — HIGH — Saved SSID endpoint returns authentication secret

**Evidence:**

```text
app/backend/api/session.py:436-448
436 | @router.get("/saved-ssid")
437 | async def saved_ssid(demo: bool = False) -> JSONResponse:
...
447 |             "ssid": saved,
```

```text
app/frontend/src/stores/useAuthStore.js:27-34
27 |       const data = await sessionSavedSsid(demo);
28 |       const savedSsid = typeof data?.ssid === 'string' ? data.ssid : '';
...
31 |         ssidInput: savedSsid,
```

```text
app/frontend/src/components/auth/ConnectDialog.jsx:150-156
150 |                 <textarea
151 |                   value={ssidInput}
...
156 |                 />
```

**Explanation:** The backend returns the full saved SSID and the frontend stores/displays it.

**Why it matters:** The SSID is equivalent to a session authentication secret. Exposure is acceptable only under local-only assumptions and dangerous if the backend is bound beyond localhost or if frontend state is inspected.

**Recommendation:** @Architect should decide whether saved SSID retrieval should return only `has_saved_ssid` and masked metadata. @Coder should remove full-secret echoing before productionizing.

---

#### Finding I-3 — HIGH — Tick hook ImportError is silently swallowed

**Evidence:**

```text
app/backend/session/pocket_option_session.py:44-89
44 |     def _apply_hooks(cls):
...
47 |             import pocketoptionapi.global_value as gv
...
86 |                 gv.set_csv = hooked_set_csv
87 |                 logging.getLogger("PocketOptionSession").info("Broker tick hooks applied successfully.")
88 |         except ImportError:
89 |             pass
```

**Explanation:** If `pocketoptionapi.global_value` cannot import, hook installation fails without log, exception, status flag, or user-visible error.

**Why it matters:** The entire live tick → candle → OTEO pipeline depends on this hook. Failure here means no live candles, no market context, and no signals.

**Required Core Principle #8 note:**

> “This catch block swallows the error and will cause silent failures in production. Must either log + re-throw, return a proper error response, or show a user-friendly message.”

**Recommendation:** @Coder should replace the silent pass with explicit logging and a status surface. @Reviewer should phase-gate this because it touches the core tick path.

---

#### Finding I-4 — MEDIUM — Backend auto-connect exists but frontend does not expose it

**Evidence:**

```text
app/backend/api/session.py:292-310
292 | @router.post("/auto-connect")
293 | async def auto_connect_session(request: Request, demo: bool = False) -> JSONResponse:
294 |     """
295 |     Auto-connect to Pocket Option by extracting the live SSID from Chrome via CDP.
```

```text
app/frontend/src/api/opsApi.js:24-31
24 | export const sessionConnect = (ssid, demo) =>
25 |   request('POST', '/session/connect', { ssid, demo });
...
31 | export const sessionClearSsid = (demo) => request('POST', '/session/clear-ssid', { demo });
```

```text
app/frontend/src/components/auth/ConnectDialog.jsx:194-196
194 |               <p className="text-[10px] text-slate-400 text-center">
195 |                 Get the SSID from Chrome DevTools → Network → WS tab after logging into Pocket Option.
196 |               </p>
```

**Explanation:** The backend has a CDP extractor, but the UI remains manual-first.

**Why it matters:** The user experience and actual backend capability are misaligned.

**Recommendation:** @UI-Designer should design a non-generic, clear local-only auto-connect UX. @Coder should only wire it after security boundaries are confirmed.

---

#### Finding I-5 — MEDIUM — Streaming startup failure after session connect is treated as non-fatal

**Evidence:**

```text
app/backend/api/session.py:203-208
203 |     try:
204 |         streaming_service = request.app.state.streaming_service
205 |         PocketOptionSession.set_tick_callback(streaming_service.process_tick)
206 |         streaming_service.start()
207 |     except Exception as stream_exc:
208 |         logger.warning("Stream start after connect failed (non-fatal): %s", stream_exc)
```

```text
app/backend/api/session.py:392-397
392 |     try:
393 |         streaming_service = request.app.state.streaming_service
394 |         PocketOptionSession.set_tick_callback(streaming_service.process_tick)
395 |         streaming_service.start()
396 |     except Exception as stream_exc:
397 |         logger.warning("Stream start after auto-connect failed (non-fatal): %s", stream_exc)
```

**Explanation:** Authentication can succeed while streaming fails.

**Why it matters:** The app can report session connected while candle production is not running.

**Recommendation:** @Architect should define two explicit statuses: `session.connected` and `streaming.active`. @Coder should propagate streaming startup failure to the response or status endpoint.

---

#### Finding I-6 — MEDIUM — Current candle history is live-only and shallow on restart

**Evidence:**

```text
app/backend/services/streaming.py:140-145
140 |             recent_ticks = self.tick_logger.load_recent(asset, max_ticks=300)
141 |             if recent_ticks:
142 |                 for tick in recent_ticks:
143 |                     oteo.seed_tick(float(tick["p"]), timestamp=float(tick["t"]))
144 |                     market_context.seed_tick(float(tick["p"]), timestamp=float(tick["t"]))
145 |                 logger.info("Pre-seeded OTEO for %s with %d historical ticks", asset, len(recent_ticks))
```

```text
app/backend/services/market_context.py:327-329
327 |             self._cached_context = {
328 |                 "ready": len(closed_candles) >= max(self.config.adx_period + 2, self.config.cci_period, self.config.micro_pivot_span * 3 + 2),
329 |                 "candle_count": len(closed_candles),
```

**Explanation:** Seeding 300 raw ticks is not equivalent to deep candle backfill. The context readiness threshold can require roughly 16 closed 1-minute candles.

**Why it matters:** Restart behavior may leave Level 2/3 unavailable longer than expected.

**Recommendation:** External candle development should include deterministic replay/backfill and explicit readiness reporting before integration.

---

### 7.4 Investigator Recommendations

1. **Do not modify the installed broker historical-candle path inside the main app first.** Build externally and test with a fake transport plus recorded broker payloads.
2. **Define a CandleProvider interface** before integration:
   ```python
   class CandleProvider(Protocol):
       async def get_candles(self, asset: str, period: int, count: int, end_time: int | None = None) -> list[CandleDTO]: ...
   ```
3. **Keep live tick-derived candles as the main runtime truth** until broker historical candles are proven correct.
4. **Treat broker historical candles as backfill only**, not as a replacement for the live stream.
5. **Do not expose saved SSIDs to the frontend in full** if this app ever moves beyond a strictly local environment.
6. **Make streaming status explicit** so “connected” never implies “candles are flowing” unless the tick path is confirmed active.

### 7.5 Investigator Risk Forecast

If ignored:

- Future callers may use `PocketOptionSession.get_candles(...)` and receive boolean/global-mutation behavior instead of candle arrays.
- Reconnects may continue to show connected sessions with no live candle production.
- SSID secret exposure can become a serious account/session compromise if network exposure changes.
- Attempts to “fix historical candles” inside the existing runtime may destabilize the already-working tick stream and Auto-Ghost path.

---

## 8. @Reviewer Findings

### 8.1 Strengths

- **Good separation in v3 app:** session API, session manager, broker adapter, streaming service, market context engine, and frontend store responsibilities are mostly separated.
- **Fail-fast SSID validation exists:** malformed SSID frames are rejected before broker connection.
- **Thread dispatch is safer than direct async misuse:** tick callbacks are marshalled into the main event loop with `run_coroutine_threadsafe`.
- **Market context caching is substantially improved:** heavy ADX/CCI/pivot logic is recomputed on cache miss or candle close rather than every tick.
- **Ops endpoints have local-gating:** Chrome lifecycle actions are protected better than general session endpoints.

### 8.2 Issues

| Severity | Review issue | Rationale | Suggested owner |
|---|---|---|---|
| HIGH | Secret handling is too permissive for saved SSID | `/saved-ssid` returns full auth frame | @Architect + @Coder |
| HIGH | Installed vs bundled PocketOptionAPI divergence is a maintainability risk | Developers may inspect bundled files while runtime uses installed files | @Architect |
| HIGH | Silent `ImportError` in tick hook violates explicit error handling | Can kill tick/candle path without visibility | @Coder |
| MEDIUM | Auto-connect backend not reflected in frontend UX | Incomplete integration creates user confusion | @UI-Designer + @Coder |
| MEDIUM | Streaming success is not part of connect success contract | Auth can succeed while tick/candle stream fails | @Architect + @Coder |
| MEDIUM | Broker historical candle path lacks tests in active app | No confidence in return shape, timing, edge cases | @Tester |
| LOW | Single-timeframe candle context limits future strategy evolution | 1-minute only | @Architect |

### 8.3 Reviewer Suggestions

1. **Add a runtime dependency note** documenting that `pocketoptionapi` resolves from `C:\QuFLX\v2\ssid\PocketOptionAPI-v2\pocketoptionapi`, not `ssid_integration_package/pocketoptionapi`.
2. **Create tests before integrating historical candles:**
   - valid candle array shape
   - timestamp spacing
   - missing candles / gaps
   - malformed broker payload
   - timeout behavior
   - expired SSID behavior
3. **Do not let broker backfill mutate live engine state directly.** Convert broker payloads to immutable DTOs first.
4. **Split connection state into clear flags:**
   - Chrome running
   - SSID extracted
   - broker authenticated
   - tick hook installed
   - streaming active
   - first tick received
   - candle engine ready
5. **Add a safe masked-SSID UX:** show `session_id` or masked suffix, not the full auth frame.

---

## 9. Recommendation: Develop Historical Candles Outside This Project First

I recommend developing the historical-candle feature outside the current app first.

### Why external development is safer

1. **The current app’s live tick path is valuable and already integrated.** It powers sparklines, OTEO, Level 2/3 context, Auto-Ghost, and Socket.IO payloads.
2. **Broker historical candle code is not currently in the active v3 path.** This makes it a good candidate for isolated prototyping.
3. **The installed API has global-state side effects.** `global_value.pairs`, `history_new`, `history_data`, and WebSocket flags are shared mutable state.
4. **The installed API does not match the bundled package implementation.** External development lets you pin and inspect the real runtime version without touching v3.
5. **Historical backfill can destabilize live streaming if done incorrectly.** Backfill requests share the same broker WebSocket and can interfere with `change_symbol`, tick messages, or message flags.

### Recommended external module boundaries

Build a standalone package or script with these boundaries:

```text
external_candle_lab/
  candle_provider.py        # clean interface
  pocket_transport.py       # raw broker websocket / package wrapper
  normalizer.py             # broker payload -> CandleDTO
  validator.py              # spacing, OHLC integrity, gaps
  recorder.py               # save raw payloads for replay
  replay_tests.py           # deterministic tests from saved payloads
  README.md                 # exact runtime requirements
```

### Minimum CandleDTO contract

```python
@dataclass(frozen=True)
class CandleDTO:
    asset: str
    period: int
    time: int
    open: float
    high: float
    low: float
    close: float
    source: Literal["broker_history", "tick_replay"]
```

### Validation rules before importing into v3

- `high >= max(open, close, low)`
- `low <= min(open, close, high)`
- timestamps are strictly ascending
- spacing equals requested period, or gaps are explicitly reported
- last incomplete candle is either excluded or flagged
- time zone offsets are proven and documented
- timeout returns structured error, not `[]`, `False`, or silent global mutation
- expired SSID returns explicit auth error
- broker response shape is recorded and replayable

---

## 10. Safe Future Integration Plan

If the external module proves stable, integrate in phases:

### Phase A — Documentation and contract only

- Document installed PocketOptionAPI version/path.
- Define `CandleDTO` and `CandleProvider` contract inside v3.
- Do not call broker history yet.

### Phase B — Read-only diagnostic endpoint

- Add a backend-only endpoint such as:
  ```text
  GET /api/diagnostics/candles?asset=EURUSD_otc&period=60&count=20
  ```
- Return normalized candles and validation status.
- Do not feed results into OTEO/Level2/Level3 yet.

### Phase C — Backfill as optional warmup

- Use broker historical candles only to warm `MarketContextEngine` before live ticks.
- Keep live tick candles authoritative after startup.
- Add explicit readiness states:
  - `history_backfill_ok`
  - `history_backfill_failed`
  - `live_tick_ready`
  - `market_context_ready`

### Phase D — Phase-gated review

- Run @Reviewer after every phase.
- Run @Tester with recorded broker payloads and fake time.
- Run live session validation only after deterministic tests pass.

---

## 11. Decision Matrix

| Option | Benefit | Risk | Recommendation |
|---|---|---|---|
| Keep current v3 live tick candles only | Stable, already integrated | Startup warmup remains limited | Good short-term default |
| Wire `PocketOptionSession.get_candles` directly now | Fastest path | High risk due installed API mismatch | Do **not** do this |
| Patch installed PocketOptionAPI inside current app workflow | Could unlock broker history | Can destabilize auth/ticks/trading | Avoid inside v3 initially |
| Build external candle lab first | Safest learning path | Takes more setup time | **Recommended** |
| Integrate external module through DTO/provider later | Controlled risk | Requires tests and adapter discipline | Recommended after validation |

---

## 12. Final Recommendations

1. **Develop broker historical candle logic outside OTC_SNIPER first.** Your instinct is correct: this feature touches unstable broker/WebSocket/global-state code.
2. **Preserve current v3 candle behavior as the stable runtime path.** It is live tick-derived, integrated, and already used by Level 2/3.
3. **Treat historical candles as optional backfill, not the main source of truth.** Live ticks should remain authoritative after connection.
4. **Do not call `PocketOptionSession.get_candles(...)` from production code until the installed API mismatch is resolved.**
5. **Fix or at least document the silent tick-hook ImportError before relying on candle availability.**
6. **Reduce SSID exposure before productionizing.** Return masked status instead of full saved auth frames.
7. **Expose streaming/candle readiness separately from session connected status.** This will prevent “connected but dead chart” confusion.

---

## 13. Bottom Line

The current v3 SSID integration is usable, but historical candle production is not yet a safe, clean, first-class subsystem. The working app produces candle context from live ticks; the broker historical-candle path exists only as an unused wrapper over a volatile installed API. The safest next move is to prototype broker historical candles externally with strict DTO normalization and replay tests, then integrate later through a narrow read-only provider boundary.
