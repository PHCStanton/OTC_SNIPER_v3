# Phase 8 — AI Integration Details

**Date:** 2026-03-30  
**Status:** Planned — Awaiting approval before implementation  
**Compiled by:** @Researcher, @Architect, @Engineer, @Reviewer  
**Reference:** `Dev_Docs/OTC_SNIPER_v3_Implementation_Plan_26-03-24.md` Phase 8

---

## 1. Executive Summary

Phase 8 adds advisory-only AI intelligence to OTC SNIPER v3 using the xAI Grok API. The integration includes text chat, image/screenshot analysis for historical chart context, and a dedicated AI tab in the RightSidebar. The architecture is provider-agnostic (xAI today, swappable to OpenAI/Anthropic later), stateless on the backend, and designed to never interfere with core trading functionality.

---

## 2. xAI / Grok API Research

### 2.1 API Compatibility

The xAI API is **OpenAI-compatible**, meaning it uses the same request/response format as the OpenAI Responses API. This allows us to use a thin HTTP client (`httpx`) instead of installing a heavy SDK.

- **Base URL:** `https://api.x.ai/v1`
- **Auth Header:** `Authorization: Bearer <GROK_API_KEY>`
- **Endpoint:** `POST /v1/responses`

### 2.2 Model Selection

| Model | Capabilities | Input Cost (per M tokens) | Output Cost (per M tokens) | Context Window | Vision |
|-------|-------------|--------------------------|---------------------------|----------------|--------|
| `grok-4-1-fast-non-reasoning` | Text + Vision + Functions + Structured | $0.20 | $0.50 | 2,000,000 | ✅ |
| `grok-4-1-fast-reasoning` | Text + Vision + Functions + Structured + Reasoning | $0.20 | $0.50 | 2,000,000 | ✅ |
| `grok-4` | Text + Vision + Functions + Structured | $2.00 | $6.00 | 2,000,000 | ✅ |

**Default model:** `grok-4-1-fast-non-reasoning`  
**Rationale:** 10x cheaper than grok-4, supports vision, fast response times. Suitable for real-time trading advisory. User can upgrade to reasoning or full grok-4 via App Settings.

### 2.3 Image Understanding API Format

```json
{
  "model": "grok-4-1-fast-non-reasoning",
  "input": [
    {
      "role": "system",
      "content": "You are a trading analysis assistant..."
    },
    {
      "role": "user",
      "content": [
        {
          "type": "input_image",
          "image_url": "data:image/png;base64,<base64_string>",
          "detail": "high"
        },
        {
          "type": "input_text",
          "text": "Analyze this chart screenshot for patterns and key levels."
        }
      ]
    }
  ]
}
```

### 2.4 Image Constraints

| Constraint | Value |
|-----------|-------|
| Max image size | 20 MB |
| Supported formats | JPEG, PNG |
| Max images per request | No hard limit |
| Server-side storage | **Not recommended** — xAI advises against storing request/response history with images |

### 2.5 Authentication

The API key is stored in `app/.env` as `GROK_API_KEY`. The backend reads it via `config.py` and uses it exclusively server-side. The key is **never** exposed to the frontend.

---

## 3. Architecture Design

### 3.1 Design Principles

1. **Provider-agnostic service layer** — The backend AI service wraps a generic interface. Today it's xAI/Grok; tomorrow it could be OpenAI, Anthropic, or a local model. The frontend never knows which provider is behind the curtain.
2. **Stateless request/response** — Each AI call is independent. No server-side conversation history (aligns with xAI's image recommendation and keeps memory footprint zero).
3. **Frontend owns conversation state** — The chat history lives in a Zustand store (`useAIStore`). The backend is a pure proxy/formatter.
4. **Advisory-only** — AI responses are displayed in the UI. They never trigger trades, modify risk settings, or override validation. This is a non-negotiable constraint from the architecture doc.
5. **Graceful degradation** — If the API key is missing or the service is down, the AI tab shows a clear disabled state. Core trading is never affected.

### 3.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                              │
│                                                          │
│  ┌──────────┐   ┌───────────┐   ┌────────────────────┐  │
│  │ AITab    │──▶│ useAIStore │──▶│ aiApi.js           │  │
│  │ (Right   │   │ (messages, │   │ POST /api/ai/chat  │  │
│  │ Sidebar) │   │  loading,  │   │ POST /api/ai/      │  │
│  │          │   │  images)   │   │      analyze-image  │  │
│  └──────────┘   └───────────┘   │ GET  /api/ai/status │  │
│                                  └─────────┬──────────┘  │
│                                            │             │
└────────────────────────────────────────────┼─────────────┘
                                             │ HTTP
┌────────────────────────────────────────────┼─────────────┐
│                    BACKEND                  │             │
│                                            ▼             │
│  ┌─────────────┐   ┌──────────────────────────────────┐  │
│  │ api/ai.py   │──▶│ services/ai_service.py           │  │
│  │ (FastAPI    │   │                                   │  │
│  │  router)    │   │  ┌─────────────────────────────┐  │  │
│  │             │   │  │ providers/xai_provider.py   │  │  │
│  │ /api/ai/*   │   │  │ (httpx client → x.ai API)  │  │  │
│  └─────────────┘   │  └─────────────────────────────┘  │  │
│                     │                                   │  │
│                     │  Future: openai_provider.py       │  │
│                     │  Future: anthropic_provider.py    │  │
│                     └──────────────────────────────────┘  │
│                                                          │
│  config.py ← GROK_API_KEY, AI_MODEL, AI_ENABLED         │
└──────────────────────────────────────────────────────────┘
```

### 3.3 RightSidebar Tab Strategy

Instead of replacing the existing Session Risk content, **add a tab system to the RightSidebar**:

| Tab | Content | Source |
|-----|---------|--------|
| **Risk** | Current session risk pulse (existing) | `useRiskStore`, `useOpsStore` |
| **AI** | Chat interface with image upload | `useAIStore`, `aiApi.js` |

This keeps the risk pulse always one click away while giving AI its own dedicated surface.

### 3.4 Data Flow

```
User types message or drops screenshot
  → useAIStore.sendMessage(text, image?)
    → aiApi.chat({ messages, context? }) or aiApi.analyzeImage({ image_base64, prompt })
      → POST /api/ai/chat or /api/ai/analyze-image
        → ai_service.py formats request with system prompt + trading context
          → xai_provider.py sends to https://api.x.ai/v1/responses
            → Response returned
          → ai_service.py validates and extracts response text
        → FastAPI returns { response, model, usage }
      → aiApi returns data
    → useAIStore appends assistant message
  → AITab re-renders with new message
```

---

## 4. Implementation Plan

### 4.1 New Files

#### Backend (5 files)

| # | File | Purpose |
|---|------|---------|
| 1 | `app/backend/services/ai_providers/__init__.py` | Provider registry and base interface |
| 2 | `app/backend/services/ai_providers/xai_provider.py` | xAI/Grok HTTP client using `httpx` |
| 3 | `app/backend/services/ai_service.py` | Provider-agnostic AI service with prompt formatting, image handling, error boundaries |
| 4 | `app/backend/api/ai.py` | FastAPI router: `/api/ai/chat`, `/api/ai/analyze-image`, `/api/ai/status` |
| 5 | `app/backend/models/ai_models.py` | Request/response Pydantic models for AI endpoints |

#### Frontend (3 files)

| # | File | Purpose |
|---|------|---------|
| 6 | `app/frontend/src/api/aiApi.js` | HTTP client for AI endpoints |
| 7 | `app/frontend/src/stores/useAIStore.js` | Zustand store for messages, loading state, image queue |
| 8 | `app/frontend/src/components/ai/AITab.jsx` | Chat UI with image upload, message history, and input |

#### Documentation (1 file)

| # | File | Purpose |
|---|------|---------|
| 9 | `Research/research_xai_grok_api_2026-03-30.md` | xAI API research paper (this document serves as the reference) |

### 4.2 Files to Modify

| File | Change |
|------|--------|
| `app/backend/config.py` | Add `grok_api_key`, `ai_model`, `ai_enabled` fields to `RuntimeSettings` |
| `app/backend/main.py` | Register `ai_router` with `fastapi_app.include_router(ai_router)` |
| `app/frontend/src/components/layout/RightSidebar.jsx` | Add Risk/AI tab toggle, render AITab when AI tab is selected |
| `app/frontend/src/stores/useSettingsStore.js` | Add `aiModel` setting with default value |

### 4.3 Implementation Steps

| Step | Sub-Phase | What | Files |
|------|-----------|------|-------|
| 1 | **8.1** | Backend config + AI provider interface | `config.py` (modify), `ai_providers/__init__.py`, `xai_provider.py` |
| 2 | **8.2** | AI service layer + models | `ai_service.py`, `ai_models.py` |
| 3 | **8.3** | AI API router + wire into main.py | `api/ai.py`, `main.py` (modify) |
| 4 | **8.4** | Frontend API client + store | `aiApi.js`, `useAIStore.js` |
| 5 | **8.5** | AI Tab component | `components/ai/AITab.jsx` |
| 6 | **8.6** | RightSidebar tab system | `RightSidebar.jsx` (modify) |
| 7 | **8.7** | Settings integration (model selector) | `useSettingsStore.js` (modify) |
| 8 | **8.8** | Build verification + endpoint test | Production build + Swagger test |

### 4.4 Backend Endpoints

```
GET  /api/ai/status
  → Response: { enabled: bool, model: str, provider: str, has_api_key: bool }
  → Purpose: Frontend checks if AI is available before showing the tab

POST /api/ai/chat
  → Request:  { messages: [{ role, content }], context?: { asset, balance, pnl, winRate } }
  → Response: { response: str, model: str, usage: { input_tokens, output_tokens } }
  → Purpose: Text-only chat with optional trading context injection

POST /api/ai/analyze-image
  → Request:  { image_base64: str, prompt?: str, context?: { asset, balance, pnl, winRate } }
  → Response: { analysis: str, model: str, usage: { input_tokens, output_tokens } }
  → Purpose: Screenshot/chart analysis with vision model
```

---

## 5. Key Design Decisions

### 5.1 Why `httpx` Instead of the OpenAI SDK

The xAI API is OpenAI-compatible, so a thin `httpx` client hitting `https://api.x.ai/v1/responses` is:
- **Simpler** — ~50 lines of code vs. a full SDK
- **Zero new dependencies** — `httpx` is likely already in the conda env; if not, it's one `pip install`
- **Provider boundary is crystal clear** — The provider file is the only place that knows about xAI
- **Easier to swap** — Adding an OpenAI or Anthropic provider is just another file with the same interface

### 5.2 Why Frontend Owns Conversation State

- xAI recommends NOT storing request/response history server-side when images are involved
- Keeps the backend stateless and simple (pure proxy)
- Zustand persistence means chat survives page refreshes
- Conversation cap at ~20 messages prevents payload bloat

### 5.3 Why RightSidebar Tabs (Not a New View)

- The AI assistant should be **ambient** — always accessible while trading, not a separate page
- Risk pulse and AI are complementary: check risk → ask AI for advice → continue trading
- No changes to `MainLayout.jsx` or `useLayoutStore.js` routing needed
- Keeps the existing three-surface architecture intact (Settings = configure, RightSidebar = observe, Risk Manager = manage)

### 5.4 System Prompt Strategy

The system prompt lives server-side only in `ai_service.py`. It includes:
- What OTC SNIPER is (OTC binary options trading tool)
- Advisory-only rules (never suggest specific trade execution)
- Chart analysis guidelines (identify patterns, support/resistance, trend direction)
- Risk awareness (reference the user's session context if provided)
- Response format preferences (concise, actionable, structured)

The frontend never sends or sees the system prompt.

### 5.5 Context Injection (Optional, Scalable)

The frontend can optionally send a `context` object with any AI request:

```json
{
  "context": {
    "asset": "EURUSD_otc",
    "balance": 1000.00,
    "sessionPnl": 45.00,
    "winRate": 68.5,
    "currentStreak": 3,
    "totalTrades": 12
  }
}
```

The backend injects this into the system prompt so Grok has trading context. This is opt-in and never required.

---

## 6. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| API key exposure to frontend | Backend is the sole proxy. `GROK_API_KEY` never leaves the server. |
| Prompt injection via user input | System prompt is server-side only. User messages are passed as `user` role content. |
| Image size abuse | Backend validates image size (<20MB) and format (JPEG/PNG) before proxying. |
| Rate limiting / cost control | Backend enforces request debounce. Frontend disables send button during loading. Phase 9: add proper rate limiting middleware. |
| AI executing trades | No trade execution paths exist in the AI router. AI endpoints return text only. |
| Service unavailability | `GET /api/ai/status` lets frontend disable AI tab entirely if no API key or service is down. |

---

## 7. Dependency Analysis

### Backend
- **`httpx`** — Async HTTP client for xAI API calls. Check if already in QuFLX-v2 conda env. If not: `pip install httpx`.
- No other new dependencies.

### Frontend
- **Zero new dependencies.** Uses native `fetch` (via existing `httpClient.js`), `FileReader` for base64 conversion, existing Zustand patterns.
- Icons from `lucide-react` (already installed).

---

## 8. Model Configuration in Settings

Add to App Settings (Phase 7 already built):

| Setting | Key | Default | Options |
|---------|-----|---------|---------|
| AI Model | `aiModel` | `grok-4-1-fast-non-reasoning` | `grok-4-1-fast-non-reasoning`, `grok-4-1-fast-reasoning`, `grok-4` |

Stored in `useSettingsStore` and sent with each AI request to the backend.

---

## 9. Reviewer Pre-Implementation Assessment

### ✅ Strengths
1. Provider abstraction is correct — swapping providers requires only a new provider file
2. No new frontend dependencies — keeps the bundle lean
3. Advisory-only enforcement — no trade execution paths in AI router
4. Stateless backend — no conversation storage server-side
5. Graceful degradation — status endpoint enables/disables AI tab
6. Tab-based RightSidebar — preserves existing risk pulse

### ⚠️ Medium Observations
1. Rate limiting should be added (Phase 9 hardening if not in Phase 8)
2. Image size validation must be enforced server-side before proxying

### ⚠️ Low Observations
1. Token usage tracking for cost monitoring (defer to Phase 9)
2. Conversation length cap at ~20 messages to prevent payload bloat

### Verdict
**✅ Plan is sound, scalable, and aligned with CORE_PRINCIPLES.** No blockers. Ready for implementation upon approval.

---

## 10. Acceptance Criteria

- [ ] `GET /api/ai/status` returns correct enabled/disabled state based on API key presence
- [ ] `POST /api/ai/chat` sends a text message and returns a structured Grok response
- [ ] `POST /api/ai/analyze-image` accepts a base64 image and returns chart analysis
- [ ] AI tab appears in the RightSidebar with Risk/AI tab toggle
- [ ] Chat messages display correctly with user/assistant distinction
- [ ] Image upload (drag-drop or file picker) converts to base64 and sends to analyze endpoint
- [ ] AI functionality is completely disabled when `GROK_API_KEY` is not set
- [ ] No AI endpoint can trigger trade execution or modify risk settings
- [ ] Production build passes with 0 errors
- [ ] Backend validates image size (<20MB) and format (JPEG/PNG) before proxying

---

## 11. Future Scalability Paths

These are NOT in Phase 8 scope but the architecture supports them:

- **Additional providers** — Add `openai_provider.py` or `anthropic_provider.py` with the same interface
- **Streaming responses** — xAI supports SSE streaming; can be added to the provider layer
- **Conversation persistence** — Save chat history to `data/ai/` for session review
- **Automated context injection** — Auto-attach current chart data, OTEO signals, and risk state to every AI request
- **Prompt templates** — Pre-built analysis prompts (e.g., "Analyze this 5-min chart", "Summarize my session")
- **Cost dashboard** — Track and display token usage and estimated costs per session
