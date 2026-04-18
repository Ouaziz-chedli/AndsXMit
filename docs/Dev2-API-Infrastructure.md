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
    CHROMA_PATH: str = "/data/vector_db"
    DB_PATH: str = "/data/db.sqlite"
    # Ollama settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "medgemma"  # Or specific tag like "medgemma:latest"
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

---

## Ollama Setup (Model Hosting)

Ollama runs the AI model locally via a simple REST API. This is the simplest way to self-host MedGemma.

### Quick Start

```bash
# 1. Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama server (runs in background)
ollama serve

# 3. In another terminal, pull and run MedGemma
ollama pull medgemma
ollama run medgemma "Analyze this ultrasound image"

# GPU check (optional, for faster inference)
ollama ps  # Shows which model is loaded and hardware used
```

### Model Management Commands

```bash
# Pull a model (downloads to local cache)
ollama pull medgemma

# List available models
ollama list

# Run a model interactively
ollama run medgemma

# Remove a model
ollama rm medgemma

# Show model info
ollama show medgemma
```

### GPU Support

Ollama automatically uses GPU when available:

```bash
# Check if GPU is detected
ollama run medgemma "test"  # Look for "using GPU" in output

# Force CPU-only (slower but works without GPU)
OLLAMA_HOST=localhost:11434 CUDA_VISIBLE_DEVICES="" python your_script.py
```

### API Usage from Python

```python
# backend/app/core/ollama_client.py

import httpx
from typing import AsyncIterator

class OllamaClient:
    """Simple Ollama API client for MedGemma inference."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)  # Long timeout for inference

    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """
        Send image to Ollama for analysis.
        Works with medgemma model that supports vision.
        """
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": "medgemma",
                "prompt": prompt,
                "images": [image_bytes.hex()],  # Ollama expects hex-encoded image
                "stream": False,
            }
        )
        response.raise_for_status()
        return response.json()["response"]

    async def close(self):
        await self.client.aclose()
```

### Docker + Ollama (Production)

For production with GPU:

```bash
# docker-compose.yml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    runtime: nvidia

  app:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - ollama
    environment:
      - OLLAMA_HOST=http://ollama:11434

volumes:
  ollama_data:
```

Without GPU (CPU only, slow):

```bash
# Just run Ollama directly on host, app in Docker connects to host network
docker run -p 8000:8000 --network host your_app
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
from backend.app.core.medgemma import extract_symptoms  # Uses OllamaClient internally
from backend.app.core.vector_store import search_disease
from backend.app.core.aggregation import aggregate_scores
```

**Dev 1's medgemma module will call Ollama** (via httpx), not load model weights directly. This keeps the code simple — Ollama handles model management.

### `Dockerfile` + `docker-compose.yml`

Single container, volume mounts for `/data`:

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Pull model on container start (or via init script)
CMD ["sh", "-c", "ollama pull medgemma && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

```yaml
# docker-compose.yml (with Ollama)
services:
  app:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
      - ollama_data:/root/.ollama
    environment:
      - DATA_DIR=/data
      - OLLAMA_HOST=localhost:11434
    runtime: nvidia  # Optional: only if GPU available
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_data:
```

**Note**: GPU is strongly recommended for reasonable inference speed. Without GPU, CPU inference will be very slow (~30+ seconds per image).

---

## Quick Start Script

A single script to set up everything:

```bash
#!/bin/bash
# setup.sh - One-command setup for PrenatalAI

set -e

echo "Installing PrenatalAI..."

# 1. Install Ollama
echo "[1/4] Installing Ollama..."
if command -v ollama &> /dev/null; then
    echo "Ollama already installed"
else
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 2. Pull MedGemma model
echo "[2/4] Pulling MedGemma model (this may take a while on first run)..."
ollama pull medgemma

# 3. Start Ollama in background
echo "[3/4] Starting Ollama server..."
ollama serve &
sleep 3  # Wait for server to start

# 4. Install Python dependencies
echo "[4/4] Installing Python dependencies..."
pip install -r backend/requirements.txt

echo ""
echo "Setup complete! Run 'docker compose up' to start PrenatalAI."
echo "Or run 'python -m uvicorn app.main:app' for development."
```

```bash
# One-command setup (run from project root)
bash setup.sh
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
    # First-trimester biomarkers
    b_hcg: float | None = Form(None),       # IU/L, serum biomarker
    papp_a: float | None = Form(None),        # IU/L, serum biomarker
    mother_age: int = Form(...),              # Age at due date
    gestational_age_weeks: float = Form(...), # Weeks since LMP
    # Optional modifiers
    fetal_count: int = Form(1),              # 1, 2, or 3
    ivf_conception: bool = Form(False),
    previous_affected_pregnancy: bool = Form(False),
):
    """
    Upload ultrasound images and get diagnosis.
    Returns fast track immediately, comprehensive scan runs in background.

    First-trimester biomarkers (b-hCG, PAPP-A) are from blood test.
    Gestational age from ultrasound CRL measurement.
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
| 1 | Ollama running MedGemma locally |
| 2 | `POST /diagnosis` returning a hardcoded mock response |
| 3 | Single-container Docker running cleanly |
| 4 | Service layer wiring Dev 1's output to the API |
| 5 | Comprehensive scan via `BackgroundTasks` |

One disease (Down Syndrome), one trimester (1st), end-to-end, running offline via Docker.

---

## Troubleshooting

### Ollama Issues

```bash
# Ollama not starting
ollama serve  # Run manually to see error messages

# Model won't download
ollama pull medgemma  # Retry

# GPU not detected (should see "using GPU" when running)
nvidia-smi  # Check NVIDIA drivers installed
ollama run medgemma "test"  # Look for GPU usage in output

# Reset Ollama (if corrupted)
rm -rf ~/.ollama
ollama pull medgemma
```

### Docker Issues

```bash
# Build fails
docker build --no-cache -t prenatal-ai ./backend

# Port already in use
docker compose down
docker compose up

# Volume permissions
sudo chown -R $USER:$USER ./data
```

### API Connection Issues

```bash
# Test Ollama is running
curl http://localhost:11434/api/tags

# Test model is available
curl http://localhost:11434/api/show -d '{"name":"medgemma"}'

# Check app can reach Ollama
python -c "import httpx; httpx.get('http://localhost:11434').raise_for_status()"
```

---

## Dependencies

```txt
# backend/requirements.txt
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
sqlalchemy>=2.0.0
chromadb>=0.4.0
httpx>=0.27.0
pypdf>=4.0.0
sentence-transformers>=2.4.0
pydicom>=3.0.0
Pillow>=10.0.0
numpy>=1.24.0
scipy>=1.12.0
```
