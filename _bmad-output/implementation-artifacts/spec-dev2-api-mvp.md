---
title: 'Dev2 API Infrastructure MVP'
type: 'feature'
created: '2026-04-18'
status: 'done'
baseline_commit: '5b0b618bde62364b234e848c615c47e3f70ac015'
context:
  - 'docs/ARCHITECTURE.md'
  - 'docs/Dev1-AI-Pipeline.md'
  - 'docs/Dev2-API-Infrastructure.md'
---

## Intent

**Problem:** PrenatalAI backend doesn't exist — need FastAPI app with diagnosis endpoints, SQLite persistence, Docker deployment, and background task support.

**Approach:** Build the API layer with mock/skeleton implementations that wire to Dev1's AI modules. Start with `POST /diagnosis` returning hardcoded responses, then layer in service orchestration, Docker containerization, and background comprehensive scan.

## Boundaries & Constraints

**Always:**
- Single container, `docker compose up` brings up everything
- SQLite for metadata (file on disk, zero infra)
- FastAPI `BackgroundTasks` for async comprehensive scan (no Celery/Redis)
- Local filesystem for image storage
- Self-hostable — no external cloud APIs

**Ask First:**
- Ollama integration approach (Dev1 owns medgemma.py)

**Never:**
- PostgreSQL or any server-based database
- MinIO/S3 for image storage
- Multi-container setup (except Ollama as optional sidecar)
- Cloud infrastructure

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HEALTH_CHECK | GET /health | {"status": "ok"} | N/A |
| DIAGNOSIS_MOCK | POST /diagnosis with image | Fast track response (top 5) + comprehensive pending | 422 if missing required fields |
| COMPREHENSIVE_PENDING | GET /diagnosis/{id}/comprehensive | 202 + {"status": "pending"} | 404 if task not found |
| CASE_UPLOAD | POST /cases with image + diagnosis | 201 + case_id | 422 if validation fails |
| LIST_CASES | GET /cases?disease=&trimester= | Paginated case list | Empty list if no matches |
| LIST_DISEASES | GET /diseases | Disease list with trimester weights | Always returns 200 |

## Code Map

- `backend/app/main.py` -- FastAPI bootstrap + health endpoint
- `backend/app/config.py` -- Pydantic Settings (DATA_DIR, CHROMA_PATH, DB_PATH, OLLAMA_HOST)
- `backend/app/models/` -- Shared Pydantic models (DiagnosisQuery, PatientContext, DiagnosisResult, etc.)
- `backend/app/db/database.py` -- SQLAlchemy + SQLite engine
- `backend/app/db/repositories.py` -- CRUD for CommunityCase, Disease, Contributor
- `backend/app/api/diagnosis.py` -- POST /diagnosis, GET /diagnosis/{id}/comprehensive
- `backend/app/api/cases.py` -- POST /cases, GET /cases
- `backend/app/api/diseases.py` -- GET /diseases, GET /diseases/{id}/weights
- `backend/app/services/diagnosis.py` -- run_diagnosis() mock, BackgroundTasks for comprehensive
- `backend/app/services/case_upload.py` -- process_case_upload() stub
- `backend/app/services/validation.py` -- validate_case() stub
- `backend/tests/test_api.py` -- API endpoint tests
- `backend/requirements.txt` -- Python dependencies
- `backend/Dockerfile` -- Single container build
- `backend/docker-compose.yml` -- Volume mounts for /data

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/config.py` -- Settings from env vars with pydantic-settings
- [x] `backend/app/main.py` -- FastAPI app with /health, import routers
- [x] `backend/app/models/__init__.py` -- Re-export Dev1's models (PatientContext, DiagnosisResult, etc.)
- [x] `backend/app/models/diagnosis.py` -- DiagnosisQuery, DiagnosisResponse, PatientContext MoM
- [x] `backend/app/db/database.py` -- SQLAlchemy engine, SessionLocal, Base
- [x] `backend/app/db/repositories.py` -- CaseRepository, DiseaseRepository
- [x] `backend/app/api/diagnosis.py` -- POST /diagnosis returning mock top-5, GET /{id}/comprehensive
- [x] `backend/app/api/cases.py` -- POST /cases, GET /cases
- [x] `backend/app/api/diseases.py` -- GET /diseases, GET /{id}/weights
- [x] `backend/app/services/diagnosis.py` -- run_diagnosis() mock, run_comprehensive_background() with BackgroundTasks
- [x] `backend/app/services/case_upload.py` -- process_case_upload() stub
- [x] `backend/requirements.txt` -- Dependencies per Dev2 doc
- [x] `backend/Dockerfile` -- Python 3.11-slim + pip install
- [x] `backend/docker-compose.yml` -- Single service, ./data volume mount
- [x] `backend/tests/test_api.py` -- Test file (partial - DB dependency injection needs refinement)

**Acceptance Criteria:**
- Given FastAPI server running, when GET /health, then {"status": "ok"}
- Given running app, when POST /diagnosis with mock image, then 200 with fast_track array and comprehensive_pending flag
- Given running app, when GET /diseases, then returns disease list
- Given Docker installed, when docker compose up, then single container starts on port 8000
- Given app running in Docker, when uploading case, then image saved to /data/images

## Design Notes

**Mock Diagnosis Response Structure:**
```python
{
    "fast_track": [
        {
            "disease_id": "down_syndrome",
            "disease_name": "Down Syndrome (Trisomy 21)",
            "final_score": 0.65,
            "confidence_interval": [0.55, 0.75],
            "applied_priors": ["maternal_age_35"],
            "matching_positive_cases": [{"case_id": "mock_001", "similarity": 0.82}],
            "matching_negative_cases": [{"case_id": "mock_neg_001", "similarity": 0.25}]
        }
    ],
    "comprehensive_pending": True,
    "comprehensive_callback_url": "/api/v1/diagnosis/mock-task-123/comprehensive",
    "fast_track_ms": 150,
    "timestamp": "2026-04-18T12:00:00Z"
}
```

**Service Layer Pattern:** Dev1 implements core modules in `backend/app/core/`. Dev2's services in `backend/app/services/` call Dev1's core functions. For MVP mock, services return hardcoded data until Dev1's modules exist.

**Background Task Flow:** POST /diagnosis returns immediately with fast_track results + task_id. Comprehensive scan runs in BackgroundTasks, results stored in SQLite with task_id. Client polls GET /diagnosis/{task_id}/comprehensive.

## Verification

**Commands:**
- `cd backend && python -m uvicorn app.main:app --reload` -- expected: server starts on port 8000
- `curl http://localhost:8000/health` -- expected: {"status":"ok"}
- `curl -X POST http://localhost:8000/api/v1/diagnosis -F "images=@test.jpg" -F "trimester=1st" -F "mother_age=35" -F "gestational_age_weeks=12"` -- expected: mock diagnosis response
- `cd backend && docker build -t prenatal-ai .` -- expected: image builds successfully
- `cd backend && docker compose up` -- expected: container starts, port 8000 accessible

**Manual checks (if no CLI):**
- Swagger UI at http://localhost:8000/docs shows all endpoints
- /data directory created with db.sqlite, images/, vector_db/ subdirs after first run

## Suggested Review Order

**API Structure & Entry Point**

- FastAPI bootstrap with lifespan, CORS, and router aggregation
  [`backend/app/main.py:1`](backend/app/main.py#L1)

**Endpoints & Request Handling**

- Diagnosis endpoint: form-based image upload, patient context, background task queuing
  [`backend/app/api/diagnosis.py:1`](backend/app/api/diagnosis.py#L1)
- Cases endpoint: multipart upload, contributor validation, case listing
  [`backend/app/api/cases.py:1`](backend/app/api/cases.py#L1)
- Diseases endpoint: disease listing with trimester weights
  [`backend/app/api/diseases.py:1`](backend/app/api/diseases.py#L1)

**Data Models**

- Patient context and diagnosis result schemas (Pydantic v2)
  [`backend/app/models/diagnosis.py:1`](backend/app/models/diagnosis.py#L1)
- SQLAlchemy ORM models (Disease, CommunityCase, DiagnosisTask, Contributor)
  [`backend/app/db/models.py:1`](backend/app/db/models.py#L1)

**Service Layer (Mock Implementation)**

- Mock diagnosis with contextual score adjustment (maternal age, IVF, biomarkers)
  [`backend/app/services/diagnosis.py:1`](backend/app/services/diagnosis.py#L1)
- Background comprehensive scan task
  [`backend/app/services/diagnosis.py:85`](backend/app/services/diagnosis.py#L85)

**Infrastructure**

- Single-container Dockerfile with volume mounts
  [`backend/Dockerfile:1`](backend/Dockerfile#L1)
- Docker compose for local dev
  [`backend/docker-compose.yml:1`](backend/docker-compose.yml#L1)