# Dev 1 — AI/ML Pipeline

**Owns**: image → MedGemma symptom extraction → ChromaDB vector search → scored results

> UI/UX and Marketing are handled by a separate team.

---

## Core Constraint: Fully Self-Hostable

The hackathon app must run entirely on a hospital's own machine — no cloud, no external APIs, no managed services. A doctor should be able to run `docker compose up` and have everything working offline.

Complexity is only justified when it directly serves this goal. If a simpler tool does the job, use it.

### Stack Decisions (Relevant to Dev 1)

| Need | Simple choice | Ruled out |
|------|--------------|-----------|
| Vector storage | **ChromaDB embedded** (`PersistentClient`, writes to disk) | ChromaDB server container |
| AI inference | **MedGemma local** (mandatory) | MedGemma API — breaks self-hosting |
 
### Target Deployment

```
docker compose up
```

Runs a **single container** with everything inside it. Dev 2 handles Docker; Dev 1 focuses on:
- MedGemma weights (mounted or pulled on first start into `/data/models`)
- ChromaDB embedded (persists to `/data/vector_db` volume)

---

## Phase 1: Foundation (define first — Dev 2 depends on these models)

### Pydantic Models (agree with Dev 2 Day 1)

Place in `backend/app/models/` — these are the shared contract:

```python
# backend/app/models/diagnosis.py
class DiagnosisQuery(BaseModel):
    images: list[ImageData]
    trimester: Literal["1st", "2nd", "3rd"]
    patient_context: PatientContext

class PatientContext(BaseModel):
    """
    First-trimester screening context.
    Based on French NT-prenatal screening protocol (11-14 weeks).

    Key biomarkers:
    - b-hCG (IU/L) - beta human chorionic gonadotropin
    - PAPP-A (IU/L) - Pregnancy-associated plasma protein A
    - Mother age at due date
    - Gestational age in weeks (from CRL or exam date)
    """
    b_hcg: float | None = None          # IU/L, serum biomarker
    papp_a: float | None = None          # IU/L, serum biomarker
    mother_age: int                       # Age at due date
    gestational_age_weeks: float           # Weeks since LMP/conception
    # Optional modifiers
    previous_affected_pregnancy: bool = False  # Prior chromosomal anomaly

    def to_mom(self) -> "PatientContextMoM":
        """
        Convert raw values to MoM (Multiple of Median).
        MoM normalizes for gestational age and gives population-relative values.
        """
        # Median values at 10 weeks (typical first-trimester screening timing)
        MEDIAN_B_HCG = 50000.0  # IU/L
        MEDIAN_PAPP_A = 1500.0  # IU/L
        return PatientContextMoM(
            b_hcg_mom=self.b_hcg / MEDIAN_B_HCG if self.b_hcg else None,
            papp_a_mom=self.papp_a / MEDIAN_PAPP_A if self.papp_a else None,
            mother_age=self.mother_age,
            gestational_age_weeks=self.gestational_age_weeks,
            previous_affected_pregnancy=self.previous_affected_pregnancy,
        )

class PatientContextMoM(BaseModel):
    """
    MoM-normalized patient context for risk calculation.
    Using Multiple of Median removes gestational age dependency from biomarkers.
    """
    b_hcg_mom: float | None = None
    papp_a_mom: float | None = None
    mother_age: int
    gestational_age_weeks: float
    previous_affected_pregnancy: bool = False


class DiagnosisResult(BaseModel):
    disease_id: str
    disease_name: str
    final_score: float
    confidence_interval: tuple[float, float]
    applied_priors: list[str]

class DiseaseCase(BaseModel):
    case_id: str
    disease_id: str
    trimester: Literal["1st", "2nd", "3rd"]
    label: Literal["positive", "negative"]
    symptom_text: str
    gestational_age_weeks: float
    # Stored as MoM for consistent matching
    b_hcg_mom: float | None = None
    papp_a_mom: float | None = None
```

### Core Modules

- `backend/app/core/medgemma.py` — local MedGemma inference only (no API fallback)
- `backend/app/core/vector_store.py` — ChromaDB `PersistentClient` abstraction

```python
# backend/app/core/medgemma.py
async def extract_symptoms(image_bytes: bytes) -> SymptomDescription: ...
```

```python
# backend/app/core/vector_store.py
async def search_disease(
    query_embedding: list[float],
    disease_id: str,
    trimester: str,
    top_k: int
) -> list[RetrievedCase]: ...
```

---

## Phase 2: Core Engine

### `backend/app/core/scoring.py`

```python
def calculate_raw_score(positive_sims: list[float], negative_sims: list[float]) -> float:
    """
    score = avg(positive_similarities) - avg(negative_similarities)
    """
    return mean(positive_sims) - mean(negative_sims)
```

### `backend/app/core/aggregation.py`

Trimester weighting + symptom overlap distribution:

```python
TRIMESTER_WEIGHTS = {
    "1st": {"down_syndrome": 0.85, "cardiac_defect": 0.50, ...},
    "2nd": {"down_syndrome": 0.75, "cardiac_defect": 0.90, ...},
    "3rd": {"down_syndrome": 0.40, "cardiac_defect": 0.60, ...},
}

def aggregate_scores(raw_score: float, disease: str, trimester: str) -> float:
    return raw_score * TRIMESTER_WEIGHTS[trimester][disease]
```

### `backend/app/core/priors.py`

Biomarker-based prior calculation using MoM values:

```python
"""
First-trimester chromosomal risk priors based on biomarkers and maternal age.
Based on French NT-prenatal screening protocol.

Key insight: b-hCG and PAPP-A MoM values indicate chromosomal risk:
- Low PAPP-A + High b-hCG → increased Down syndrome risk
- Both low → increased T18/T13 risk
"""

from scipy.stats import norm

# Population medians for risk calculation
MEDIAN_MOTHER_AGE_RISK = 37.0  # Age where risk starts increasing significantly
TRISOMY_21_BASE_RISK = 800      # 1 in 800 at maternal age 30

def calculate_age_risk(mother_age: int) -> float:
    """
    Calculate age-based prior risk for chromosomal abnormality.
    Risk doubles every 2.5 years after age 25.
    Returns: risk multiplier relative to baseline
    """
    if mother_age < 30:
        return 1.0
    # Approximation of maternal age risk curve
    # Risk at 30: 1/800, at 35: 1/270, at 40: 1/100
    risk_factor = 800 / max(100, 800 - 10 * (mother_age - 30) ** 2)
    return min(risk_factor, 5.0)  # Cap at 5x

def calculate_biomarker_risk(
    b_hcg_mom: float | None,
    papp_a_mom: float | None,
) -> float:
    """
    Calculate biomarker-based risk modifier.
    Based on MoM values relative to expected medians.

    Typical patterns:
    - Down syndrome: b-hCG MoM elevated (~2.0), PAPP-A MoM low (~0.5)
    - Edwards (T18): both b-hCG and PAPP-A low
    - Patau (T13): both b-hCG and PAPP-A low
    """
    if b_hcg_mom is None and papp_a_mom is None:
        return 1.0

    risk = 1.0

    # b-hCG risk modifier
    if b_hcg_mom is not None:
        if b_hcg_mom > 2.0:
            # High b-hCG suggests Down syndrome
            risk *= 1.5
        elif b_hcg_mom < 0.25:
            # Very low b-hCG suggests T18/T13
            risk *= 1.3

    # PAPP-A risk modifier
    if papp_a_mom is not None:
        if papp_a_mom < 0.4:
            # Very low PAPP-A indicates high risk
            risk *= 2.0
        elif papp_a_mom < 0.5:
            risk *= 1.5
        elif papp_a_mom < 0.75:
            risk *= 1.2

    # Combined modifier for opposing patterns (high b-hcg + low papp_a)
    if b_hcg_mom and papp_a_mom:
        if b_hcg_mom > 1.5 and papp_a_mom < 0.6:
            # Classic Down syndrome pattern
            risk *= 1.8

    return risk

def apply_priors(
    weighted_score: float,
    disease: str,
    context: PatientContext | PatientContextMoM,
) -> float:
    """
    Apply all priors to get final disease probability modifier.

    For chromosomal diseases (Down, Edwards, Patau):
    - Maternal age is significant factor
    - b-hCG and PAPP-A MoM values indicate disease-specific patterns
    """
    multiplier = 1.0

    # Maternal age risk (significant for all chromosomal diseases)
    age_risk = calculate_age_risk(context.mother_age)
    if disease in ("down_syndrome", "edwards_syndrome", "patau_syndrome"):
        multiplier *= age_risk

    # Biomarker risk
    if isinstance(context, PatientContextMoM):
        biomarker_risk = calculate_biomarker_risk(context.b_hcg_mom, context.papp_a_mom)
    else:
        # Convert to MoM first
        mom_context = context.to_mom()
        biomarker_risk = calculate_biomarker_risk(mom_context.b_hcg_mom, mom_context.papp_a_mom)

    if disease in ("down_syndrome", "edwards_syndrome", "patau_syndrome"):
        multiplier *= biomarker_risk

    # IVF modifier (slight increase for chromosomal anomalies)
    if context.ivf_conception and disease in ("down_syndrome", "edwards_syndrome", "patau_syndrome"):
        multiplier *= 1.1

    # Previous affected pregnancy (significant risk factor)
    if context.previous_affected_pregnancy:
        multiplier *= 2.5

    return weighted_score * multiplier
```

---

## Phase 3: Data

### Seed Data Structure

```python
# data/diseases.json
{
    "down_syndrome": {
        "name": "Down Syndrome (Trisomy 21)",
        "base_prevalence": 1.0,  # Per 1000 births
        "trimester_profiles": {
            "1st": {
                "biomarker_pattern": {"b_hcg_mom": 2.0, "papp_a_mom": 0.5},
                "nt_cutoff_mm": 3.0
            }
        }
    }
}

# data/priors_config.json
{
    "median_b_hcg": 50000.0,
    "median_papp_a": 1500.0,
    "gestational_age_range": {"min": 11, "max": 14},
    "risk_factors": {
        "maternal_age_threshold": 35,
        "ivf_multiplier": 1.1,
        "previous_affected_multiplier": 2.5
    }
}
```

### `backend/scripts/seed_mock_data.py`

Mock positive + negative Down Syndrome cases with MoM-normalized biomarkers:

```python
# Example mock case (positive Down syndrome)
{
    "case_id": "ds_pos_001",
    "disease_id": "down_syndrome",
    "trimester": "1st",
    "label": "positive",
    "symptom_text": "nt_3_5mm absent_nasal_bone",
    "gestational_age_weeks": 12.0,
    "b_hcg_mom": 2.1,      # Elevated
    "papp_a_mom": 0.48,    # Low
}

# Example mock case (negative/healthy)
{
    "case_id": "norm_001",
    "disease_id": "down_syndrome",
    "trimester": "1st",
    "label": "negative",
    "symptom_text": "normal_nt_1_8mm nasal_bone_present",
    "gestational_age_weeks": 12.0,
    "b_hcg_mom": 1.0,      # Normal
    "papp_a_mom": 1.0,     # Normal
}
```

### `backend/scripts/compute_embeddings.py`

Pre-compute and load embeddings into ChromaDB.

---

## Phase 4: Tests

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
pydicom>=3.0.0     # DICOM file reading
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
    gestational_age_weeks: int | None
    trimester: Literal["1st", "2nd", "3rd"] | None
    acquisition_date: str | None
    patient_age: int | None
    study_description: str | None
    manufacturer: str | None

def load_ultrasound_image(filepath: str) -> tuple[Image.Image, UltrasoundMetadata]:
    ext = filepath.lower().split('.')[-1]
    if ext in ('dcm', 'dicom'):
        return _load_dicom(filepath)
    elif ext in ('jpg', 'jpeg', 'png'):
        return _load_conventional(filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")

def _load_dicom(filepath: str) -> tuple[Image.Image, UltrasoundMetadata]:
    ds = dcmread(filepath)
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

    pixel_array = ds.pixel_array
    if pixel_array.dtype != np.uint8:
        pixel_array = ((pixel_array - pixel_array.min()) /
                       (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
    image = Image.fromarray(pixel_array)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    return image, metadata

def _load_conventional(filepath: str) -> tuple[Image.Image, UltrasoundMetadata]:
    image = Image.open(filepath)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    metadata = UltrasoundMetadata(
        gestational_age_weeks=None, trimester=None,
        acquisition_date=None, patient_age=None,
        study_description=None, manufacturer=None,
    )
    return image, metadata

def _extract_gestational_age(ds: Dataset) -> int | None:
    for tag in ['GestationalAge', 'GestationalAgeSample', 'ClinicalTrialTimePoint']:
        if hasattr(ds, tag):
            try:
                return int(float(getattr(ds, tag)))
            except (ValueError, TypeError):
                continue
    return None

def _compute_trimester(gestational_age_weeks: int | None) -> Literal["1st", "2nd", "3rd"] | None:
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
    image, metadata = load_ultrasound_image(image_path)
    trimester = user_provided_trimester or metadata.trimester
    if trimester is None:
        raise ValueError("Trimester must be provided.")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    symptoms = medgemma.analyze(image_bytes.read())
    return SymptomDescription(
        symptoms=symptoms,
        trimester=trimester,
        gestational_age=metadata.gestational_age_weeks,
    )
```

### DICOM De-identification

Before storing DICOM in community database, strip PII:

```python
def anonymize_dicom(ds: Dataset) -> Dataset:
    pii_fields = [
        'PatientName', 'PatientID', 'PatientBirthDate',
        'PatientSex', 'PatientAddress', 'PatientTelephoneNumbers',
        'OtherPatientIDs', 'OtherPatientNames',
        'StudyDate', 'StudyTime',
    ]
    for field in pii_fields:
        if hasattr(ds, field):
            setattr(ds, field, None)
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    return ds
```

---

## Document Processing Pipeline

### Two Distinct Pipelines

| Data Type | Input | Processing | Embedding Model |
|-----------|-------|------------|-----------------|
| **Ultrasound images** | DICOM, JPEG, PNG | MedGemma → symptom text | Vision encoder |
| **Medical documents** | PDF, TXT | Chunk → embed | Sentence Transformers |

### Libraries

```
pypdf>=4.0.0          # PDF text extraction
sentence-transformers # Text embeddings
```

### Implementation

```python
# backend/app/core/document_processor.py

import re
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:].strip())
            break
        chunk = text[start:end]
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
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
    model = SentenceTransformer(embed_model)
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        content = ""
        if filename.endswith(".pdf"):
            reader = PdfReader(path)
            content = " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
        elif filename.endswith(".txt"):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        if content:
            chunks = chunk_text(clean_text(content))
            if chunks:
                ids = [f"{filename}_{i}" for i in range(len(chunks))]
                embeddings = model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)
                collection.upsert(documents=chunks, ids=ids, embeddings=embeddings.tolist(),
                               metadatas=[{"source": filename}] * len(chunks))
```

### Two ChromaDB Collections

| Collection | Purpose |
|------------|---------|
| `disease_cases` | Ultrasound similarity search |
| `medical_docs` | Reference document search |

### Usage Modes

```bash
python -m backend.scripts.process_files --mode fast   # Fast embedding
python -m backend.scripts.process_files --mode deep   # Detailed embedding
```

Configuration:
```python
EMBED_MODEL_FAST = "paraphrase-MiniLM-L6-v2"
EMBED_MODEL_DETAILED = "msmarco-distilbert-base-v4"
CHUNK_PRESET_FAST = {"size": 300, "overlap": 30}
CHUNK_PRESET_DETAILED = {"size": 500, "overlap": 50}
```

---

## MVP Priority

| Priority | Task |
|----------|------|
| 1 | MedGemma extracting symptoms from a sample image |
| 2 | ChromaDB seeded with mock Down Syndrome cases |
| 3 | Aggregation + scoring producing a ranked result |
| 4 | Biomarker priors (b-hCG, PAPP-A, maternal age) |

One disease (Down Syndrome), one trimester (1st), end-to-end, running offline via Docker.

### Biomarker Reference (from `docs/calcul probabilité.pdf`)

| Marker | Full Name | Normal Range (MoM) | Down Syndrome Pattern |
|--------|-----------|-------------------|---------------------|
| **b-hCG** | Beta human chorionic gonadotropin | ~1.0 MoM | Elevated (~2.0 MoM) |
| **PAPP-A** | Pregnancy-associated plasma protein A | ~1.0 MoM | Low (~0.5 MoM) |
| **NT** | Nuchal translucency | <3.0mm | Elevated (>3.0mm) |

MoM (Multiple of Median) normalizes values for gestational age.
