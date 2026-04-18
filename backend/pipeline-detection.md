# PrenatalAI Detection Pipeline

The PrenatalAI diagnosis follows a **7-step pipeline** that transforms an ultrasound image into a disease probability score.

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────┐
│ 1. IMAGE PROCESSING                                       │
│    load_ultrasound_image()                                │
│    - Reads DICOM/JPEG/PNG                                  │
│    - Extracts metadata (gestational age, trimester)        │
│    - Converts to PIL Image → PNG bytes                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MEDGEMMA (Symptom Extraction)                         │
│    medgemma.extract_symptoms()                            │
│    - Sends image to Ollama running MedGemma                 │
│    - AI returns structured JSON:                          │
│      {symptoms: [{type, value, assessment}], overall}      │
│    - Falls back to mock if Ollama unavailable            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. EMBEDDING (Vector Search Prep)                        │
│    medgemma.embed_symptoms()                              │
│    - Converts symptom text → 768-dim vector              │
│    - Used for ChromaDB similarity search                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VECTOR STORE (Case Retrieval)                         │
│    vector_store.search_disease()                           │
│    - Searches ChromaDB for similar cases                 │
│    - Returns:                                           │
│      • top-K positive cases (diseased)                   │
│      • top-K negative cases (healthy)                    │
│    - Per disease (down_syndrome, edwards_syndrome, etc.) │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. SCORING (Raw Score Calculation)                        │
│    calculate_raw_score()                                  │
│    Formula:                                               │
│    score = avg(positive_sims) - avg(negative_sims)       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. AGGREGATION (Trimester Weighting)                      │
│    aggregate_scores()                                     │
│    Formula:                                               │
│    weighted = raw_score × trimester_weight                │
│                                                             │
│    Example weights (Down Syndrome):                        │
│    • 1st trimester: 0.85 (most predictive)              │
│    • 2nd trimester: 0.75                                 │
│    • 3rd trimester: 0.40                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. PRIORS (Bayesian Patient Context)                     │
│    apply_priors()                                        │
│    Formula:                                               │
│    final = weighted × prior_multiplier                   │
│                                                             │
│    Priors applied:                                        │
│    • Maternal age ≥35 → ~5x for chromosomal diseases     │
│    • High b-hCG + Low PAPP-A → classic Down pattern      │
│    • Previous affected pregnancy → 2.5x                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │     RESULT      │
                   │ DiagnosisResult │
                   │ • disease_id    │
                   │ • final_score   │
                   │ • confidence    │
                   │ • applied_priors│
                   └─────────────────┘
```

## Step Details

### 1. Image Processing

**Module:** `app/core/image_processor.py`

```python
from app.core.image_processor import load_ultrasound_image

image, metadata = load_ultrasound_image("ultrasound.dcm")
# metadata.trimester → "1st", "2nd", or "3rd"
# metadata.gestational_age_weeks → float
```

Supports:
- **DICOM** (~90% of clinical ultrasound)
- **JPEG** (exports, consumer devices)
- **PNG** (reports, secondary use)

### 2. MedGemma Symptom Extraction

**Module:** `app/core/medgemma.py`

```python
from app.core.medgemma import get_medgemma

medgemma = get_medgemma()
symptoms = medgemma.extract_symptoms("ultrasound.png", trimester="1st")
# Returns SymptomDescription with structured symptoms
```

**Output:**
```json
{
  "symptoms": [
    {"type": "nuchal_translucency", "value": "3.2mm", "assessment": "elevated"},
    {"type": "nasal_bone", "value": "absent", "assessment": "anomalous"}
  ],
  "overall": "Abnormal first-trimester markers present"
}
```

**Integration:** Uses Ollama (`app/core/ollama_client.py`) to run MedGemma locally. Falls back to mock mode when Ollama is unavailable.

### 3. Embedding Generation

**Module:** `app/core/medgemma.py`

```python
embedding = medgemma.embed_symptoms("nuchal_translucency=3.2mm, nasal_bone=absent")
# Returns 768-dimensional vector
```

Used for ChromaDB similarity search.

### 4. Vector Store Retrieval

**Module:** `app/core/vector_store.py`

```python
from app.core.vector_store import get_vector_store

vector_store = get_vector_store()
positive_cases = vector_store.search_disease(
    query_embedding=embedding,
    disease_id="down_syndrome",
    trimester="1st",
    filter_positive=True,
    top_k=10
)
negative_cases = vector_store.search_disease(
    query_embedding=embedding,
    disease_id="down_syndrome",
    trimester="1st",
    filter_positive=False,
    top_k=10
)
```

**ChromaDB Collections:** One per disease per trimester (e.g., `down_syndrome_1st`)

### 5. Raw Score Calculation

**Module:** `app/core/scoring.py`

```python
from app.core.scoring import calculate_raw_score

raw_score = calculate_raw_score(
    positive_sims=[0.82, 0.78, 0.85],
    negative_sims=[0.25, 0.30, 0.28]
)
# raw_score = mean([0.82, 0.78, 0.85]) - mean([0.25, 0.30, 0.28])
# raw_score = 0.817 - 0.277 = 0.54
```

### 6. Trimester Aggregation

**Module:** `app/core/aggregation.py`

```python
from app.core.aggregation import aggregate_scores

weighted_score = aggregate_scores(
    raw_score=0.54,
    disease="down_syndrome",
    trimester="1st"
)
# weighted_score = 0.54 × 0.85 = 0.459
```

**Trimester Weights (Down Syndrome):**
| Trimester | Weight | Rationale |
|-----------|--------|----------|
| 1st | 0.85 | NT most predictive |
| 2nd | 0.75 | Morphology scan |
| 3rd | 0.40 | Growth restriction |

### 7. Bayesian Priors

**Module:** `app/core/priors.py`

```python
from app.core.priors import apply_priors
from app.models.patient import PatientContext

context = PatientContext(
    mother_age=38,
    b_hcg=85000,  # High
    papp_a=600,    # Low
    gestational_age_weeks=12.0,
    previous_affected_pregnancy=False
)

final_score = apply_priors(
    weighted_score=0.459,
    disease="down_syndrome",
    context=context
)
# Age risk: 1.45
# Biomarker risk: 1.8 (classic pattern)
# final = 0.459 × 1.45 × 1.8 = 1.2 (capped at 1.0)
```

**Prior Multipliers:**
| Factor | Multiplier |
|--------|------------|
| Maternal age 35 | ~1.5x |
| Maternal age 40 | ~5.0x |
| High b-hCG + Low PAPP-A | 1.8x |
| Previous affected pregnancy | 2.5x |

## API Entry Point

**Endpoint:** `POST /api/v1/diagnosis`

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
      "applied_priors": ["maternal_age_35", "biomarker_pattern_ds"]
    }
  ],
  "comprehensive_pending": true,
  "fast_track_ms": 150
}
```

### Two Output Paths

| Mode | Scope | Latency | Use Case |
|------|-------|---------|----------|
| **Fast Track** | Top 5 diseases | < 1 second | Immediate ruling out |
| **Comprehensive** | All diseases | Background (async) | Thorough screening |

## Key Principle

> **MedGemma sees ONLY the ultrasound image.** All patient context (age, genetics, biomarkers) is processed **algorithmically** in the priors module — NOT by the AI model.

## File Structure

```
backend/app/
├── core/
│   ├── image_processor.py    # Step 1: DICOM/JPEG/PNG loading
│   ├── medgemma.py            # Steps 2-3: Symptom extraction + embedding
│   ├── ollama_client.py       # Ollama REST API client
│   ├── vector_store.py         # Step 4: ChromaDB similarity search
│   ├── scoring.py             # Step 5: Raw score calculation
│   ├── aggregation.py          # Step 6: Trimester weighting
│   └── priors.py              # Step 7: Bayesian priors
├── services/
│   └── diagnosis.py           # Orchestration layer
└── models/
    ├── diagnosis.py           # DiagnosisResult, DiagnosisQuery
    └── patient.py             # PatientContext, PatientContextMoM
```

## Complete Scoring Formula

```
final_score = (avg(positive_similarities) - avg(negative_similarities))
               × trimester_weight
               × age_risk
               × biomarker_risk
               × previous_affected_pregnancy
```

Where:
- `avg(positive_similarities)` = mean similarity to top-K confirmed diseased cases
- `avg(negative_similarities)` = mean similarity to top-K confirmed healthy cases
- `trimester_weight` = disease/trimester-specific weight (0.40-0.90)
- `age_risk` = maternal age multiplier (1.0-5.0)
- `biomarker_risk` = b-hCG/PAPP-A pattern multiplier (1.0-1.8)
- `previous_affected_pregnancy` = 1.0 or 2.5
