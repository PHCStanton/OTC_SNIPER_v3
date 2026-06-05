1. Previous Conversation: The user reported experiencing progressive lag in Trading Sessions — smooth immediately after restart, but deteriorating after 10–15 minutes with delayed clicks, slow streaming visuals, and sluggish loading. Mini sparklines were disabled and gauge-on-hover was set to "only on hover." The user asked for a thorough assessment delegating @Investigator, @Optimizer, @Debugger, and @Code_Simplifier, plus expert recommendations including system-level improvements.

2. Current Work: I performed a full read-only forensic analysis of the OTC_SNIPER v3 codebase (at c:\v3\OTC_SNIPER) following the QuFLX diagnosis skill and investigation-workflow rules. I read all key backend and frontend files — streaming service, market context engine, tick logger, signal logger, manipulation detector, OTEO, socket client, stream connection hook, Zustand stores (stream, risk, toast), plus all trading UI components (Sparkline, MiniSparkline, MultiChartView, TradingWorkspace, RightSidebar, SessionRiskPanel, JournalView, App.jsx). I also read the Socket.IO event pipeline in main.py, the tick dispatch hook in pocket_option_session.py, and the broker adapter. I produced a detailed plan-mode report with findings from all four specialists. The work is complete and waiting for user approval to switch to

   Act Mode (⌘⇧A).

3. Key Technical Concepts:

- OTC_SNIPER v3 stack: FastAPI + async Socket.IO streaming, Python asyncio backend, React + Zustand + Tailwind frontend
- Tick flow: Broker thread → monkey-patched hook → asyncio.run_coroutine_threadsafe(process_tick()) → tick logger (JSONL per-tick aiofiles append) → OTEO/MarketContext/Manipulation enrichment → Level 2/3 policy → Auto-Ghost → Socket.IO emit to per-asset Socket.IO rooms
- Frontend flow: Socket.IO client → useStreamConnection.js RAF-batched updates → useStreamStore Zustand (ticks, signals, manipulation) → component subscriptions (Sparkline SVG, MultiChartView mini cards, OTEORing, etc.)
- Main lag suspects identified: tick dispatch has no backpressure/coalescing; tick logging is sequential await blocking UI emit; mini-chart cards subscribe to full tick arrays and compute series even when sparklines disabled; gauge-on-hover is CSS-only (DOM still rendered); ghost trade/trade marker/toast arrays unbounded; broad Zustand selectors cause unnecessary rerenders; session state summaries remap all historical trades per update
- The project is in PLAN MODE; no code was written or commands executed

4. Relevant Files and Code:

- __app/backend/session/pocket_option_session.py:70-78__: `asyncio.run_coroutine_threadsafe(cls._tick_callback(asset, price, ts), loop)` — unbounded tick dispatch into event loop
- __app/backend/services/streaming.py:268-273, 308-310__: tick JSONL write BEFORE Socket.IO emit — disk blocks UI
- __app/backend/services/tick_logger.py:45-46__: per-tick aiofiles open/write/close — no batching
- __app/frontend/src/components/trading/MultiChartView.jsx:49-58__: each mini-card subscribes to full tick array and computes series even without sparklines
- __app/frontend/src/components/trading/MultiChartView.jsx:84-86__: gauge-on-hover is CSS opacity, gauge still in DOM
- __app/frontend/src/hooks/useStreamConnection.js:59-90__: RAF-batched updates copy full tick arrays per frame
- __app/frontend/src/stores/useRiskStore.js:392-395__: `summarizeGhostTrades([...state.ghostTrades, nextTrade])` — full remap on each ghost trade
- __app/frontend/src/stores/useToastStore.js__: no hard cap on toast queue
- __app/frontend/src/stores/useStreamStore.js:83-90__: trade markers grow unbounded, removeExpiredMarkers never called by UI
- __app/frontend/src/components/layout/RightSidebar.jsx:20-21__: broad `useRiskStore()` selector
- __app/frontend/src/App.jsx:116-187__: per-trade-result state updates through risk store, stream store, toast store

5. Problem Solving: Root cause identified as a producer-faster-than-consumer pattern. Restart helps because StreamingService.stop() clears all engine maps/caches and frontend resetAll() clears arrays. After 10–15 min, three compounded factors cause visible lag: a) Backend async backlog grows (no bounded queue/drop policy for tick dispatch) b) Per-tick synchronous-ish disk I/O delays event loop c) Frontend render pressure accumulates (hidden mini-card work + growing arrays + broad store subscriptions)

This is not purely hardware limits — the architecture lacks backpressure, batching, and selective rendering safeguards.

6. Pending Tasks and Next Steps: The task is in PLAN MODE and awaiting user approval to switch toAct Mode (⌘⇧A). The proposed implementation plan has 4 phases:

- __Phase 0__: Add lightweight performance telemetry (event-loop lag, tick processing duration p50/p95, queue length, emit rate, dropped UI tick count)
- __Phase 1__: Backend hot-path hardening — bounded tick queue/consumer with coalescing/drop policy, buffered tick writer, emit before disk logging
- __Phase 2__: Frontend stream-store split — latest-by-asset state separate from chart series, mini cards use latest-only unless sparklines enabled, throttled chart updates (10-15 FPS selected, 2-4 FPS mini), lazy gauge render on actual hover
- __Phase 3__: Bound session growth — cap trade markers per asset and auto-expire, incremental ghost trade summary, cap toast queue
- __Phase 4__: Selector cleanup — narrow Zustand selectors, memoize only where useful

Plus operational recommendations: run backend without --reload, use production frontend build for serious sessions, keep watched assets minimal, restart cadence workaround every 10-20 min until fixed.
