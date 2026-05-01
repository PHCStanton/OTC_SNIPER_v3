<condense>
<context>
1. Previous Conversation:
The user asked for a thorough code review of two folders in the Pocket Option websocket layer: `pocketoptionapi\ws\objects` and `pocketoptionapi\ws\channels`, and specifically wanted to understand why they appear to serve the same purpose, with special interest in the candle-related files and whether they can retrieve historical candles via the SSID after refactoring.

I inspected the key files in both folders and the main wiring files (`pocketoptionapi/ws/client.py`, `pocketoptionapi/api.py`, and `pocketoptionapi/stable_api.py`). I then produced a detailed reviewer-style assessment explaining that the folders are not duplicates: `channels/` sends outbound websocket commands, while `objects/` is intended for inbound data models/state holders. I highlighted that the actual working historical candle path is `stable_api.get_candles()` -> `api.get_candles_data()` -> `channels/candles.py:GetCandles` -> websocket response handled in `client.py`.

The user then switched the task from review/planning into implementation-oriented work and asked: “Put together a detailed `Refactor_Implementation_Plan_26-03-30.md` so we ca adress these issues and see if we can get the SSID to fuction optimaly”. I created a detailed refactor plan markdown file under `Research/` and saved it as `Research/Refactor_Implementation_Plan_2026-03-30.md`.

2. Current Work:
The last completed action was writing the refactor plan markdown document. It contains a phased plan to clean up the websocket layer and improve SSID candle retrieval reliability. The plan includes:
- Dead code removal (`objects/enhanced_candles.py`, `channels/get_currency_pairs.py`)
- Candle model consolidation into a single dataclass-based file
- Merging duplicate time sync implementations
- Hardening the candle retrieval path with better signaling and validation
- Cleaning up the channel files, especially the buy-related channels
- Refactoring the monolithic websocket client message handler
- Adding tests for candle pipeline and time sync behavior

The content of the plan intentionally emphasized that the SSID candle retrieval is already working via the channel/message pipeline, but the object-side candle classes are broken/dead and should be rewritten or removed rather than incrementally patched.

3. Key Technical Concepts:
- WebSocket request/response architecture
- SSID-authenticated websocket handshake and session persistence
- Candle data retrieval via `loadHistoryPeriod`
- Separation of concerns: command channels vs object models
- Duplicate data representations (`Candle`, `CandleData`, raw dicts)
- Duplicate time synchronization classes (`TimeSync`, `TimeSynchronizer`)
- Busy-wait polling vs event-driven signaling
- Immutable dataclasses for canonical domain models
- Caching via candle collection/store structures
- Incremental refactor/testing strategy
- Python logging and avoidance of silent failures
- Backward compatibility for `stable_api.get_candles()` return format

4. Relevant Files and Code:
- `pocketoptionapi/ws/channels/candles.py`
  - Contains `GetCandles`, which sends the actual websocket command:
    - message type: `['loadHistoryPeriod', data]`
    - data includes `asset`, `index`, `offset`, `period`, and `time`
  - This is the core working historical candle retrieval mechanism.

- `pocketoptionapi/ws/objects/candles.py`
  - Contains a `Candle` class and a `Candles` class.
  - `Candles.get_historical_candles()` checks `hasattr(self, 'api')`, but `self.api` is never set, so this path is non-functional.
  - It also tries to update `EnhancedCandles`, but that cache is not used by the active data flow.

- `pocketoptionapi/ws/objects/enhanced_candles.py`
  - Defines `CandleData` and `EnhancedCandles`.
  - Appears to be dead/unused code in the active candle pipeline.
  - Contains cache/update logic but no real integration with the response handler.

- `pocketoptionapi/ws/objects/timesync.py`
  - Defines `TimeSync` with server timestamp and expiration calculations.

- `pocketoptionapi/ws/objects/time_sync.py`
  - Defines `TimeSynchronizer`, a second time-sync abstraction with local timezone compensation and synced datetime calculation.

- `pocketoptionapi/ws/client.py`
  - WebSocket receive loop and `on_message()` handling.
  - Detects asset list messages, trade updates, balance updates, candle-related `loadHistoryPeriod` events, and auth messages.
  - Writes candle payloads into `self.api.history_data` rather than into `objects/candles.py`.

- `pocketoptionapi/api.py`
  - Defines `PocketOptionAPI` and the `get_candles_data()` method.
  - The candle request path ultimately uses `self.getcandles(active, interval, count, end_time)`.
  - The current design instantiates websocket channel classes via `@property`, which can create new objects repeatedly.

- `pocketoptionapi/stable_api.py`
  - Provides higher-level `PocketOption` convenience methods.
  - `get_candles()` calls `api.get_candles_data()` and formats the response into `[time, open, high, low, close]` lists.

- `Research/Refactor_Implementation_Plan_2026-03-30.md`
  - Newly created detailed refactor plan document.
  - Contains phases, risk assessment, file matrix, acceptance criteria, and explicit guidance for candle/SSID improvements.

5. Problem Solving:
I identified that the architecture is split into two conceptual layers:
- `channels/` is the command layer: send websocket requests.
- `objects/` is the state/data-model layer: store and interpret incoming data.

The main confusion is that the candle-related object files were trying to act like both a model and a data-fetch service, but the active pipeline does not use them. The actual historical candle retrieval path is already working through the `channels/candles.py` request plus `client.py` response handling. That means the safest refactor path is to preserve that working pipeline while deleting or rewriting the broken object-side candle abstractions.

I also discovered two time sync implementations that overlap heavily and should be merged to avoid future drift/duplication bugs. The plan reflects a clean, phased consolidation approach rather than more incremental patches.

6. Pending Tasks and Next Steps:
- The user asked for a detailed refactor implementation plan; that has been completed and saved to `Research/Refactor_Implementation_Plan_2026-03-30.md`.
- The next likely step is for the user to review and approve the plan, then toggle back to ACT mode if they want the implementation work performed.
- Once approved, the implementation should follow the plan’s phases in order, with testing after each phase.

Verbatim recent context showing where we left off:
- User request: “Put together a detailed `Refactor_Implementation_Plan_26-03-30.md` so we ca adress these issues and see if we can get the SSID to fuction optimaly”
- The plan file was written successfully to `Research/Refactor_Implementation_Plan_2026-03-30.md`.

Important note for continuation:
- The file was saved with `2026-03-30` in the filename, not `26-03-30`. If the exact filename matters, that may need to be corrected later.
</context>
<task_progress>
- [x] Review all files in `ws/objects/` and `ws/channels/`
- [x] Analyze overlap and duplication between the two folders
- [x] Deep-dive into candle-related files for historical candle retrieval via SSID
- [x] Deliver comprehensive Reviewer report
- [x] Create detailed Refactor Implementation Plan markdown document
</task_progress>
</condense>