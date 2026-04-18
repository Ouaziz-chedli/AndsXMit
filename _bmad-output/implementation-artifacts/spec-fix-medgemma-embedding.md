---
title: 'Fix MedGemma Embedding Error'
type: 'bugfix'
created: '2026-04-19'
status: 'ready-for-dev'
context:
  - 'backend/app/core/medgemma.py'
  - 'backend/app/core/ollama_client.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** MedGemma does not support embeddings (Ollama returns "this model does not support embeddings"). The diagnosis pipeline fails when trying to generate symptom embeddings for vector similarity search.

**Approach:** 
1. Add a dedicated embedding model (`nomic-embed-text`) to Ollama for text embeddings
2. Fall back to deterministic hash-based embeddings when embedding API fails
3. Ensure mock embeddings are deterministic (same text = same embedding)

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
- [x] `backend/app/core/medgemma.py` -- Fix embed_image_async to use deterministic fallback -- Same hash-based approach as embed_symptoms_async
- [x] `backend/app/core/ollama_client.py` -- Update generate_embeddings to use dedicated embedding model -- Use nomic-embed-text for embeddings
- [x] `backend/app/config.py` -- Add OLLAMA_EMBEDDING_MODEL setting -- Default to nomic-embed-text

**Acceptance Criteria:**
- Given Ollama returns embedding error, when embed_symptoms_async(), then returns deterministic mock embedding
- Given same symptom text, when embed_symptoms_async() twice, then returns same embedding (deterministic)

## Verification

```bash
# Pull nomic-embed-text model (one-time setup)
ollama pull nomic-embed-text

# Test embedding
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
