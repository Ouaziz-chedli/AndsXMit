# PrenatalAI Backend Reference

> AI-powered prenatal disease detection using MedGemma + RAG architecture.

## Overview

PrenatalAI uses a **no-training AI architecture** combining:
- **MedGemma** - Vision-language model for symptom extraction from ultrasound images
- **ChromaDB** - Vector database for similarity search against community cases
- **Algorithmic priors** - Patient context (age, biomarkers) processed mathematically, NOT by AI

**Key Principle**: MedGemma sees ONLY the ultrasound image. All patient context (age, genetics, biomarkers) is processed algorithmically.

---

## Quick Start

### Development Mode
```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Docker Mode
```bash
cd backend
docker build -t prenatal-ai .
docker compose up
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         INPUT                               │
│         Ultrasound Image + Patient Context                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SYMPTOM EXTRACTION (MedGemma)                   │
│              AI sees ONLY the image                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    VECTOR SEARCH                             │
│         ChromaDB - Per-disease similarity search             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AGGREGATION                             │
│         Trimester weights + Patient priors                   │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
    FAST TRACK                              COMPREHENSIVE
    (< 1 second)                            (background)
```

---

## API Endpoints

### Diagnosis

#### Submit Diagnosis
```
POST /api/v1/diagnosis
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | file | Yes | Ultrasound image(s) |
| `trimester` | string | Yes | `"1st"`, `"2nd"`, or `"3rd"` |
| `mother_age` | integer | Yes | Mother's age at due date |
| `gestational_age_weeks` | float | Yes | Weeks since LMP |
| `b_hcg` | float | No | Beta-hCG biomarker (IU/L) |
| `papp_a` | float | No | PAPP-A biomarker (IU/L) |
| `previous_affected_pregnancy` | boolean | No | Prior chromosomal anomaly |

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/diagnosis \
  -F "images=@ultrasound.jpg" \
  -F "trimester=1st" \
  -F "mother_age=35" \
  -F "gestational_age_weeks=12" \
  -F "b_hcg=55000" \
  -F "papp_a=1200"
```

**Response:**
```json
{
  "fast_track": [
    {
      "disease_id": "down_syndrome",
      "disease_name": "Down Syndrome (Trisomy 21)",
      "final_score": 0.65,
      "confidence_interval": [0.55, 0.75],
      "applied_priors": ["maternal_age_35", "biomarker_pattern_ds"],
      "matching_positive_cases": [{"case_id": "mock_ds_pos_001", "similarity": 0.82}],
      "matching_negative_cases": [{"case_id": "mock_neg_001", "similarity": 0.25}]
    }
  ],
  "comprehensive_pending": true,
  "comprehensive_callback_url": "/api/v1/diagnosis/task-abc123/comprehensive",
  "fast_track_ms": 150
}
```

#### Get Comprehensive Results
```
GET /api/v1/diagnosis/{task_id}/comprehensive
```

### Cases

#### Upload Case
```
POST /api/v1/cases
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | file | Yes | Case ultrasound images |
| `diagnosis` | string | Yes | Symptom text description |
| `trimester` | string | Yes | `"1st"`, `"2nd"`, `"3rd"` |
| `gestational_age_weeks` | float | Yes | Gestational age |
| `contributor_id` | string | Yes | Contributor ID |
| `disease_id` | string | No | Disease ID (if diagnosed) |
| `b_hcg_mom` | float | No | MoM-normalized b-hCG |
| `papp_a_mom` | float | No | MoM-normalized PAPP-A |

#### List Cases
```
GET /api/v1/cases?disease=down_syndrome&validated=true
```

### Diseases

#### List Diseases
```
GET /api/v1/diseases
```

#### Get Disease Weights
```
GET /api/v1/diseases/{disease_id}/weights
```

---

## Data Models

### PatientContext
```python
class PatientContext(BaseModel):
    b_hcg: float | None = None          # IU/L, serum biomarker
    papp_a: float | None = None          # IU/L, serum biomarker
    mother_age: int                        # Age at due date
    gestational_age_weeks: float            # Weeks since LMP
    previous_affected_pregnancy: bool = False  # Prior chromosomal anomaly
```

### DiagnosisResult
```python
class DiagnosisResult(BaseModel):
    disease_id: str
    disease_name: str
    final_score: float
    confidence_interval: tuple[float, float]
    applied_priors: list[str]
    matching_positive_cases: list[dict] = []
    matching_negative_cases: list[dict] = []
```

### CommunityCase (ORM)
```python
class CommunityCase(BaseModel):
    case_id: str
    disease_id: str | None
    trimester: str
    images: str  # JSON list of paths
    symptom_text: str
    gestational_age_weeks: float
    b_hcg_mom: float | None
    papp_a_mom: float | None
    validated: bool  # Requires admin validation
    contributor_id: str
```

---

## Scoring Algorithm

```
disease_score = (avg(positive_similarities) - avg(negative_similarities))
                 × trimester_weight
                 × prior_multiplier
```

### Trimester Weights (Down Syndrome Example)
| Trimester | Weight |
|-----------|--------|
| 1st | 0.85 |
| 2nd | 0.75 |
| 3rd | 0.40 |

### Prior Multipliers
| Factor | Multiplier |
|--------|------------|
| Maternal age ≥40 | ~5.0x (chromosomal) |
| Previous affected pregnancy | 2.5x |
| Classic Down biomarker pattern (high b-hCG + low PAPP-A) | 1.8x |

---

## Two Output Paths

| Mode | Scope | Latency | Use Case |
|------|-------|---------|----------|
| **Fast Track** | Top 5 diseases | < 1 second | Immediate ruling out |
| **Comprehensive** | All diseases | Background (async) | Thorough screening |

---

## File Structure

```
backend/app/
├── main.py                    # FastAPI application entry
├── config.py                  # Environment settings
├── api/
│   ├── diagnosis.py          # POST /api/v1/diagnosis
│   ├── cases.py              # POST/GET /api/v1/cases
│   └── diseases.py           # GET /api/v1/diseases
├── models/
│   ├── patient.py            # PatientContext, PatientContextMoM
│   ├── disease.py           # Disease, TrimesterProfile
│   ├── case.py              # DiseaseCase, ImageData
│   └── diagnosis.py         # DiagnosisResult, DiagnosisResponse
├── core/
│   ├── medgemma.py           # Symptom extraction (AI)
│   ├── vector_store.py       # ChromaDB wrapper
│   ├── scoring.py            # Raw score calculation
│   ├── aggregation.py        # Trimester weighting
│   ├── priors.py             # Bayesian priors
│   └── image_processor.py    # DICOM/JPEG/PNG handling
├── services/
│   ├── diagnosis.py          # DiagnosisService orchestration
│   ├── case_upload.py        # Case upload + vector storage
│   └── validation.py         # Admin validation
└── db/
    ├── database.py           # SQLAlchemy setup
    ├── models.py             # ORM models
    └── repositories.py       # Data access layer
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/data` | Base directory for all data |
| `DB_PATH` | `/data/db.sqlite` | SQLite database path |
| `CHROMA_PATH` | `/data/vector_db` | ChromaDB persistence path |
| `IMAGE_DIR` | `/data/images` | Uploaded image storage |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `medgemma` | Ollama model name |

---

## Data Storage

```
/data/
├── db.sqlite          # SQLite database (metadata)
├── vector_db/         # ChromaDB vector database
└── images/            # Uploaded ultrasound images
```

---

## Supported Diseases

| Disease ID | Name | Trimester Weights |
|------------|------|-------------------|
| `down_syndrome` | Down Syndrome (Trisomy 21) | 1st: 0.85, 2nd: 0.75, 3rd: 0.40 |
| `edwards_syndrome` | Edwards Syndrome (Trisomy 18) | 1st: 0.80, 2nd: 0.85, 3rd: 0.50 |
| `patau_syndrome` | Patau Syndrome (Trisomy 13) | 1st: 0.75, 2nd: 0.80, 3rd: 0.45 |

---

*Last updated: 2026-04-18*
