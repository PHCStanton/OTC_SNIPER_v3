# OTC SNIPER v3 — OTEO Update Plan

**File date:** 2026-03-30  
**Last updated:** 2026-04-04  
**Status:** Quick phase implemented, Ghost backend MVP in progress, Medium phase partially implemented, Advanced planned  
**Scope:** Cleanly evolve OTEO from a tick-only exhaustion engine into a scalable signal stack with better directional logic, lower duplicate noise, user-selectable Level 1 / 2 / 3 profiles, future candle-context integration, Ghost-mode testing support, and optional AI-assisted ranking  
**Current implementation files:**
- `app/backend/services/oteo.py`
- `app/backend/services/streaming.py`
- `app/backend/services/manipulation.py`

---

## 1. Executive Summary

This document tracks the staged upgrade plan for the OTEO indicator so future work can continue with minimal context loss.

The strategy direction is intentionally simple:

- Keep **OTEO core** focused on fast, deterministic tick-based exhaustion logic
- Expose **Quick / Medium / Advanced** as **OTEO Level 1 / Level 2 / Level 3** profiles for user testing
- Build **Ghost Mode** early so the levels can be compared safely before risking live capital
- Add **market context** in later phases instead of overloading the core
- Use **Support / Resistance + ADX** as a filter layer, not as a replacement for OTEO
- Use **AI** only where it adds ranking, calibration, or scheduled regime review

This keeps the design clean, scalable, and easier to test.

---

## 2. Current Completion Status

### 2.1 Overall Phase Status

| Phase | Name | Status | Notes |
|---|---|---|---|
| Quick | Tick-native OTEO cleanup and signal-quality fix | [x] | Implemented in backend |
| Ghost | Ghost-mode backend foundation for safe level testing | [~] | Backend MVP in progress |
| Medium | Candle-context integration with S/R + ADX filter layer | [~] | Backend foundation implemented, tuning and live validation pending |
| Advanced | Regime engine + AI-assisted ranking and scheduled analysis | [ ] | Planned |

### 2.2 Current Task Checklist

- [x] Investigated legacy OTEO weaknesses and repetitive signal behavior
- [x] Reviewed QuFLX indicator reference for S/R and ADX suitability
- [x] Reworked OTEO architecture to support staged growth
- [x] Implemented Quick-phase Gauss-style weighted pressure logic
- [x] Added cleaner directional gating and neutral state handling
- [x] Improved duplicate signal suppression using actionable gating
- [x] Separated historical warmup seeding from live signal mutation
- [x] Extended streaming payload with richer OTEO metadata
- [x] Confirmed backend compile validation
- [x] Approved direction to expose OTEO as Level 1 / Level 2 / Level 3 profiles
- [~] Ghost mode frontend exists, but backend execution path was only partially implemented and is now being upgraded
- [~] Ghost viewer popup exists in frontend, but previous stats were static placeholders and are now being wired to real ghost results
- [~] Manipulation detection path verified in backend/store wiring, but active frontend display still needs runtime/UI verification
- [~] Ghost backend MVP implementation started
- [x] Medium-phase market context service foundation implemented
- [x] Medium-phase micro / macro Support-Resistance integration foundation implemented
- [x] Medium-phase ADX trend-strength filter foundation implemented
- [x] Medium-phase signal policy merge implemented
- [x] Medium-phase frontend toggle and backend runtime sync implemented
- [~] Medium-phase replay validation completed, live runtime validation still needed
- [ ] Medium-phase threshold tuning / optimization
- [ ] Advanced-phase regime classifier
- [ ] Advanced-phase scheduled AI review loop

---

## 3. Why This Update Is Needed

The previous OTEO version was functional but had several quality limitations:

- It used a blunt raw velocity measurement based on start/end movement
- It discarded signed context in the score product
- It could stay “hot” too long and produce repetitive same-direction signals
- Historical pre-seeding could mutate live cooldown state
- It had no clean architecture boundary for future candle-context filters

The update plan addresses these without turning OTEO into a monolithic indicator engine.

---

## 4. Architecture Direction

### 4.1 Target Layering

The long-term design should be:

1. **OTEO Core Layer**
   - Tick-native
   - Fast
   - Deterministic
   - No heavy candle dependencies

2. **Market Context Layer**
   - Candle-derived filters
   - Support / Resistance
   - ADX / directional strength
   - Multi-timeframe structure bias

3. **Signal Policy Layer**
   - Combines OTEO core + market context
   - Applies penalties, boosts, and suppression rules
   - Produces final entry quality state

4. **AI Review Layer**
   - Periodic analysis
   - Ranking and calibration
   - Regime summaries
   - Never replaces deterministic core triggering

### 4.2 Why This Structure Matters

- OTEO stays easy to test and tune
- Candle indicators can evolve independently
- AI can be added later without destabilizing the entry engine
- Support / Resistance and ADX become optional context modules rather than hard-coded clutter inside OTEO

### 4.3 User-Facing OTEO Levels

The rollout should expose staged logic as three user-selectable intensity profiles:

- **Level 1**
  - current Quick-phase OTEO only
  - fast tick-native exhaustion logic
  - weighted pressure
  - neutral gating
  - duplicate suppression

- **Level 2**
  - Level 1 plus market context
  - micro / macro Support-Resistance
  - ADX trend-strength filter
  - location-aware confidence adjustment

- **Level 3**
  - Level 2 plus advanced context
  - regime classification
  - scheduled AI review
  - quality ranking and caution states

These levels must be implemented as **profiles on one architecture**, not as three separate indicator codepaths.

---

## 5. Quick Phase — Implemented

### 5.1 Goal

Improve signal cleanliness and directional correctness without adding candle dependencies or frontend layout changes.

### 5.2 What Was Implemented

- [x] Added a dedicated `OTEOConfig` object for scalable configuration
- [x] Replaced simple raw velocity with weighted pressure logic
- [x] Added `pressure_pct`
- [x] Added neutral-direction gating
- [x] Added actionable signal gating
- [x] Added stretch alignment metric
- [x] Fixed historical warmup seeding so it no longer mutates live signal state
- [x] Reduced duplicate signal spam in streaming/logging

### 5.3 Implemented Files

- `app/backend/services/oteo.py`
- `app/backend/services/streaming.py`

### 5.4 Quick-Phase Logic

The updated Quick-phase engine now uses:

- **Weighted pressure**
  - Recent deltas matter more than older deltas
  - Very cheap to compute
  - Inspired by Gauss-style weighted normalization

- **Signed stretch alignment**
  - Signal strength only grows when pressure and deviation point to a true exhaustion state
  - Prevents scoring contradictory states as equally strong

- **Neutral gating**
  - If pressure and stretch are not meaningfully aligned, OTEO returns `NEUTRAL`
  - This reduces false urgency and repetitive entries

- **Actionable flag**
  - OTEO can remain informative without always being trade-worthy
  - Streaming only logs actionable signals

- **Live-safe warmup seeding**
  - Historical ticks seed buffers only
  - They no longer trigger cooldown or prior synthetic signals

### 5.5 Quick-Phase Outcome

This phase is meant to produce:

- cleaner entries
- more neutral states in noisy zones
- fewer duplicate same-direction bursts
- a better foundation for later S/R and ADX filters

### 5.6 Quick-Phase Status

- [x] Backend logic implemented
- [x] Backend compile validation completed
- [x] Architecture made extensible for later phases
- [~] Runtime trading validation still depends on next live test cycle

---

## 6. Medium Phase — Partially Implemented

### 6.1 Goal

Add a lightweight **market context service** that runs on candle data and improves OTEO confidence by filtering entries according to structure and trend regime.

### 6.2 Main Additions

- [x] 1-minute candle aggregation service foundation
- [x] Context updates during live streaming
- [x] Micro Support / Resistance foundation
- [x] Macro Support / Resistance foundation
- [x] ADX + DI trend strength foundation
- [x] Context payload merged into final signal policy
- [x] Runtime Level 2 enable / disable control
- [ ] CCI confirmation layer
- [ ] Threshold tuning and per-asset calibration

### 6.3 Recommended Design

Create a new backend-side context module with responsibilities such as:

- candle aggregation from live ticks
- rolling OHLC construction
- periodic indicator update
- per-asset context snapshots

Suggested responsibilities:

- `market_context_service.py`
  - build and cache candle context
- `sr_context.py`
  - support / resistance calculations
- `trend_context.py`
  - ADX / DI and trend-strength calculations
- `signal_policy.py`
  - combine OTEO + context into final confidence

### 6.4 Support / Resistance Recommendation

The QuFLX reference confirms strong value in structure-based S/R.

Recommended OTEO use:

- Use **micro S/R** for immediate reaction zones
- Use **macro S/R** for stronger structural boundaries
- Upgrade reversal quality when:
  - CALL is near support
  - PUT is near resistance
- Downgrade entries when price is stretched but far from meaningful structure

### 6.5 ADX Recommendation

ADX should be used as a **trend-strength filter**, not a direct signal source.

Recommended behavior:

- Low / moderate ADX:
  - OTEO reversals are more valid
- High ADX with aligned DI:
  - Reversal entries should be downgraded or suppressed
- Falling ADX after expansion:
  - Reversal setup quality improves

### 6.6 Medium-Phase Signal Policy

A Medium-phase policy should do this:

- OTEO generates raw exhaustion candidate
- S/R checks whether location is meaningful
- ADX checks whether reversal is realistic in the current regime
- Final confidence becomes:
  - boosted
  - unchanged
  - downgraded
  - suppressed

### 6.7 Medium-Phase Status

- [x] Candle context service foundation
- [x] S/R integration foundation
- [x] ADX integration foundation
- [x] Signal policy merge
- [x] Frontend toggle and backend runtime sync
- [x] Backtest / replay validation
- [~] Live ghost validation
- [ ] CCI confirmation
- [ ] Manipulation-aware suppression tuning
- [ ] Expiry-aware tuning
- [ ] Analytics / reporting layer

---

## 7. Ghost Mode Foundation — In Progress

### 7.1 Goal

Create a real backend ghost execution mode so OTEO Level 1 / 2 / 3 can be tested safely and compared before live deployment.

### 7.2 Why Ghost Comes Before Medium and Advanced

Ghost Mode should be built before the Medium and Advanced layers are completed because it becomes the safest test harness for:

- comparing Level 1 vs Level 2 vs Level 3 behavior
- validating S/R and ADX filters
- testing manipulation suppression
- collecting simulated performance without risking live capital

### 7.3 Ghost MVP Requirements

- [x] Frontend ghost toggle already exists
- [x] Ghost banner and draggable ghost GIF widget already exist
- [x] Ghost trade storage paths already exist in backend repository
- [~] Backend ghost execution branch is being added
- [~] Ghost trade results are being emitted through the same Socket.IO result channel
- [~] Ghost widget popup is being wired from static placeholder stats to real ghost result stats
- [ ] Ghost trade history separation / labeling review
- [ ] Runtime validation with live tick stream

### 7.4 Ghost MVP Design

The Ghost MVP should:

- accept a proper backend trade mode
- persist trades as `TradeKind.GHOST`
- use latest known streamed/logged price as entry
- evaluate outcome at expiry using logged market price
- emit result events just like live mode
- keep ghost analytics separate from live session analytics

### 7.5 Ghost MVP Status

- [x] Frontend ghost settings path exists
- [x] Backend ghost data directories exist
- [x] Trade model already supports `TradeKind.GHOST`
- [~] Request/response plumbing being upgraded to support explicit ghost mode
- [~] Backend simulation and payout resolution being added
- [~] Frontend ghost popup stats being switched from hardcoded placeholders to store-driven values
- [ ] Full runtime test

---

## 8. Advanced Phase — Planned

### 8.1 Goal

Add intelligent regime detection and AI-assisted ranking without making the system opaque or overcomplicated.

### 8.2 Main Additions

- [ ] Regime classifier
- [ ] Manipulation-aware state adjustments
- [ ] Multi-timeframe context fusion
- [ ] Scheduled AI analysis hooks
- [ ] Historical calibration and scoring feedback loop

### 8.3 Regime Types to Detect

Suggested regimes:

- trend continuation
- range / mean reversion
- squeeze / compression
- breakout expansion
- high manipulation risk
- post-expansion exhaustion

### 8.4 AI Role

AI should be used for:

- periodic context analysis
- ranking of candidate setups
- explanation summaries
- threshold calibration suggestions
- post-trade pattern discovery

AI should **not** become the raw trade trigger.

### 8.5 Scheduled AI Review

Recommended later settings:

- analysis interval configurable in settings
- AI receives:
  - latest OTEO state
  - candle context snapshot
  - S/R proximity
  - ADX state
  - manipulation flags
  - recent signal history
- AI returns:
  - setup grade
  - regime label
  - caution notes
  - confidence commentary

### 8.6 Advanced-Phase Status

- [ ] Regime engine
- [ ] AI scheduling
- [ ] Signal ranking
- [ ] Calibration loop
- [ ] Historical effectiveness dashboard inputs

---

## 9. Manipulation Detection Status

### 9.1 Current State

Manipulation detection exists in the backend and is already emitted through the stream path.

Verified path:

- backend detection logic exists
- streaming payload includes manipulation flags
- frontend stream hook stores manipulation state

### 9.2 Current Gap

The active trading workspace does not yet clearly surface those flags in the currently used frontend view.

Current status:

- [x] Backend manipulation detector exists
- [x] Backend stream emits manipulation data
- [x] Frontend store receives manipulation data
- [~] Runtime/UI verification for visible display is still needed
- [ ] If required later, add a clean visible alert element to the active workspace

### 9.3 Recommendation

Do not complicate manipulation logic yet.

First:

- verify that the emitted flags are arriving during live runtime
- confirm whether the workspace renders them

Then:

- improve the detector only if the signal path is confirmed active

---

## 10. QuFLX Reference Fit

### 10.1 Relevant QuFLX Components

From the QuFLX indicator reference, the most relevant components for future OTEO evolution are:

- ADX / plus DI / minus DI
- support / resistance structure
- EMA alignment
- ATR-based proximity handling

### 10.2 What Should Be Reused

- [x] General S/R approach as a concept reference
- [x] ADX as trend-strength filter
- [x] ATR-aware distance logic as a quality feature
- [ ] Direct code import into current backend

### 10.3 What Should Not Be Done

- Do not force the full QuFLX candle indicator pipeline into OTEO core
- Do not make tick OTEO dependent on heavy pandas calculations
- Do not let AI replace deterministic entry logic

---

## 11. Validation Strategy

### 11.1 Quick Phase

- [x] Backend compile validation
- [~] Tick replay sanity review
- [ ] Live runtime validation during next session

### 11.2 Ghost Mode

- [~] Backend ghost execution path
- [~] Ghost result event emission
- [~] Ghost widget real stat wiring
- [ ] Runtime ghost trade verification
- [ ] Verify ghost trades do not contaminate live-account metrics

### 11.3 Medium Phase

- [ ] Replay validation with candle context
- [ ] S/R proximity sanity tests
- [ ] ADX threshold verification
- [ ] Signal-count comparison versus Quick phase

### 11.4 Advanced Phase

- [ ] Regime classification validation
- [ ] AI output consistency review
- [ ] Historical quality ranking validation

---

## 12. Recommended Next Implementation Order

### Immediate Next Step

- [~] Complete the Ghost-mode backend MVP
- [x] Expose OTEO Level 1 / Level 2 / Level 3 profile selection cleanly in settings/backend config
- [ ] Continue Medium-phase tuning and deterministic enhancements

### After That

- [x] Build the Medium-phase backend **market context service**
- [x] Add micro and macro S/R context foundation
- [x] Add ADX regime filter foundation
- [x] Merge into signal policy layer
- [~] Validate with stored tick data
- [ ] Validate with live ghost sessions
- [ ] Add CCI confirmation and stronger ATR-driven tuning

### Only After Medium Is Stable

- [ ] Add scheduled AI analysis
- [ ] Add regime classification
- [ ] Add ranking and calibration loop

---

## 13. Current Working Verdict

The OTEO update is now on a better architectural path.

The Quick phase is implemented and already improves signal cleanliness by:

- reducing repeated same-direction noise
- enforcing directional alignment
- producing neutral states where confidence is not justified
- preparing the backend for future context-aware expansion

The next meaningful edge will come from:

1. **Ghost-mode validation harness**
2. **Support / Resistance context**
3. **ADX trend-strength filtering**
4. **scheduled higher-level AI review**

That order is recommended because it preserves clean logic and avoids premature complexity.

---

## 14. Live Context Handoff Checklist

Use this section when resuming work later.

- [x] Quick-phase backend OTEO update has been implemented
- [x] Quick-phase architecture is scalable
- [x] QuFLX S/R + ADX reference has been reviewed
- [x] Support / Resistance + ADX is approved as the Medium-phase direction
- [x] OTEO should be exposed as Level 1 / Level 2 / Level 3 profiles
- [~] Ghost Mode frontend exists but backend execution support is still being finalized
- [~] Ghost widget popup is present and now needs runtime verification with real ghost stats
- [~] Manipulation detection path exists but visible frontend behavior still needs runtime confirmation
- [x] Medium-phase backend context service foundation is built
- [x] Medium-phase Level 2 toggle/runtime sync is implemented
- [~] Medium-phase validation is only partial so far
- [ ] CCI confirmation is not yet implemented
- [ ] Advanced-phase AI review loop not yet built
