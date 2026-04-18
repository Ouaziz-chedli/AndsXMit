# Backend Task Division — Two Developers

UI/UX and Marketing are handled by a separate team.

## Core Constraint: Fully Self-Hostable

The hackathon app must run entirely on a hospital's own machine — no cloud, no external APIs, no managed services. A doctor should be able to run `docker compose up` and have everything working offline.

Complexity is only justified when it directly serves this goal. If a simpler tool does the job, use it.

### Stack Decisions

| Need | Simple choice | Ruled out |
|------|--------------|-----------|
| Relational metadata | **SQLite** (file on disk, zero infra) | PostgreSQL — needs a server |
| Async comprehensive scan | **FastAPI `BackgroundTasks`** (built-in) | Celery + Redis — two extra services for no gain at this scale |
| Vector storage | **ChromaDB embedded** (`PersistentClient`, writes to disk) | ChromaDB server container — unnecessary when one process owns the DB |
| Image storage | **Local filesystem** (Docker volume) | MinIO/S3 — cloud concept, irrelevant for self-hosting |
| AI inference | **MedGemma local** (mandatory) | MedGemma API — breaks self-hosting |

### Target Deployment

```
docker compose up
```

Runs a **single container** with everything inside it:
- FastAPI app
- ChromaDB embedded (persists to `/data/vector_db` volume)
- SQLite (persists to `/data/db.sqlite` volume)
- MedGemma weights (mounted or pulled on first start into `/data/models`)
- Uploaded images (persists to `/data/images` volume)

```yaml
# docker-compose.yml (target)
services:
  app:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data          # vector DB, SQLite, images, model weights
    environment:
      - DATA_DIR=/data
      - MEDGEMMA_MODEL_PATH=/data/models/medgemma
```

No other services. One container, one volume, runs offline.

---

## Dev 1 — AI/ML Pipeline (Bottom-Up)

**Owns**: image → MedGemma symptom extraction → ChromaDB vector search → scored results

### Phase 1: Foundation (define first — Dev 2 depends on these models)

- Pydantic models in `backend/app/models/` — `DiagnosisQuery`, `PatientContext`, `DiagnosisResult`, `DiseaseCase`
- `backend/app/core/medgemma.py` — local MedGemma inference only (no API fallback; self-hosting is non-negotiable)
- `backend/app/core/vector_store.py` — ChromaDB `PersistentClient` abstraction (collections per disease, upsert, similarity search)

### Phase 2: Core Engine

- `backend/app/core/scoring.py` — `avg(positive_sims) - avg(negative_sims)`
- `backend/app/core/aggregation.py` — trimester weighting + symptom overlap distribution
- `backend/app/core/priors.py` — Bayesian multipliers (maternal age, family history, IVF)

### Phase 3: Data

- `backend/scripts/seed_diseases.py` — populate `data/diseases.json`, `trimester_weights.json`, `priors_config.json`
- `backend/scripts/seed_mock_data.py` — mock positive + negative Down Syndrome cases (1st trimester)
- `backend/scripts/compute_embeddings.py` — pre-compute and load embeddings into ChromaDB

### Phase 4: Tests

- `backend/tests/test_aggregation.py`
- `backend/tests/test_medgemma.py` (with a real small image, or mocked if model load is slow)

---

## Dev 2 — API + Infrastructure (Top-Down)

**Owns**: FastAPI app, endpoints, SQLite, background tasks, Docker — calls Dev 1's core modules

### Phase 1: Foundation (parallel with Dev 1's Phase 1)

- `backend/app/main.py` + `config.py` — FastAPI bootstrap, settings from env vars (`DATA_DIR`, `MEDGEMMA_MODEL_PATH`)
- `backend/app/db/database.py` — SQLAlchemy with SQLite (`sqlite:////{DATA_DIR}/db.sqlite`)
- `backend/app/db/repositories.py` — CRUD for `CommunityCase`, `Contributor`, `Disease`
- `Dockerfile` + `docker-compose.yml` — single container, volume mounts for `/data`

### Phase 2: Services Layer (after Dev 1 has models)

- `backend/app/services/diagnosis.py` — fast track (sync) + comprehensive scan (`BackgroundTasks`, not Celery)
- `backend/app/services/case_upload.py` — validates upload, anonymizes, saves image to `/data/images`, triggers embedding
- `backend/app/services/validation.py` — admin case validation

### Phase 3: API Endpoints

- `backend/app/api/diagnosis.py` — `POST /api/v1/diagnosis`, `GET /api/v1/diagnosis/{id}/comprehensive`
- `backend/app/api/cases.py` — `POST /api/v1/cases`, `GET /api/v1/cases`
- `backend/app/api/diseases.py` — `GET /api/v1/diseases`, `GET /api/v1/diseases/{id}/weights`

### Phase 4: Tests

- `backend/tests/test_api.py`
- `backend/tests/test_integration.py`

---

## Interface Contract (Agree Day 1)

```python
# Dev 1 exposes, Dev 2 calls via services:
async def extract_symptoms(image_bytes: bytes) -> SymptomDescription: ...
async def search_disease(query_embedding, disease_id, trimester, top_k) -> list[RetrievedCase]: ...
def aggregate_scores(similarity_results, trimester, patient_context) -> list[DiagnosisResult]: ...
```

Pydantic models in `backend/app/models/` are the only hard dependency between the two devs — agree on these before splitting.

---

## Hackathon MVP Priority

One disease (Down Syndrome), one trimester (1st), end-to-end, running offline via Docker.

| Priority | Dev 1 | Dev 2 |
|----------|-------|-------|
| 1 | MedGemma extracting symptoms from a sample image | `POST /diagnosis` returning a hardcoded mock response |
| 2 | ChromaDB seeded with mock Down Syndrome cases | Single-container Docker running cleanly |
| 3 | Aggregation + scoring producing a ranked result | Service layer wiring Dev 1's output to the API |
| 4 | Priors for maternal age | Comprehensive scan via `BackgroundTasks` |
