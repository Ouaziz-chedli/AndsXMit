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

## Image Processing Pipeline

Ultrasound images require format-specific handling before MedGemma can process them.

### Ultrasound Format Support

| Format | Clinical Usage | Support |
|--------|---------------|---------|
| **DICOM** | ~90% of clinical ultrasound | Primary format |
| **JPEG** | Exports, consumer devices | Supported |
| **PNG** | Reports, secondary use | Supported |
| **Proprietary** | Vendor-specific (GE, Philips, Siemens) | Convert to DICOM first |

### Libraries Required

```
pydicom>=3.0.0     # DICOM file reading (handles compressed transfer syntaxes)
Pillow>=10.0.0     # JPEG/PNG handling
numpy>=1.24.0      # Pixel array manipulation
```

### Image Loading Implementation

```python
# backend/app/core/image_processor.py

import io
import numpy as np
from PIL import Image
from pydicom import dcmread
from pydicom.dataset import Dataset
from dataclasses import dataclass
from typing import Literal

@dataclass
class UltrasoundMetadata:
    """Critical metadata extracted from DICOM headers."""
    gestational_age_weeks: int | None
    trimester: Literal["1st", "2nd", "3rd"] | None
    acquisition_date: str | None
    patient_age: int | None
    study_description: str | None
    manufacturer: str | None

def load_ultrasound_image(
    filepath: str,
) -> tuple[Image.Image, UltrasoundMetadata]:
    """
    Load ultrasound image, handling DICOM or conventional formats.
    Returns PIL Image + extracted metadata.
    """
    ext = filepath.lower().split('.')[-1]

    if ext in ('dcm', 'dicom'):
        return _load_dicom(filepath)
    elif ext in ('jpg', 'jpeg', 'png'):
        return _load_conventional(filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")

def _load_dicom(filepath: str) -> tuple[Image.Image, UltrasoundMetadata]:
    """Load DICOM ultrasound file."""
    ds = dcmread(filepath)

    # Extract gestational age from DICOM tags
    gestational_age = _extract_gestational_age(ds)
    trimester = _compute_trimester(gestational_age)

    metadata = UltrasoundMetadata(
        gestational_age_weeks=gestational_age,
        trimester=trimester,
        acquisition_date=str(ds.StudyDate) if hasattr(ds, 'StudyDate') else None,
        patient_age=int(ds.PatientAge) if hasattr(ds, 'PatientAge') else None,
        study_description=ds.StudyDescription if hasattr(ds, 'StudyDescription') else None,
        manufacturer=ds.Manufacturer if hasattr(ds, 'Manufacturer') else None,
    )

    # Handle different transfer syntaxes (compressed/uncompressed)
    pixel_array = ds.pixel_array

    # Normalize to 8-bit for MedGemma
    if pixel_array.dtype != np.uint8:
        pixel_array = ((pixel_array - pixel_array.min()) /
                       (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)

    # Convert to PIL Image
    image = Image.fromarray(pixel_array)

    # Handle color vs grayscale
    if image.mode != 'RGB':
        image = image.convert('RGB')

    return image, metadata

def _load_conventional(filepath: str) -> tuple[Image.Image, UltrasoundMetadata]:
    """Load JPEG/PNG ultrasound export."""
    image = Image.open(filepath)

    # Force RGB for consistency
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # No DICOM metadata available for conventional formats
    metadata = UltrasoundMetadata(
        gestational_age_weeks=None,
        trimester=None,  # Must be provided by user
        acquisition_date=None,
        patient_age=None,
        study_description=None,
        manufacturer=None,
    )

    return image, metadata

def _extract_gestational_age(ds: Dataset) -> int | None:
    """Extract gestational age from DICOM tags."""
    # Try various DICOM tags for gestational age
    for tag in ['GestationalAge', 'GestationalAgeSample', 'ClinicalTrialTimePoint']:
        if hasattr(ds, tag):
            try:
                return int(float(getattr(ds, tag)))
            except (ValueError, TypeError):
                continue
    return None

def _compute_trimester(gestational_age_weeks: int | None) -> Literal["1st", "2nd", "3rd"] | None:
    """Determine trimester from gestational age."""
    if gestational_age_weeks is None:
        return None
    if gestational_age_weeks <= 13:
        return "1st"
    elif gestational_age_weeks <= 26:
        return "2nd"
    else:
        return "3rd"
```

### Usage in Diagnosis Pipeline

```python
# In backend/app/core/medgemma.py

async def extract_symptoms(image_path: str, user_provided_trimester: str | None = None):
    """
    Extract symptoms from ultrasound image.
    User-provided trimester overrides DICOM metadata.
    """
    image, metadata = load_ultrasound_image(image_path)

    # Prefer user-provided trimester (from form input) over DICOM
    trimester = user_provided_trimester or metadata.trimester

    if trimester is None:
        raise ValueError(
            "Trimester must be provided: DICOM has no gestational age "
            "and user did not specify."
        )

    # Convert PIL Image to bytes for MedGemma
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)

    symptoms = medgemma.analyze(image_bytes.read())

    return SymptomDescription(
        symptoms=symptoms,
        trimester=trimester,
        gestational_age=metadata.gestational_age_weeks,
        metadata_source="dicom" if metadata.trimester else "user",
    )
```

### DICOM De-identification

Before storing DICOM images in the community database, strip PII:

```python
def anonymize_dicom(ds: Dataset) -> Dataset:
    """Remove PII from DICOM file before community storage."""
    # These fields contain PII - clear them
    pii_fields = [
        'PatientName', 'PatientID', 'PatientBirthDate',
        'PatientSex', 'PatientAddress', 'PatientTelephoneNumbers',
        'OtherPatientIDs', 'OtherPatientNames',
        'StudyDate', 'StudyTime',  # Optional: remove for full anonymization
    ]
    for field in pii_fields:
        if hasattr(ds, field):
            setattr(ds, field, None)

    ds.is_little_endian = True
    ds.is_implicit_VR = True
    return ds
```

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

---

## Document Processing Pipeline

The system handles **two distinct data types** with separate pipelines:

| Data Type | Input | Processing | Embedding Model |
|-----------|-------|------------|-----------------|
| **Ultrasound images** | DICOM, JPEG, PNG | MedGemma → symptom text | Vision encoder |
| **Medical documents** | PDF, TXT | Chunk → embed | Sentence Transformers |

### Libraries Required

```
pydicom>=3.0.0        # DICOM ultrasound image reading
Pillow>=10.0.0        # JPEG/PNG handling
numpy>=1.24.0         # Pixel array manipulation
pypdf>=4.0.0          # PDF text extraction
sentence-transformers # Text embeddings
chromadb              # Vector storage (already in stack)
```

### Document Processing Implementation

```python
# backend/app/core/document_processor.py

import re
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb

def clean_text(text: str) -> str:
    """Normalize medical text for embedding."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text on sentence boundaries, respecting semantic units."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        chunk = text[start:end]
        # Break at sentence boundary nearest to chunk_size * 0.5
        last_punctuation = max(chunk.rfind('.'), chunk.rfind('!'), chunk.rfind('?'))
        if last_punctuation != -1 and last_punctuation > chunk_size * 0.5:
            actual_end = start + last_punctuation + 1
        else:
            last_space = chunk.rfind(' ')
            actual_end = start + last_space if last_space != -1 else end

        chunks.append(text[start:actual_end].strip())
        start = actual_end - overlap

    return [c for c in chunks if len(c) > 10]

def process_document(directory: str, collection_name: str, embed_model: str):
    """Process PDF/TXT files into ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    model = SentenceTransformer(embed_model)

    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        content = ""

        if filename.endswith(".pdf"):
            reader = PdfReader(path)
            content = " ".join([
                page.extract_text()
                for page in reader.pages
                if page.extract_text()
            ])
        elif filename.endswith(".txt"):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

        if content:
            clean_content = clean_text(content)
            chunks = chunk_text(clean_content)

            if chunks:
                ids = [f"{filename}_{i}" for i in range(len(chunks))]
                metadatas = [{"source": filename} for _ in chunks]
                embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)

                collection.upsert(
                    documents=chunks,
                    ids=ids,
                    embeddings=embeddings.tolist(),
                    metadatas=metadatas
                )
```

### Two ChromaDB Collections

| Collection | Purpose | Content |
|------------|---------|---------|
| `disease_cases` | Ultrasound similarity search | Image-derived symptom embeddings |
| `medical_docs` | Reference document search | Medical literature, guidelines |

### Usage Modes

```bash
# Fast mode: smaller model, faster processing
python -m backend.scripts.process_files --mode fast

# Deep mode: larger model, better quality
python -m backend.scripts.process_files --mode deep
```

Configuration via `config.py`:
```python
EMBED_MODEL_FAST = "paraphrase-MiniLM-L6-v2"
EMBED_MODEL_DETAILED = "msmarco-distilbert-base-v4"
CHUNK_PRESET_FAST = {"size": 300, "overlap": 30}
CHUNK_PRESET_DETAILED = {"size": 500, "overlap": 50}
```

### Integration with Main Pipeline

Medical documents serve as **reference context**, not direct diagnosis input:

1. Doctor uploads ultrasound → MedGemma extracts symptoms
2. Symptoms queried against `disease_cases` collection
3. Top matches returned with reference to relevant medical docs
4. Doctor can browse supporting literature for each diagnosis

This keeps MedGemma's scope clean (symptoms only) while enriching results with curated medical knowledge.
