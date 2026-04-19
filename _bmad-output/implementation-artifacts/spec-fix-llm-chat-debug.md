---
title: 'Fix LLM Chat + Frontend-Backend Integration'
type: 'bugfix'
created: '2026-04-19'
status: 'ready-for-dev'
context:
  - 'frontend/src/pages/Chat.jsx'
  - 'frontend/vite.config.js'
  - 'backend/app/api/llm.py'
  - 'backend/app/core/ollama_client.py'
  - 'api/src/index.js'
---

## Intent

**Problem:** The `/api/llm/chat` endpoint is not working and the frontend-backend integration has path mismatches preventing proper linking.

**Approach:**
1. Add debug logging at each layer (Express proxy, FastAPI endpoint, OllamaClient) to trace requests
2. Fix any integration issues found during debugging
3. Verify frontend properly calls backend endpoints

## Boundaries & Constraints

**Always:**
- Keep existing API contract (request/response shapes unchanged)
- Preserve error handling behavior
- Use structured logging for easy filtering

**Never:**
- Modify Ollama API call structure (standard Ollama chat format)
- Expose sensitive data in logs (no credentials, no full image data)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CHAT_HAPPY | POST /api/llm/chat with valid message | LLM response with response text | N/A |
| OLLAMA_UNAVAILABLE | Ollama not running | 503 "LLM service not available" | Catches is_available()=false |
| PROXY_ERROR | Express can't reach FastAPI | 502 proxy error | onError handler |
| FRONTEND_PROXY | Vite dev server proxy | Forwards /api/* to Express | vite.config.js proxy |

## Code Map

**Frontend:**
- `frontend/src/pages/Chat.jsx` -- Calls /api/llm/chat via fetch(buildApiUrl(...))
- `frontend/src/lib/api.js` -- buildApiUrl() for constructing API URLs
- `frontend/vite.config.js` -- Proxy config: /api -> http://localhost:3000

**Backend:**
- `api/src/index.js` -- Express proxy for /api/llm (needs debug logging)
- `backend/app/api/llm.py` -- FastAPI chat endpoint (needs request/response logging)
- `backend/app/core/ollama_client.py` -- Ollama client (needs debug logging on chat calls)
- `backend/app/config.py` -- Settings including OLLAMA_HOST

## Tasks & Acceptance

**Debug Logging:**
- [ ] `api/src/index.js` -- Add DEBUG logging to /api/llm proxy -- trace proxy req/res
- [ ] `backend/app/api/llm.py` -- Add logging to chat endpoint -- log request received, Ollama response, errors
- [ ] `backend/app/core/ollama_client.py` -- Add logging to chat() method -- log model, messages, response

**Frontend-Backend Linking:**
- [ ] Verify Chat.jsx uses correct URL path `/api/llm/chat`
- [ ] Verify vite proxy forwards to correct Express port (3000)
- [ ] Verify Express proxies /api/llm/* to FastAPI correctly
- [ ] Test end-to-end: Frontend Chat → Express → FastAPI → Ollama → response back

**Acceptance Criteria:**
- Given Ollama is running, when user sends chat message in frontend, then LLM response appears in UI
- Given DEBUG=true, when chat flows through Express→FastAPI→Ollama, then logs show full trace
- Given Ollama is unavailable, when POST /api/llm/chat, then 503 error with helpful message
- Given all services running, when Chat page loads, then "Online" status shows green

## Debug Log Flow

```
Frontend: fetch('/api/llm/chat', ...)
  ↓ Vite proxy (if dev)
Express: [PROXY] POST /api/llm/chat -> http://backend:8000/api/llm/chat
  ↓
FastAPI: [LLM] Received chat request: message="..."
  ↓
OllamaClient: [OLLAMA] Sending chat request to http://localhost:11434/api/chat
OllamaClient: [OLLAMA] Response received: model=medgemma, content_length=XXX
  ↓
FastAPI: [LLM] Returning response to client
  ↓
Express: [PROXY] Response 200 for /api/llm/chat
  ↓
Frontend: displays response
```

## Verification

**Commands:**
- `curl -X POST http://localhost:3000/api/llm/chat -H "Content-Type: application/json" -d '{"message":"test"}'` -- test through Express
- `curl -X POST http://localhost:8000/api/llm/chat -H "Content-Type: application/json" -d '{"message":"test"}'` -- test direct to FastAPI
- `curl http://localhost:11434/api/tags` -- verify Ollama is running

**Frontend checks:**
- Open Chat page in browser, see if "Online" indicator shows
- Send a test message, see if response appears