---
title: 'Debug Logging for Chat Function'
type: 'bugfix'
created: '2026-04-19'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** Chat function not working - requests not reaching Ollama. No visibility into where the request chain breaks.

**Approach:** Add debug logging throughout the request chain: Frontend (Chat → apiClient) → Express → FastAPI → Ollama.

## Suggested Review Order

**Frontend Debug Logging**
- `frontend/src/pages/Chat.jsx:42` -- Use apiClient instead of raw fetch for logging

**Docker Environment**
- `docker-compose.yml:14` -- Enable DEBUG=true for api service
- `docker-compose.yml:27` -- Enable VITE_DEBUG=true for frontend service
- `docker-compose.yml:44` -- Enable DEBUG=true for backend service