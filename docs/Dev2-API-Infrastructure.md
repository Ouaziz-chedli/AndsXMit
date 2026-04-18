# Dev 2 — API + Infrastructure

**Owns**: FastAPI app, endpoints, SQLite, background tasks, Docker — calls Dev 1's core modules

> UI/UX and Marketing are handled by a separate team.

---

## Core Constraint: Fully Self-Hostable

The hackathon app must run entirely on a hospital's own machine — no cloud, no external APIs, no managed services. A doctor should be able to run `docker compose up` and have everything working offline.

Complexity is only justified when it directly serves this goal. If a simpler tool does the job, use it.

### Stack Decisions (Relevant to Dev 2)

| Need | Simple choice | Ruled out |
|------|--------------|-----------|
| Relational metadata | **SQLite** (file on disk, zero infra) | PostgreSQL — needs a server |
| Async comprehensive scan | **FastAPI `BackgroundTasks`** (built-in) | Celery + Redis — two extra services |
| Image storage | **Local filesystem** (Docker volume) | MinIO/S3 — cloud concept |

### Target Deployment

```bash
docker compose up
```

Runs a **single container** with everything inside it:
- FastAPI app
- ChromaDB embedded (persists to `/data/vector_db` volume)
- SQLite (persists to `/data/db.sqlite` volume)
- MedGemma weights (mounted into `/data/models`)
- Uploaded images (persists to `/data/images` volume)

```yaml
# docker-compose.yml (target)
services:
  app:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
    environment:
      - DATA_DIR=/data
      - MEDGEMMA_MODEL_PATH=/data/models/medgemma
```

No other services. One container, one volume, runs offline.

---

## Phase 1: Foundation (parallel with Dev 1's Phase 1)

### `backend/app/main.py` + `config.py`

FastAPI bootstrap, settings from env vars:

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATA_DIR: str = "/data"
    MEDGEMMA_MODEL_PATH: str = "/data/models/medgemma"
    CHROMA_PATH: str = "/data/vector_db"
    DB_PATH: str = "/data/db.sqlite"
    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.background import BackgroundTasks

app = FastAPI(title="PrenatalAI")

@app.get("/health")
def health():
    return {"status": "ok"}
```

### `backend/app/db/database.py`

SQLAlchemy with SQLite:

```python
# sqlite:////{DATA_DIR}/db.sqlite
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(f"sqlite:///{settings.DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### `backend/app/db/repositories.py`

CRUD for shared models (Dev 1 defines these in `backend/app/models/`):

```python
# These models are defined by Dev 1 - import from there
from backend.app.models.case import CommunityCase
from backend.app.models.contributor import Contributor
from backend.app.models.disease import Disease

class CaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, case: CommunityCase) -> CommunityCase:
        self.session.add(case)
        self.session.commit()
        self.session.refresh(case)
        return case

    def get_by_id(self, case_id: str) -> CommunityCase | None:
        return self.session.query(CommunityCase).filter(CommunityCase.case_id == case_id).first()
```

### `backend/app/core/` (Dev 1's modules)

These are **interface modules** — Dev 2 calls them, Dev 1 implements them:

```python
# Dev 2 imports and calls Dev 1's modules:
from backend.app.core.medgemma import extract_symptoms
from backend.app.core.vector_store import search_disease
from backend.app.core.aggregation import aggregate_scores
```

### `Dockerfile` + `docker-compose.yml`

Single container, volume mounts for `/data`:

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Phase 2: Services Layer (after Dev 1 has models)

### `backend/app/services/diagnosis.py`

Fast track (sync) + comprehensive scan (`BackgroundTasks`, not Celery):

```python
# backend/app/services/diagnosis.py

async def run_diagnosis(
    images: list[UploadFile],
    trimester: str,
    patient_context: PatientContext
) -> DiagnosisReport:
    """
    1. Load images (Dev 1's image_processor)
    2. Extract symptoms (Dev 1's medgemma)
    3. Search disease DBs (Dev 1's vector_store)
    4. Aggregate scores (Dev 1's aggregation)
    5. Return results
    """
    # ... implementation
    pass

def run_comprehensive_background(
    images: list[UploadFile],
    trimester: str,
    patient_context: PatientContext,
    task_id: str
):
    """Background task for comprehensive scan."""
    # ... implementation
    pass
```

### `backend/app/services/case_upload.py`

Validates upload, anonymizes, saves image to `/data/images`, triggers embedding:

```python
# backend/app/services/case_upload.py

async def process_case_upload(
    images: list[UploadFile],
    diagnosis: DiagnosisData,
    contributor_id: str
) -> CommunityCase:
    # 1. Save images to /data/images/
    # 2. Anonymize any DICOM metadata
    # 3. Create CommunityCase record
    # 4. Trigger embedding computation
    # 5. Return case
    pass
```

### `backend/app/services/validation.py`

Admin case validation:

```python
# backend/app/services/validation.py

async def validate_case(case_id: str, validator_id: str, approved: bool) -> CommunityCase:
    """Mark case as validated (or rejected) by admin."""
    pass
```

---

## Phase 3: API Endpoints

### `backend/app/api/diagnosis.py`

```python
from fastapi import APIRouter, UploadFile, File, Form
from typing import Annotated

router = APIRouter(prefix="/api/v1", tags=["diagnosis"])

@router.post("/diagnosis")
async def diagnose(
    images: list[UploadFile] = File(...),
    trimester: str = Form(...),
    maternal_age: int = Form(...),
    paternal_age: int | None = Form(None),
    family_history: str = Form(""),
    # ... other patient context fields
):
    """
    Upload ultrasound images and get diagnosis.
    Returns fast track immediately, comprehensive scan runs in background.
    """
    # ... calls diagnosis service
    pass

@router.get("/diagnosis/{id}/comprehensive")
async def get_comprehensive_results(id: str):
    """Get comprehensive scan results (poll after background processing)."""
    pass
```

### `backend/app/api/cases.py`

```python
router = APIRouter(prefix="/api/v1", tags=["cases"])

@router.post("/cases")
async def upload_case(
    images: list[UploadFile] = File(...),
    diagnosis: str = Form(...),
):
    """Upload a diagnosed case to the community database."""
    pass

@router.get("/cases")
async def list_cases(
    disease: str | None = None,
    trimester: str | None = None,
    validated: bool | None = None,
):
    """List cases (admin only)."""
    pass
```

### `backend/app/api/diseases.py`

```python
@router.get("/diseases")
async def list_diseases():
    """List all supported diseases with trimester weights."""
    pass

@router.get("/diseases/{disease_id}/weights")
async def get_disease_weights(disease_id: str):
    """Get trimester-specific symptom weights for a disease."""
    pass
```

---

## Phase 4: Tests

- `backend/tests/test_api.py`
- `backend/tests/test_integration.py`

---

## Interface Contract (Agree with Dev 1 Day 1)

Dev 2 **calls** these from Dev 1's modules:

```python
# Dev 1 implements, Dev 2 calls via services:
async def extract_symptoms(image_bytes: bytes) -> SymptomDescription: ...
async def search_disease(query_embedding, disease_id, trimester, top_k) -> list[RetrievedCase]: ...
def aggregate_scores(similarity_results, trimester, patient_context) -> list[DiagnosisResult]: ...
```

**Critical**: Pydantic models in `backend/app/models/` are the **only hard dependency** between devs. Agree on these before splitting work.

---

## MVP Priority

| Priority | Task |
|----------|------|
| 1 | `POST /diagnosis` returning a hardcoded mock response |
| 2 | Single-container Docker running cleanly |
| 3 | Service layer wiring Dev 1's output to the API |
| 4 | Comprehensive scan via `BackgroundTasks` |

One disease (Down Syndrome), one trimester (1st), end-to-end, running offline via Docker.
