# Backend Task Division — Two Developers

UI/UX and Marketing are handled by a separate team.

---

## Dev 1 — AI/ML Pipeline (Bottom-Up)

**Owns**: everything from image → symptom extraction → vector search → final scores (no API layer)

### Tasks

**Phase 1: Foundation (do first — others depend on it)**
- Define and finalize Pydantic models in `backend/app/models/` (`DiagnosisQuery`, `PatientContext`, `DiagnosisResult`, `DiseaseCase`) — this is the **contract** with Dev 2
- `backend/app/core/medgemma.py` — MedGemma integration (local inference + API fallback), symptom extraction from images
- `backend/app/core/vector_store.py` — ChromaDB abstraction (init per-disease collections, upsert, similarity search)

**Phase 2: Core Engine**
- `backend/app/core/scoring.py` — raw score calculation (`avg(pos) - avg(neg)`)
- `backend/app/core/aggregation.py` — trimester weighting + symptom overlap distribution
- `backend/app/core/priors.py` — Bayesian prior multipliers (maternal age, family history, IVF)

**Phase 3: Data**
- `backend/scripts/compute_embeddings.py` — pre-compute embeddings for seeded cases
- `backend/scripts/seed_diseases.py` — initialize `data/diseases.json`, `trimester_weights.json`, `priors_config.json`
- `backend/scripts/seed_mock_data.py` — mock positive/negative cases for Down Syndrome (1st trimester) for demo
- `data/` — populate `diseases.json` with Down Syndrome as MVP disease

**Phase 4: Tests**
- `backend/tests/test_aggregation.py`
- `backend/tests/test_medgemma.py` (mocked)

---

## Dev 2 — Backend API + Infrastructure (Top-Down)

**Owns**: FastAPI app, all endpoints, async jobs, DB, Docker — calls into Dev 1's core modules via services

### Tasks

**Phase 1: Foundation (do in parallel with Dev 1's Phase 1)**
- `backend/app/main.py` + `config.py` — FastAPI app bootstrap, settings (env vars, DB URLs, etc.)
- `docker-compose.yml` — PostgreSQL + Redis + ChromaDB + app
- `backend/app/db/database.py` — SQLAlchemy setup + connection pooling
- `backend/app/db/repositories.py` — CRUD for `CommunityCase`, `Contributor`, `Disease`

**Phase 2: Services Layer (after Dev 1 has models)**
- `backend/app/services/diagnosis.py` — orchestrates fast track + background comprehensive scan, calls `core/medgemma.py` and `core/aggregation.py`
- `backend/app/services/case_upload.py` — validates upload, calls anonymizer, triggers embedding computation
- `backend/app/services/validation.py` — admin case validation workflow

**Phase 3: API Endpoints**
- `backend/app/api/diagnosis.py` — `POST /api/v1/diagnosis`, `GET /api/v1/diagnosis/{id}/comprehensive`
- `backend/app/api/cases.py` — `POST /api/v1/cases`, `GET /api/v1/cases`
- `backend/app/api/diseases.py` — `GET /api/v1/diseases`, `GET /api/v1/diseases/{id}/weights`
- `backend/app/api/vector.py` — internal vector search/index endpoints

**Phase 4: Async + Storage**
- Celery + Redis worker setup for comprehensive background scan
- `backend/app/db/s3.py` — MinIO/S3 client for image storage
- `backend/tests/test_api.py` + `test_integration.py`

---

## Interface Contract (Define Day 1)

Dev 2 calls Dev 1's services through these boundaries — agree on these before splitting:

```python
# Dev 1 exposes, Dev 2 calls:
async def extract_symptoms(image_bytes: bytes) -> SymptomDescription: ...
async def search_disease(query_embedding, disease_id, trimester, top_k) -> list[RetrievedCase]: ...
def aggregate_scores(similarity_results, trimester, patient_context) -> list[DiagnosisResult]: ...
```

Both devs agree on the Pydantic models in `backend/app/models/` **on day 1** — that's the only real dependency.

---

## Hackathon MVP Priority

Focus on **Down Syndrome, 1st Trimester** end-to-end before expanding:

| Priority | Dev 1 | Dev 2 |
|----------|-------|-------|
| 1 | MedGemma working on a sample image | `POST /diagnosis` endpoint returning mock response |
| 2 | ChromaDB seeded with mock Down Syndrome cases | Docker compose running cleanly |
| 3 | Aggregation + scoring producing ranked output | Service layer wiring it all together |
| 4 | Priors for maternal age | Comprehensive scan background task |
