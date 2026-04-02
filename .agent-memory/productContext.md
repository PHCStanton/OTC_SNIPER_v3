# Product Context

## Summary
- OTC_SNIPER is a modular OTC trading workspace focused on reliable execution, live market visibility, and disciplined risk management for Pocket Option style workflows
- The rebuild separates the planning workspace from the functional application root so trading, streaming, risk, and UI concerns can be maintained and verified independently
- This file captures stable product intent rather than temporary debugging state

## Intended Users
- Professional, discretionary, or algorithmic traders who need fast OTC execution
- Users who depend on realtime session feedback, safer operational controls, and ghost trading support

## Core Functionality
- Submit trades through the Pocket Option backend integration
- Stream realtime data through the broker callback and Socket.IO pipeline
- Track session performance, trade history, win rate, and P/L
- Support ghost trading for safer strategy validation
- Provide AI-assisted journaling and decision support without autonomous execution
- Surface failures clearly so trade rejection, connectivity issues, and runtime errors are visible to the operator

## Success Metrics
- Stable trade execution without freezing the backend event loop
- Reliable realtime delivery for sparklines and trade outcomes
- Clear separation between repository, broker/session logic, services, and React UI
- Explicit fail-fast validation and error reporting throughout the stack
