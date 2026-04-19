---
title: 'Fix /api/llm Chat - API to Backend Communication'
type: 'bugfix'
created: '2026-04-19'
status: 'ready-for-dev'
context:
  - 'api/src/index.js'
  - 'backend/app/api/llm.py'
  - 'backend/app/main.py'
  - 'backend/app/core/ollama_client.py'
---

## Intent

**Problem:** Frontend can communicate with Express API (auth works), but `/api/llm/chat` requests from Express are not reaching FastAPI backend, or responses aren't coming back.

**Approach:** Investigate the proxy chain: Express → FastAPI. Test connectivity, verify pathRewrite logic, add debug logging, fix any misconfigurations.

## Code Map

- `api/src/index.js:74-105` -- `/api/llm` proxy configuration
- `backend/app/main.py:42` -- LLM router registration
- `backend/app/api/llm.py:10` -- Router prefix `/api/llm`
- `docker-compose.yml:15` -- `BACKEND_URL=http://backend:8000`

## Proxy Chain Analysis

```
Frontend → Express (/api/llm/chat)
  └─ Express proxy mounts at /api/llm
  └─ pathRewrite: /chat → /api/llm/chat
  └─ Forward to: http://backend:8000/api/llm/chat

Backend (FastAPI)
  └─ Router prefix: /api/llm
  └─ Endpoint: POST /chat → /api/llm/chat
  └─ OllamaClient.chat() → Ollama
```

## Investigation Tasks

- [ ] `api/src/index.js` -- Verify proxy pathRewrite logic is correct
- [ ] `api/src/index.js` -- Add explicit logging to trace proxy execution
- [ ] `backend/app/api/llm.py` -- Verify router is mounted at correct prefix
- [ ] `backend/app/core/ollama_client.py` -- Check OLLAMA_HOST resolution in Docker

## I/O & Edge-Case Matrix

| Scenario | Input | Expected | Error |
|----------|-------|----------|-------|
| HAPPY_PATH | POST /api/llm/chat | Response from Ollama | N/A |
| BACKEND_DOWN | Express → backend unreachable | 502 proxy error | Connection refused |
| WRONG_PATH | pathRewrite bug | 404 from backend | Wrong path sent |
| OLLAMA_DOWN | Ollama not running | 503 from backend | LLM unavailable |

## Spec Change Log

<!-- Empty until findings trigger changes -->