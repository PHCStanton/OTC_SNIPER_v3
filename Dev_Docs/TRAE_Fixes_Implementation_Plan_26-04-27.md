# OTC SNIPER v3 — TRAE Session Fixes Implementation Plan

**Date:** 2026-04-27  
**Status:** Plan — Awaiting explicit approval before implementation  
**Source:** [Expert Review](file:///C:/Users/piete/.gemini/antigravity/brain/9cddf6c4-9644-4d49-a7ee-5a1c0623d20b/expert_review_TRAE_report.md) of [TRAE Executive Report](file:///c:/v3/OTC_SNIPER/@reports/exuctive_report_TRAE_modifications_26-04-27.md)  
**Compiled by:** @Reviewer + @Backend-Specialist + @Frontend-Specialist + @Optimizer + @Code_Simplifier  
**CORE_PRINCIPLES:** All changes must comply with `.agents/CORE_PRINCIPLES.md`

---

## 1. Executive Summary

The expert review of the TRAE modifications session validated the report's core findings and uncovered **1 critical bug the report missed**, plus **2 moderate issues** and **3 low-priority cleanups**. This plan organizes all remediation into 4 phases by priority.

**Total scope:** 5 files modified, 0 new files. ~60 lines of changes.

---

## 2. Issue Tracker

| # | Severity | Issue | File(s) | Source |
|---|----------|-------|---------|--------|
| 1 | 🔴 CRITICAL | `auto_connect_session` missing `request: Request` param — NameError at runtime | `session.py` | Expert review (missed by report) |
| 2 | 🟠 HIGH | Frontend sends numeric `confidence`, backend expects `str` — 422 rejection | `requests.py`, `useTradingStore.js` | Report §3.1 |
| 3 | 🟠 HIGH | Ghost vs Live confidence semantic drift breaks journal consistency | `useStreamConnection.js`, `useTradingStore.js` | Report §3.2 |
| 4 | 🟡 MODERATE | `httpClient.js` can't parse FastAPI 422 `detail` arrays — shows `[object Object]` | `httpClient.js` | Expert review |
| 5 | 🟡 MODERATE | `demo: false` hardcoded in manual trade path — ignores actual session type | `useTradingStore.js` | Expert review |
| 6 | 🔵 LOW | Signal object has duplicate fields (`score`/`oteo_score`, `marketContext`/`market_context`) | `useStreamConnection.js` | Expert review (@Code_Simplifier) |
| 7 | 🔵 LOW | `normalizeConfidence` does too many things — hard to reason about | `useStreamConnection.js` | Expert review (@Code_Simplifier) |
| 8 | 🔵 LOW | `_resolve_asset_payout_pct` called on every actionable tick — no caching | `streaming.py` | Expert review (@Optimizer) |

---

## 3. Implementation Phases

### Phase A: Critical Runtime Fix (P0)

**Priority:** CRITICAL — Must fix before next session  
**Addresses:** Issue #1  
**Estimated complexity:** 1 line  
**Owner:** @Backend-Specialist

#### A.1 — Add `request: Request` parameter to `auto_connect_session`

**File:** [session.py](file:///c:/v3/OTC_SNIPER/app/backend/api/session.py)

**Problem:** Line 293 defines `async def auto_connect_session(demo: bool = False)` but line 393 references `request.app.state.streaming_service`. This causes a `NameError` at runtime, meaning the streaming reconnect fix from the TRAE session is **broken on the auto-connect path**.

**Fix:**
```diff
-async def auto_connect_session(demo: bool = False) -> JSONResponse:
+async def auto_connect_session(request: Request, demo: bool = False) -> JSONResponse:
```

**Core Principle:** #3 (Incremental Testing) — this was not tested after being added.

---

### Phase B: Confidence Contract Alignment (P1)

**Priority:** HIGH — Resolves the manual trade execution blocker  
**Addresses:** Issues #2, #3  
**Estimated complexity:** ~25 lines across 2 files  
**Owner:** @Backend-Specialist + @Frontend-Specialist

#### B.1 — Accept both `str` and numeric `confidence` in backend

**File:** [requests.py](file:///c:/v3/OTC_SNIPER/app/backend/models/requests.py)

**Problem:** `confidence: str | None = None` rejects numeric values (or coerces `65` → `"65"`, breaking journal consistency with ghost trades that store `"HIGH"`/`"MEDIUM"`/`"LOW"`).

**Fix:** Use a Pydantic validator to accept either type and normalize to categorical string:

```python
from pydantic import field_validator

class TradeExecutionRequest(BaseModel):
    # ... existing fields ...
    confidence: str | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip().upper() if v.strip() else None
        # Numeric → categorical mapping (matches OTEO thresholds)
        numeric = float(v)
        if numeric > 75:
            return "HIGH"
        if numeric > 55:
            return "MEDIUM"
        return "LOW"
```

**Rationale:** This approach is backward-compatible — ghost trades still send categorical strings, and manual trades that send numerics get correctly mapped. Both paths now store consistent categorical values.

#### B.2 — Add transport-ready `confidence` field to trade payload

**File:** [useTradingStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useTradingStore.js)

**Problem:** `normalizeSignalSnapshot` converts confidence to a number on line 21. This numeric value is then sent as `confidence` in the trade request on line 117.

**Fix:** Keep the numeric `confidence` for UI display but send `confidence_label` (the raw categorical string from the backend) as the transport value:

```diff
 function normalizeSignalSnapshot(signal = {}) {
   const oteoScore = Number(signal.oteo_score ?? signal.score ?? 0);

   return {
     // ... existing fields ...
     confidence: Number(signal.confidence ?? 0),
+    confidence_label: signal.confidence_label ?? signal.raw_confidence ?? null,
     // ... rest of fields ...
   };
 }
```

And in the trade execution payload:
```diff
         confidence: normalizedSignal.confidence,
+        // Send categorical label for backend compatibility
+        confidence: normalizedSignal.confidence_label || String(normalizedSignal.confidence),
```

**Alternative (simpler):** Since the backend validator in B.1 now handles numeric→categorical conversion, we can simply keep sending the numeric value and let the backend normalize it. This is the recommended approach — **B.1 alone is sufficient**. B.2 becomes optional cleanup.

#### B.3 — Preserve raw confidence label in stream signal

**File:** [useStreamConnection.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js)

Add the raw categorical confidence to the signal object so it's available if needed:

```diff
       const signal = {
         direction: normalizedDirection,
         confidence,
+        raw_confidence: payload.confidence,  // preserve categorical label
         price,
```

**This gives us a clean separation:** `confidence` (numeric, for UI gauges) vs `raw_confidence` (categorical string, for transport).

---

### Phase C: Error Handling Improvements (P2)

**Priority:** MODERATE — Improves UX and debugging  
**Addresses:** Issues #4, #5  
**Estimated complexity:** ~20 lines across 2 files  
**Owner:** @Frontend-Specialist

#### C.1 — Parse FastAPI 422 validation errors in httpClient

**File:** [httpClient.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/api/httpClient.js)

**Problem:** FastAPI 422 responses return `{ detail: [{ loc: [...], msg: "...", type: "..." }] }`. The current handler does `data.detail || data.message` — when `detail` is an array, this produces `[object Object]` in the error message.

**Fix:**
```diff
   if (!res.ok) {
-    const msg = data.detail || data.message || `HTTP ${res.status}`;
+    let msg;
+    if (Array.isArray(data.detail)) {
+      // FastAPI validation errors — extract human-readable messages
+      msg = data.detail.map(e => {
+        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : 'field';
+        return `${field}: ${e.msg}`;
+      }).join('; ');
+    } else {
+      msg = data.detail || data.message || `HTTP ${res.status}`;
+    }
     throw new Error(msg);
   }
```

**Core Principle:** #8 (Defensive Error Handling) — errors must produce actionable messages.

#### C.2 — Inherit `demo` flag from session state

**File:** [useTradingStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useTradingStore.js)

**Problem:** Line 114 hardcodes `demo: false`. If the user is on a demo account, trades are logged as non-demo.

**Fix:**
```diff
-        demo: false,
+        demo: useOpsStore.getState().accountType === 'demo',
```

`useOpsStore` is already imported on line 7.

---

### Phase D: Signal Cleanup (P3)

**Priority:** LOW — Code quality and maintainability  
**Addresses:** Issues #6, #7, #8  
**Estimated complexity:** ~15 lines  
**Owner:** @Code_Simplifier + @Optimizer

#### D.1 — Deduplicate signal object fields

**File:** [useStreamConnection.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js)

Remove duplicate fields from the signal object:

| Remove | Keep | Reason |
|--------|------|--------|
| `score` (line 95) | `oteo_score` (line 96) | `score` is legacy; all consumers should use `oteo_score` |
| `label` (line 97) | `recommended` (line 98) | `label` is unused outside this object |
| `marketContext` (line 114) | `market_context` (line 113) | camelCase alias is redundant |

**Risk:** Requires checking all consumers of these fields. The `OTEORing.jsx` uses `signal.marketContext` (line 37-38), so this reference must be updated to `signal.market_context` or keep the alias temporarily.

**Action:** Search for all usages of `signal.score`, `signal.label`, and `signal.marketContext` before removing. Update consumers if found.

#### D.2 — Add JSDoc to `normalizeConfidence`

**File:** [useStreamConnection.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js)

Rather than splitting the function (which would add complexity), add clear documentation:

```javascript
/**
 * Normalize confidence to a 0–100 numeric value for UI gauges.
 * 
 * Accepts:
 *  - Numeric (0-1 → scaled to 0-100, 1-100 → used directly)
 *  - Categorical string ("HIGH" → 85, "MEDIUM" → 65, "LOW" → 40)
 *  - Falls back to OTEO score if confidence is unavailable
 * 
 * @param {string|number} payloadConfidence - Raw confidence from backend
 * @param {number} score - OTEO score fallback
 * @returns {number} Normalized 0–100 confidence value
 */
```

#### D.3 — Cache payout resolution with TTL

**File:** [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py)

**Problem:** `_resolve_asset_payout_pct` is called on every actionable signal tick. If `get_payout` involves broker IO, this adds latency to the hot path.

**Fix:** Add a simple time-based cache:

```python
# In __init__:
self._payout_cache: dict[str, tuple[float, float]] = {}  # asset -> (payout, timestamp)
PAYOUT_CACHE_TTL = 60.0  # seconds

def _resolve_asset_payout_pct(self, asset: str) -> float:
    cached = self._payout_cache.get(asset)
    now = time.time()
    if cached and (now - cached[1]) < self.PAYOUT_CACHE_TTL:
        return cached[0]
    
    # ... existing resolution logic ...
    
    self._payout_cache[asset] = (payout, now)
    return payout
```

---

## 4. Files Changed Summary

| File | Phase | Change |
|------|-------|--------|
| [session.py](file:///c:/v3/OTC_SNIPER/app/backend/api/session.py) | A | Add `request: Request` param to `auto_connect_session` |
| [requests.py](file:///c:/v3/OTC_SNIPER/app/backend/models/requests.py) | B | Add `field_validator` for confidence normalization |
| [useTradingStore.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/stores/useTradingStore.js) | B, C | Optional `confidence_label` field; fix `demo` flag |
| [useStreamConnection.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/hooks/useStreamConnection.js) | B, D | Add `raw_confidence`; deduplicate signal fields; document `normalizeConfidence` |
| [httpClient.js](file:///c:/v3/OTC_SNIPER/app/frontend/src/api/httpClient.js) | C | Parse FastAPI 422 `detail` arrays |
| [streaming.py](file:///c:/v3/OTC_SNIPER/app/backend/services/streaming.py) | D | Cache payout resolution with TTL |

**Total: 6 files modified, 0 new files**

---

## 5. Files Explicitly NOT Touched

| File | Reason |
|------|--------|
| `services/oteo.py` | OTEO core is stable — no changes needed |
| `services/trade_service.py` | Trade execution logic is correct |
| `services/market_context.py` | Level 2 policy is stable |
| `services/manipulation.py` | Manipulation detector is hardened |
| `components/trading/TradePanel.jsx` | Renders from store — no direct changes needed |
| `components/trading/OTEORing.jsx` | May need `marketContext` → `market_context` ref update in Phase D only |

---

## 6. Implementation Order & Dependencies

```
Phase A (P0 — Critical Runtime Fix)
  └── A.1: Fix auto_connect_session signature
       ↓
Phase B (P1 — Confidence Contract)
  ├── B.1: Backend validator (standalone, no deps)
  ├── B.2: Frontend transport field (optional, depends on B.1 decision)
  └── B.3: Preserve raw confidence in stream signal
       ↓
Phase C (P2 — Error Handling)
  ├── C.1: httpClient 422 parsing (standalone)
  └── C.2: demo flag inheritance (standalone)
       ↓
Phase D (P3 — Cleanup)
  ├── D.1: Deduplicate signal fields (requires consumer audit)
  ├── D.2: Document normalizeConfidence (standalone)
  └── D.3: Cache payout resolution (standalone)
```

---

## 7. Verification Checklist

### Phase A Verification
- [ ] Start backend, trigger auto-connect — confirm no `NameError`
- [ ] Verify streaming resumes after auto-connect (ticks flow in frontend)

### Phase B Verification
- [ ] Manual trade with numeric confidence → backend accepts (no 422)
- [ ] Check stored trade record has categorical confidence ("HIGH"/"MEDIUM"/"LOW")
- [ ] Ghost trade confidence format matches manual trade format in journal
- [ ] End-to-end manual trade reaches broker layer and returns result

### Phase C Verification
- [ ] Trigger a 422 error → UI shows readable field-level message (e.g. "confidence: str type expected")
- [ ] Execute manual trade on demo account → trade record has `demo: true`
- [ ] Execute manual trade on live account → trade record has `demo: false`

### Phase D Verification
- [ ] Remove `score` field → no console errors, OTEORing still works
- [ ] Remove `marketContext` alias → update `OTEORing.jsx` reference → no breakage
- [ ] Payout resolution shows cache hits in logs under repeated actionable signals

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Phase A breaks auto-connect flow | Very Low | HIGH | Single-line change; well-understood FastAPI pattern |
| Backend validator rejects valid confidence values | Low | MEDIUM | Validator handles str, int, float, None — all known input types |
| httpClient change breaks other error paths | Low | MEDIUM | Only changes behavior for array-typed `detail` — all other paths unchanged |
| Signal field removal breaks unknown consumer | Medium | LOW | Audit all imports of `useStreamStore` before removing |
| Payout cache serves stale data | Low | LOW | 60s TTL is short; payout changes are infrequent |

---

## 9. CORE_PRINCIPLES Alignment

| Principle | How This Plan Adheres |
|-----------|----------------------|
| **#1 Functional Simplicity** | ~60 lines total. No new files. No new abstractions. |
| **#2 Sequential Logic** | Phases A→D in strict priority/dependency order |
| **#3 Incremental Testing** | Each phase has explicit verification criteria |
| **#4 Zero Assumptions** | Validator explicitly handles all known input types |
| **#5 Code Integrity** | Backend validator is backward-compatible; no breaking changes |
| **#6 Separation of Concerns** | Display confidence (numeric) separated from transport confidence (categorical) |
| **#8 Defensive Error Handling** | 422 errors now produce actionable messages |
| **#9 Fail Fast** | Validator normalizes at API boundary; invalid inputs caught early |

---

## 10. Phase Gate Protocol

| Phase | Reviewer Gate | Status |
|-------|--------------|--------|
| Phase A | @Reviewer verifies session.py fix + auto-connect test | [ ] Pending |
| Phase B | @Reviewer verifies requests.py validator + E2E manual trade | [ ] Pending |
| Phase C | @Reviewer verifies httpClient.js + demo flag | [ ] Pending |
| Phase D | @Code_Simplifier + @Optimizer verify cleanups | [ ] Pending |
| **Final** | @Tester runs full E2E: connect → stream → manual trade → result | [ ] Pending |
