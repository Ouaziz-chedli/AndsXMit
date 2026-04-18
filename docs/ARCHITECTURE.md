# PrenatalAI Architecture Document

> Complete architectural reference for implementing PrenatalAI — AI-Powered Prenatal Disease Detection

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [AI Layer: MedGemma + Symptom Extraction](#ai-layer-medgemma--symptom-extraction)
4. [Data Layer: Per-Disease Vector Databases](#data-layer-per-disease-vector-databases)
5. [Aggregation Layer](#aggregation-layer)
6. [Two-Stage Inference Engine](#two-stage-inference-engine)
7. [API Design](#api-design)
8. [Data Models](#data-models)
9. [Project Structure](#project-structure)
10. [Technology Stack](#technology-stack)
11. [Security & Privacy](#security--privacy)
12. [Regulatory Considerations](#regulatory-considerations)

---

## System Overview

**PrenatalAI** is a non-invasive AI diagnostic platform that analyzes ultrasound images to detect prenatal diseases, reducing unnecessary invasive procedures (amniocentesis, CVS).

### Core Principle

- **AI scope is LIMITED**: MedGemma sees ONLY the ultrasound image
- **All contextual factors are ALGORITHMIC**: Age, genetics, history processed in aggregation layer

### Key Differentiators

1. **No model training required** — uses MedGemma + RAG
2. **Per-disease vector databases** with positive (diseased) + negative (healthy) examples
3. **Trimester-aware diagnosis** — symptoms weighted by when they manifest
4. **Community learning** — doctors contribute diagnosed/undiagnosed cases
5. **Two-stage inference** — fast (urgent) + comprehensive (background)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INPUT LAYER                                │
│   Ultrasound Image(s) + Current Trimester                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SYMPTOM EXTRACTION (MedGemma)                     │
│   AI Input: Ultrasound image ONLY                                     │
│   AI Output: Structured textual symptom description                   │
│   (Trimester context selects which vector DB to query)              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
            │  Disease A  │  │  Disease B  │  │  Disease N  │
            │  Vector DB  │  │  Vector DB  │  │  Vector DB  │
            │  ─────────  │  │  ─────────  │  │  ─────────  │
            │  • Images   │  │  • Images   │  │  • Images   │
            │  • Text Sx  │  │  • Text Sx  │  │  • Text Sx  │
            │  • Metadata │  │  • Metadata │  │  • Metadata │
            └─────────────┘  └─────────────┘  └─────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                     ┌───────────────────────────────┐
                     │      PARALLEL VECTOR SEARCH     │
                     │   Query ALL disease databases   │
                     │   Retrieve top-K similar       │
                     │   symptom patterns per disease  │
                     └───────────────────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────┐
                     │      AGGREGATION LAYER          │
                     │   • Trimester-specific weights │
                     │   • Patient context priors      │
                     │   • Symptom overlap handling    │
                     │   • Ponderated mean scoring     │
                     └───────────────────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────┐
                     │       DIAGNOSIS OUTPUT          │
                     │   ┌──────────┐ ┌──────────┐   │
                     │   │  FAST    │ │COMPREH.  │   │
                     │   │  TRACK   │ │  SCAN    │   │
                     │   │(immediate)│(background)│   │
                     │   └──────────┘ └──────────┘   │
                     └───────────────────────────────┘
```

---

## AI Layer: MedGemma + Symptom Extraction

### Responsibility

MedGemma is responsible for **symptom extraction ONLY** — converting ultrasound images into textual symptom descriptions.

### MedGemma Input/Output

```
Input: Ultrasound image (DICOM, JPEG, PNG)
Output: Structured symptom text description
```

### Example Output

```json
{
  "symptoms": [
    {
      "type": "nuchal_translucency",
      "value": "3.2mm",
      "assessment": "elevated",
      "normal_range": "1.5-2.5mm"
    },
    {
      "type": "nasal_bone",
      "value": "absent",
      "assessment": "anomalous"
    },
    {
      "type": "cardiac",
      "value": "AV canal defect",
      "assessment": "anomalous"
    }
  ],
  "overall": "Multiple markers consistent with chromosomal abnormality"
}
```

### Key Constraint

**MedGemma does NOT receive patient context** (age, genetics, history). It only sees the image. All contextual factors are processed algorithmically.

### Integration Options

```python
# Option 1: Local inference
from medgemma import MedGemma

model = MedGemma.load_local()
symptoms = model.extract_symptoms(image)

# Option 2: API call
import httpx
response = httpx.post("medgemma-api/analyze", files={"image": image_bytes})
symptoms = response.json()
```

---

## Data Layer: Per-Disease Vector Databases

### Structure

Each disease has its **own vector database** containing both positive and negative examples organized by trimester.

```
Per Disease Database (e.g., Down Syndrome):

├── 1st Trimester
│   ├── POSITIVE (Diseased)
│   │   ├── Image embeddings (confirmed Down Syndrome)
│   │   ├── Text: "NT 3.5mm, absent nasal bone, cardiac anomaly..."
│   │   └── Metadata: gestational_age, equipment, acquisition_params
│   └── NEGATIVE (Healthy/Normal)
│       ├── Image embeddings (confirmed healthy)
│       ├── Text: "Normal NT 1.8mm, nasal bone present, normal heart"
│       └── Metadata: gestational_age, equipment
│
├── 2nd Trimester
│   ├── POSITIVE (Diseased)
│   │   ├── Images (cardiac defects, short femur, duodenal atresia)
│   │   └── Text: Symptom descriptions
│   └── NEGATIVE (Healthy/Normal)
│       ├── Images (normal organ morphology)
│       └── Text: "Normal cardiac chambers, normal femur length"
│
└── 3rd Trimester
    ├── POSITIVE (Diseased)
    │   ├── Images (growth restriction, other late markers)
    │   └── Text: Symptom descriptions
    └── NEGATIVE (Healthy/Normal)
        ├── Images (normal growth, normal wellbeing)
        └── Text: "Normal growth parameters, normal placenta"
```

### Vector Database Technology

| Option | Pros | Cons |
|--------|------|------|
| **Qdrant** | Rust-based, high performance, filtering | Self-hosted |
| **ChromaDB** | Simple, embedded | Limited production scale |
| **Pinecone** | Managed, scalable | External, API cost |

**Recommendation for Hackaton**: ChromaDB (simple, local, works well for prototyping)

### Data Entry Schema

```python
class DiseaseCase(BaseModel):
    # Identification
    case_id: str
    disease_id: str
    trimester: Literal["1st", "2nd", "3rd"]
    label: Literal["positive", "negative"]  # positive=diseased, negative=healthy

    # Multi-modal data
    images: list[ImageData]  # Original + processed ultrasound images
    symptom_text: str        # Generated by MedGemma

    # Embeddings
    image_embedding: list[float]
    text_embedding: list[float]

    # Metadata
    gestational_age_weeks: int
    equipment_manufacturer: str | None
    acquisition_params: dict | None

    # Patient context (for PRIOR calculation - NOT sent to MedGemma)
    patient_context: PatientContext | None

    # Provenance
    source_institution: str
    diagnosing_physician: str
    confirmation_method: str  # clinical, genetic_testing, autopsy
    anonymized: bool

    # Timestamps
    created_at: datetime
    validated: bool
```

### Retrieval Query Schema

```python
class DiagnosisQuery(BaseModel):
    # Image data
    images: list[ImageData]

    # Context for ALGORITHMIC processing (NOT MedGemma)
    trimester: Literal["1st", "2nd", "3rd"]
    patient_context: PatientContext  # Age, genetics, history, etc.

    # Query parameters
    top_k: int = 10  # Results per disease
    include_normal: bool = True

class PatientContext(BaseModel):
    maternal_age: int
    paternal_age: int | None = None
    family_history: list[str] = []  # Disease IDs
    genetic_history: list[str] = []
    previous_pregnancies: list[PregnancyOutcome] = []
    ethnicity: str | None = None
    ivf_conception: bool = False
```

---

## Aggregation Layer

### Responsibility

Combines all signals into a final diagnosis probability using algorithmic processing (NOT AI).

### Inputs

```
1. Per-Disease Similarity Scores (from vector search)
   ├── Disease A: {positive_sim: 0.85, negative_sim: 0.30}
   ├── Disease B: {positive_sim: 0.60, negative_sim: 0.55}
   └── Disease N: ...

2. Trimester Context (ALGORITHMIC)
   └── Which trimester weight profile to apply

3. Patient Context - ALL ALGORITHMIC (Bayesian Priors)
   ├── Maternal age: 38 → multiplier for chromosomal
   ├── Family history: Down Syndrome → disease-specific boost
   ├── Genetic history: hereditary conditions
   ├── Previous pregnancies: outcome history
   ├── Ethnicity: population-based priors
   └── IVF/Conception method
```

### Step-by-Step Aggregation

#### Step 1: Per-Disease Raw Score

```python
def calculate_raw_score(positive_sims: list[float], negative_sims: list[float]) -> float:
    """
    score = avg(positive_similarities) - avg(negative_similarities)
    """
    pos_mean = mean(positive_sims)
    neg_mean = mean(negative_sims)
    return pos_mean - neg_mean

# Example:
# positive_sims = [0.85, 0.78, 0.82]
# negative_sims = [0.30, 0.25, 0.35]
# raw_score = 0.82 - 0.30 = 0.52
```

#### Step 2: Apply Trimester Weights

```python
TRIMESTER_WEIGHTS = {
    "1st": {
        "down_syndrome": 0.85,
        "edwards_syndrome": 0.80,
        "patau_syndrome": 0.75,
        "cardiac_defect": 0.50,
        # ...
    },
    "2nd": {
        "down_syndrome": 0.75,
        "edwards_syndrome": 0.85,
        "patau_syndrome": 0.80,
        "cardiac_defect": 0.90,
        # ...
    },
    "3rd": {
        "down_syndrome": 0.40,
        "edwards_syndrome": 0.50,
        "patau_syndrome": 0.45,
        "cardiac_defect": 0.60,
        # ...
    }
}

def apply_trimester_weight(raw_score: float, disease: str, trimester: str) -> float:
    weight = TRIMESTER_WEIGHTS[trimester][disease]
    return raw_score * weight
```

#### Step 3: Apply Patient Context Priors (Bayesian)

```python
PRIOR_MULTIPLIERS = {
    "maternal_age_35_plus": {"chromosomal": 1.5, "cardiac": 1.1},
    "maternal_age_40_plus": {"chromosomal": 2.0, "cardiac": 1.2},
    "family_history": {"specific_disease": 2.5, "chromosomal": 1.8},
    "previous_chromosomal": {"chromosomal": 1.8},
    "ivf": {"chromosomal": 1.3, "cardiac": 1.1}
}

def apply_priors(weighted_score: float, disease: str, context: PatientContext) -> float:
    multiplier = 1.0

    if context.maternal_age >= 40:
        multiplier *= PRIOR_MULTIPLIERS["maternal_age_40_plus"].get(disease, 1.0)
    elif context.maternal_age >= 35:
        multiplier *= PRIOR_MULTIPLIERS["maternal_age_35_plus"].get(disease, 1.0)

    if disease in context.family_history:
        multiplier *= PRIOR_MULTIPLIERS["family_history"].get(disease, 1.5)

    return weighted_score * multiplier
```

#### Step 4: Symptom Overlap Handling

```python
# When one symptom suggests multiple diseases
# Score distributed proportionally

SYMPTOM_DISEASE_WEIGHTS = {
    "cardiac_AV_canal_defect": {
        "down_syndrome": 0.80,
        "avsd": 0.90,
        "noonan_syndrome": 0.60
    },
    "short_femur": {
        "down_syndrome": 0.60,
        "skeletal_dysplasia": 0.70
    }
}

def distribute_overlap(disease_scores: dict[str, float], detected_symptoms: list[str]) -> dict[str, float]:
    """Distribute scores for overlapping symptoms."""
    overlap_adjustments = defaultdict(float)

    for symptom in detected_symptoms:
        if symptom in SYMPTOM_DISEASE_WEIGHTS:
            weights = SYMPTOM_DISEASE_WEIGHTS[symptom]
            total_weight = sum(weights.values())

            for disease, weight in weights.items():
                proportion = weight / total_weight
                overlap_adjustments[disease] += disease_scores.get(disease, 0) * proportion * 0.1

    # Apply adjustments
    for disease, adjustment in overlap_adjustments.items():
        if disease in disease_scores:
            disease_scores[disease] += adjustment

    return disease_scores
```

### Final Output

```python
class DiagnosisResult(BaseModel):
    disease_id: str
    disease_name: str

    # Score breakdown
    raw_score: float
    trimester_weight: float
    prior_multiplier: float
    final_score: float

    # Explanation
    matching_positive_cases: list[RetrievedCase]
    matching_negative_cases: list[RetrievedCase]
    applied_priors: list[str]  # ["maternal_age_38", "family_history_ds"]

    # Confidence
    confidence_interval: tuple[float, float]  # [lower, upper]
    uncertainty_category: Literal["high", "medium", "low"]

class DiagnosisReport(BaseModel):
    # Two-stage results
    fast_track: list[DiagnosisResult]  # Top 5, synchronous
    comprehensive: list[DiagnosisResult] | None  # All diseases, async

    # Processing info
    fast_track_ms: int
    comprehensive_pending: bool
    comprehensive_callback_url: str | None

    # Metadata
    model_version: str
    database_version: str
    timestamp: datetime
```

---

## Two-Stage Inference Engine

### Stage 1: Fast Track (Synchronous)

- **Trigger**: Image upload
- **Scope**: Top 5 most probable diseases
- **Latency target**: < 1 second
- **Process**:
  1. MedGemma extracts symptoms
  2. Query top-K from all disease DBs
  3. Aggregate with current priors
  4. Return top 5

### Stage 2: Comprehensive Scan (Background/Async)

- **Trigger**: After fast track completes
- **Scope**: ALL diseases in knowledge base
- **Latency**: Seconds to minutes (depending on DB size)
- **Process**:
  1. Query full disease DBs
  2. Aggregate all disease scores
  3. Store results
  4. Callback/push to doctor when complete

```python
@router.post("/diagnosis")
async def diagnose(
    images: list[UploadFile],
    trimester: Literal["1st", "2nd", "3rd"],
    patient_context: PatientContext
):
    # Stage 1: Fast track
    fast_result = await run_fast_track(images, trimester, patient_context)

    # Stage 2: Comprehensive (background)
    task = await run_comprehensive_background(images, trimester, patient_context)

    return {
        "fast_track": fast_result,
        "comprehensive_pending": True,
        "comprehensive_callback_url": f"/diagnosis/{task.id}/complete"
    }
```

---

## API Design

### Endpoints

#### Diagnosis

```
POST /api/v1/diagnosis
  - Body: multipart/form-data (images) + patient_context (JSON)
  - Response: Fast track results + comprehensive callback URL

GET /api/v1/diagnosis/{id}/comprehensive
  - Response: Comprehensive scan results (if ready)
```

#### Case Upload (Community)

```
POST /api/v1/cases
  - Body: case data + images + diagnosis
  - Auth: Requires doctor/institution verification

GET /api/v1/cases (admin)
  - Query: disease, trimester, validated, pending
  - Response: Paginated case list for validation
```

#### Vector Database Management

```
POST /api/v1/vector/search
  - Body: {query_embedding, disease_ids, trimester, top_k}
  - Response: Similar cases

POST /api/v1/vector/index
  - Body: Case data with embeddings
  - Auth: Internal only
```

#### Reference Data

```
GET /api/v1/diseases
  - Response: List of supported diseases with trimester weights

GET /api/v1/diseases/{id}/weights
  - Response: Trimester-specific symptom weights

GET /api/v1/priors
  - Response: Current prior multipliers
```

### Request/Response Examples

#### Diagnosis Request

```bash
POST /api/v1/diagnosis
Content-Type: multipart/form-data

file: ultrasound_1.jpg
file: ultrasound_2.jpg

--_form_data--
{
  "trimester": "1st",
  "patient_context": {
    "maternal_age": 38,
    "paternal_age": 42,
    "family_history": ["down_syndrome"],
    "ethnicity": "european",
    "ivf_conception": false
  }
}
```

#### Diagnosis Response

```json
{
  "fast_track": [
    {
      "disease_id": "down_syndrome",
      "disease_name": "Down Syndrome (Trisomy 21)",
      "final_score": 0.72,
      "confidence_interval": [0.65, 0.79],
      "matching_positive_cases": [
        {"case_id": "...", "similarity": 0.85}
      ],
      "matching_negative_cases": [
        {"case_id": "...", "similarity": 0.30}
      ],
      "applied_priors": ["maternal_age_38", "family_history_ds"]
    }
  ],
  "comprehensive_pending": true,
  "comprehensive_callback_url": "/api/v1/diagnosis/abc123/comprehensive"
}
```

---

## Data Models

### Core Entities

```python
# Disease
class Disease(BaseModel):
    disease_id: str
    name: str
    description: str
    trimester_profiles: dict[str, TrimesterProfile]
    base_prevalence: float  # Per 10,000 births

class TrimesterProfile(BaseModel):
    trimester: str
    symptom_weights: dict[str, float]
    normal_ranges: dict[str, tuple[float, float]]

# Case (Community Contribution)
class CommunityCase(BaseModel):
    case_id: str
    disease_id: str | None  # None if undiagnosed
    trimester_when_captured: str
    images: list[str]  # S3 URLs or local paths
    symptom_text: str
    patient_context: PatientContext
    outcome: Literal["born_healthy", "born_with_disease", "terminated", "unknown"]
    validated: bool
    contributor_id: str
    created_at: datetime

# Doctor/Institution
class Contributor(BaseModel):
    contributor_id: str
    institution: str
    specialty: str
    license_verified: bool
    contribution_count: int
    validation_status: Literal["pending", "approved", "rejected"]
```

---

## Project Structure

```
prenatal-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis.py      # Diagnosis endpoints
│   │   │   ├── cases.py         # Community case upload
│   │   │   ├── diseases.py      # Reference data
│   │   │   └── vector.py        # Vector DB operations
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── medgemma.py       # MedGemma integration
│   │   │   ├── vector_store.py   # Vector DB abstraction
│   │   │   ├── aggregation.py    # Aggregation logic
│   │   │   ├── priors.py         # Bayesian prior calculations
│   │   │   └── scoring.py        # Scoring engine
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis.py      # Diagnosis request/response
│   │   │   ├── case.py          # Community case models
│   │   │   ├── disease.py        # Disease reference
│   │   │   └── patient.py        # Patient context
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py        # PostgreSQL connection
│   │   │   ├── repositories.py  # Data access
│   │   │   └── s3.py            # S3 for images
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── diagnosis.py       # Diagnosis orchestration
│   │   │   ├── case_upload.py    # Case upload processing
│   │   │   └── validation.py     # Case validation
│   │   │
│   │   ├── config.py             # Settings
│   │   └── main.py              # FastAPI app
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_aggregation.py
│   │   ├── test_medgemma.py
│   │   ├── test_api.py
│   │   └── test_integration.py
│   │
│   ├── scripts/
│   │   ├── seed_diseases.py     # Initialize disease data
│   │   ├── seed_mock_data.py    # Mock cases for testing
│   │   └── compute_embeddings.py # Pre-compute embeddings
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Home/dashboard
│   │   ├── diagnosis/
│   │   │   └── page.tsx         # Diagnosis interface
│   │   ├── upload/
│   │   │   └── page.tsx         # Case upload
│   │   └── layout.tsx
│   ├── components/
│   │   ├── DiagnosisForm.tsx
│   │   ├── DiagnosisResults.tsx
│   │   ├── CaseUploadForm.tsx
│   │   └── SimilarCases.tsx
│   ├── lib/
│   │   ├── api.ts               # API client
│   │   └── utils.ts
│   ├── package.json
│   └── tailwind.config.ts
│
├── vector_data/                  # Local vector DB (dev)
│   ├── down_syndrome/
│   ├── cardiac_defect/
│   └── ...
│
├── data/                         # Mock/seeds
│   ├── diseases.json
│   ├── trimester_weights.json
│   ├── priors_config.json
│   └── sample_images/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── DEPLOYMENT.md
│
├── README.md
├── requirements.txt
└── docker-compose.yml
```

---

## Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Framework** | FastAPI | 0.128+ | API layer |
| **Runtime** | Python | 3.11+ | Backend |
| **Validation** | Pydantic | v2 | Data models |
| **DB ORM** | SQLAlchemy | 2.0 | Database |
| **DB** | PostgreSQL | 15+ | Metadata storage |
| **Object Storage** | S3/MinIO | - | Image storage |
| **Vector DB** | ChromaDB | latest | Vector storage |
| **Embedding** | MedGemma/BiomedCLIP | - | Multi-modal embeddings |
| **AI** | MedGemma | latest | Symptom extraction |
| **Task Queue** | Celery/Redis | - | Async comprehensive scan |
| **Caching** | Redis | 7+ | Session/cache |

### Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Framework** | Next.js 14+ | React framework |
| **Language** | TypeScript | Type safety |
| **Styling** | Tailwind CSS | Styling |
| **State** | React Query | Server state |
| **Forms** | React Hook Form | Form handling |
| **UI** | shadcn/ui | Components |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Container** | Docker | Containerization |
| **Orchestration** | docker-compose | Local dev |
| **Cloud** | TBD | Production deployment |

---

## Security & Privacy

### Data Anonymization

```python
class Anonymizer:
    """Remove PII before any storage or transmission."""

    def anonymize(self, case: CommunityCase) -> CommunityCase:
        return case.model_copy(update={
            "patient_context": PatientContext(
                # Keep only medical relevant fields
                maternal_age=randomize_age(case.patient_context.maternal_age),
                # Remove: names, addresses, IDs, contact info
            )
        })
```

### Privacy Architecture

1. **Local Processing Option**: MedGemma can run on-premise
2. **Anonymization**: Patient data stripped before any external transmission
3. **Consent**: Explicit consent for community contributions
4. **Audit**: Full audit trail of all data access
5. **GDPR Compliance**: Right to deletion, data portability

### Security Requirements

- All API endpoints require authentication
- Role-based access (doctor, institution_admin, system_admin)
- Image data encrypted at rest (S3 SSE)
- Vector DB access logged and monitored
- Regular security audits

---

## Regulatory Considerations

### Medical Device Classification

**Software as Medical Device (SaMD)** for EU (CE) and US (FDA).

| Market | Classification | Pathway |
|--------|----------------|---------|
| **EU** | Class IIa or IIb (MDR) | Technical documentation + clinical evaluation |
| **US** | Class II | 510(k) or De Novo |

### Key Requirements

1. **Clinical Validation**: Demonstrate safety and performance
2. **Quality System**: ISO 13485 compliant development process
3. **Post-Market Surveillance**: Ongoing monitoring and reporting
4. **Incident Reporting**: Adverse event reporting to regulatory bodies

### Data Requirements

| Requirement | Description |
|------------|-------------|
| **Clinical Studies** | Validate sensitivity/specificity against gold standard |
| **Training Data** | Large, diverse, representative dataset |
| **Validation Data** | Independent test set |
| **Post-Market Data** | Real-world performance monitoring |

### Documentation Requirements

- Intended use statement
- Technical file (design, development, testing)
- Clinical evaluation report
- Risk management file
- User manual / instructions for use

---

## Implementation Priorities

### Hackaton MVP

1. **Core Pipeline**
   - MedGemma integration (symptom extraction)
   - Single disease vector DB (Down Syndrome as proof of concept)
   - Basic aggregation with trimester weights
   - Simple API endpoints

2. **UI**
   - Image upload form
   - Basic results display

3. **Data**
   - Mock cases for Down Syndrome (positive + negative)
   - 1st trimester examples

### Post-Hackaton

1. **Additional Diseases**: Expand vector DBs
2. **All Trimesters**: Complete coverage
3. **Patient Context**: Full prior implementation
4. **Community Features**: Case upload and validation
5. **Comprehensive Scan**: Async background processing

### Production Path

1. **Clinical Validation**: Partner with hospitals
2. **Regulatory Filing**: CE marking / FDA 510(k)
3. **Scaling**: Cloud infrastructure
4. **Community Growth**: Doctor network expansion

---

## Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation — AI pattern using vector search + LLM |
| **Vector DB** | Database storing embeddings for similarity search |
| **Embedding** | Numeric vector representation of image/text |
| **MedGemma** | Google's medical vision-language AI model |
| **Trimester** | 3-month period of pregnancy (1st: 0-13w, 2nd: 14-26w, 3rd: 27w+) |
| **NT** | Nuchal Translucency — ultrasound measurement at 1st trimester |
| **Bayesian Prior** | Probability factor based on patient context |
| **False Negative** | Disease missed by screening |
| **False Positive** | Healthy flagged as diseased |
| **Sensitivity** | Ability to correctly identify disease |
| **Specificity** | Ability to correctly identify healthy |

---

*Document Version: 1.0*
*Last Updated: 2026-04-18*
*Project: PrenatalAI — AndsXMit Hackaton*
