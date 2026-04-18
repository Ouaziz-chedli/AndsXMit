---
title: 'Fix MedGemma Embedding Error'
type: 'bugfix'
created: '2026-04-19'
status: 'draft'
context:
  - 'backend/app/core/medgemma.py'
  - 'backend/app/core/ollama_client.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** MedGemma does not support embeddings (Ollama returns "this model does not support embeddings"). The diagnosis pipeline fails when trying to generate symptom embeddings for vector similarity search.

**Approach:** Fall back to mock embeddings when Ollama embedding API fails. Use a deterministic hash-based embedding for development/testing that doesn't require Ollama.

## Boundaries & Constraints

**Always:**
- System should still function when Ollama embeddings fail
- Mock embeddings should be deterministic (same text = same embedding)
- Mock embeddings must be 768-dimensional (matching vector store)

**Never:**
- Don't modify Ollama model (not possible)
- Don't require external embedding service

</frozen-after-approval>

## Tasks & Acceptance

**Execution:**
- [ ] `backend/app/core/ollama_client.py` -- Add try/except for embedding failures -- Graceful fallback
- [ ] `backend/app/core/medgemma.py` -- Add mock embedding fallback in embed_symptoms_async -- 768-dim deterministic

**Acceptance Criteria:**
- Given Ollama returns embedding error, when embed_symptoms_async(), then returns mock embedding without crashing
- Given same symptom text, when embed_symptoms_async() twice, then returns same embedding (deterministic)

## Verification

```bash
cd backend && source .venv/bin/activate && python3 -c "
from app.core.medgemma import MedGemma
import asyncio

async def test():
    m = MedGemma(use_mock=False)
    m.load()
    # Test embedding
    emb = await m.embed_symptoms_async('cardiac normal, femur 45mm')
    print(f'Embedding size: {len(emb)}')
    print(f'First 5 values: {emb[:5]}')

asyncio.run(test())
"
```
