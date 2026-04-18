---
title: 'Real Diagnosis Pipeline - MVP Priority Fixes'
type: 'feature'
created: '2026-04-18'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** MVP demo used mock data — API called `run_diagnosis_mock` instead of real pipeline, images weren't saved, ChromaDB wasn't seeded.

**Approach:** Wire the 4 priority fixes: (1) DiagnosisService into API + save images, (2) ChromaDB trigger on case upload, (3) seed mock data, (4) verify TRIMESTER_WEIGHTS.

## Changes

| Priority | Fix | Status |
|----------|-----|--------|
| 1 | Wire `DiagnosisService` into `/api/v1/diagnosis` + save images | Done |
| 2 | Trigger ChromaDB embedding on case upload | Done |
| 3 | Seed ChromaDB with mock data (3 disease JSON files) | Done |
| 4 | TRIMESTER_WEIGHTS has all 6 diseases (already present) | Done |

### Files Changed

- `backend/app/api/diagnosis.py` — replaced mock with DiagnosisService, added image saving to /data/images/
- `backend/app/services/case_upload.py` — added async `_trigger_embedding` to compute and store embeddings on upload
- `backend/scripts/seed_mock_data.py` — fixed hardcoded paths → relative to script dir
- `backend/app/config.py` — added `extra="ignore"` to Settings to handle frontend .env vars
- `backend/data/mock_cases/down_syndrome_1st.json` — created mock data (5 pos + 5 neg cases)
- `backend/data/mock_cases/edwards_syndrome_1st.json` — created mock data (2 pos + 2 neg)
- `backend/data/mock_cases/patau_syndrome_1st.json` — created mock data (2 pos + 2 neg)

### ChromaDB Collections Seeded

- `down_syndrome_1st`: 10 cases
- `edwards_syndrome_1st`: 4 cases
- `patau_syndrome_1st`: 4 cases

### Verification

```bash
cd backend
DATA_DIR=./data DB_PATH=./data/db.sqlite CHROMA_PATH=./data/vector_db IMAGE_DIR=./data/images .venv/bin/python -m uvicorn app.main:app --port 8000
curl http://localhost:8000/health
```

## Suggested Review Order

**API Layer**

- Diagnosis endpoint with real service wiring + image persistence
  [`backend/app/api/diagnosis.py:33`](backend/app/api/diagnosis.py#L33)

**Service Layer**

- Case upload with ChromaDB embedding trigger
  [`backend/app/services/case_upload.py:51`](backend/app/services/case_upload.py#L51)
- Background embedding task
  [`backend/app/services/case_upload.py:101`](backend/app/services/case_upload.py#L101)