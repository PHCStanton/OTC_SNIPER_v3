# Product Context

## Summary
- OTC_SNIPER is a modular OTC trading workspace focused on reliable execution, live market visibility, and disciplined risk management for Pocket Option style workflows
- The rebuild separates the planning workspace from the functional application root so trading, streaming, risk, and UI concerns can be maintained and verified independently
- This file captures stable product intent rather than temporary debugging state

## Intended Users
- Professional, discretionary, or algorithmic traders who need fast OTC execution
- Users who depend on realtime session feedback, safer operational controls, and Auto-Ghost simulation support for strategy refinement.

## Core Functionality
- Submit trades through the Pocket Option backend integration
- Stream realtime data through the broker callback and Socket.IO pipeline
- Track session performance, trade history, win rate, and P/L
- Support Auto-Ghost simulations for background strategy validation and data-driven OTEO improvement without risking live capital. Includes configurable execution filters (confidence window, manipulation severity, z-score thresholds, regime whitelists) with AI-suggested "smart averages" derived from recent N-trade results + historical KB patterns (calibration phase support).
- Results & Analysis Panel provides regime/z-score optimized filters (5 cutoffs with per-regime win rates) surfaced for manual use and fed into Grok analysis for filter recommendations.
- Provide AI-assisted journaling and decision support without autonomous execution. Native Grok TTS for professional voice playback of reports/scripts (profile-managed voices alongside browser fallback).
- Surface failures clearly so trade rejection, connectivity issues, and runtime errors are visible to the operator

## Success Metrics
- Stable trade execution without freezing the backend event loop
- Reliable realtime delivery for sparklines and trade outcomes
- Clear separation between repository, broker/session logic, services, and React UI
- Explicit fail-fast validation and error reporting throughout the stack
