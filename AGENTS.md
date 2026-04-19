# PrenatalAI — Agent Instructions

## Repo Structure

```
PrenatalAI/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/               # FastAPI route handlers
│   │   ├── core/             # Pipeline modules (image_processor, medgemma, vector_store, scoring, aggregation, priors)
│   │   ├── services/         # Business logic (diagnosis.py)
│   │   ├── models/          # Pydantic models
│   │   └── db/              # SQLAlchemy + repositories
│   ├── tests/               # Unit tests (uses .venv pytest)
│   ├── data/mock_cases/      # Mock disease case JSON files
│   └── data/vector_db/      # ChromaDB (71 seeded cases)
├── save/                     # Auto-saved diagnosis data (image + results + context)
└── _bmad-output/             # BMAD planning/implementation artifacts
```

## Key Commands

```bash
cd backend

# Run tests (uses .venv)
./.venv/bin/python -m pytest tests/ -v
./.venv/bin/python -m pytest tests/test_medgemma.py -v  # Single test file

# Run server
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# Real end-to-end test
./.venv/bin/python tests/realtest.py /path/to/image.png --trimester 2nd --ga 20

# Seed/re-seed vector DB with embeddings
# Edit and run: backend/scripts/seed_mock_data.py (uses nomic-embed-text)

# Re-seed requires clearing collections first
ollama pull nomic-embed-text  # Must be installed for embeddings
```

## Architecture

### 9-Step Diagnosis Pipeline (`app/services/diagnosis.py`)
1. `_load_image()` — DICOM/JPEG/PNG via `image_processor.py`
2. `_extract_symptoms()` — MedGemma via Ollama (~20-60s per image)
3. `embed_symptoms_async()` — `nomic-embed-text` for 768-dim vectors
4. `_search_similar_cases()` — ChromaDB per-disease retrieval
5. `_calculate_raw_score()` — `avg(pos_sims) - avg(neg_sims)`
6. `_apply_trimester_weighting()` — `aggregate_scores()`
7. `_apply_priors()` — Bayesian priors (age, biomarkers, history)
8. `_calculate_confidence_interval()` — 95% CI
9. `_generate_result()` — Final `DiagnosisResult`

### Scoring Formula
```
final_score = (avg(pos_sims) - avg(neg_sims)) × trimester_weight × age_risk × biomarker_risk × prev_affected
```

## Critical Constraints

- **MedGemma does NOT support embeddings** — use `nomic-embed-text` for embeddings
- **MedGemma inference is slow** (~20-60s per image) — not suitable for tight timeouts
- **Vector DB must be seeded with same embedding model** — hash-based embeddings won't match nomic embeddings
- **Priors are algorithmic** — MedGemma sees ONLY the image, never patient context
- **/data is read-only in Docker** — use local `./data` for development
- **Mock data only exists for 1st trimester** — 2nd trimester cases were created but need seeding

## Ollama Models

| Model | Purpose |
|-------|---------|
| `medgemma` | Symptom extraction |
| `nomic-embed-text` | Embedding generation |

Install: `ollama pull medgemma && ollama pull nomic-embed-text`

## Testing Notes

- Tests use `asyncio_mode = auto` in pytest.ini
- `test_medgemma.py` has 24 tests (requires Ollama running for live tests)
- `realtest.py` is an E2E test script, not a pytest file
- Vector store tests create temp directories and clean up

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `CHROMA_PATH` | `/data/vector_db` | Use `./data/vector_db` locally |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Not `medgemma` |
| `DATA_DIR` | `/data` | Read-only in Docker |

## Data Saving

Diagnosis API auto-saves to `save/{timestamp}/{task_id}/`:
- `image.{ext}` — copy of uploaded image
- `results.json` — diagnosis scores, CI, priors, matches
- `context.json` — anonymized patient context (no biomarkers)