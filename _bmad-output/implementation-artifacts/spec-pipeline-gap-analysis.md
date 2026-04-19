---
status: done
title: Pipeline Implementation Gap Analysis
route: one-shot
created: 2026-04-19
---

# Pipeline Implementation Gap Analysis

## Intent

Compare the desired PrenatalAI diagnosis pipeline (from README.md and pipeline-detection.md) against the current implementation state.

---

## Desired Pipeline (from README.md)

```
1. Image Processing → load_ultrasound_image() [DICOM/JPEG/PNG]
2. MedGemma → Symptom Extraction [AI sees ONLY image]
3. Embedding → 768-dim vector [nomic-embed-text]
4. Vector Store → Per-disease ChromaDB retrieval
   - top-K positive (diseased) cases
   - top-K negative (healthy) cases
5. Scoring → avg(pos_sims) - avg(neg_sims)
6. Aggregation → Trimester weighting
7. Priors → Bayesian patient context
   - Maternal age
   - Biomarkers (b-hCG, PAPP-A)
   - Previous affected pregnancy
```

**Key Principle from README:** "MedGemma sees ONLY the ultrasound image. All contextual factors (age, genetics, history) are processed algorithmically in the aggregation layer, NOT by the AI model."

---

## Current Implementation State

### ✅ Step 1: Image Processing
- **File:** `backend/app/core/image_processor.py`
- **Status:** Complete
- **Supports:** DICOM, JPEG, PNG

### ✅ Step 2: MedGemma Symptom Extraction
- **File:** `backend/app/core/medgemma.py`
- **Status:** Complete
- **Uses:** Ollama with `medgemma` model
- **Note:** Inference slow (~20-40s per image)

### ✅ Step 3: Embedding Generation
- **File:** `backend/app/core/medgemma.py`, `app/core/ollama_client.py`
- **Status:** Complete
- **Model:** `nomic-embed-text` (installed)
- **Note:** Previously used hash fallback due to MedGemma embedding error

### ✅ Step 4: Vector Store
- **File:** `backend/app/core/vector_store.py`
- **Status:** Complete
- **Database:** ChromaDB
- **Cases seeded:** 71 total cases across 9 disease/trimester combinations
- **Note:** Re-seeded with `nomic-embed-text` embeddings (was using hash-based)

### ✅ Step 5: Scoring
- **File:** `backend/app/core/scoring.py`
- **Status:** Complete
- **Formula:** `avg(positive_sims) - avg(negative_sims)`

### ✅ Step 6: Aggregation (Trimester Weighting)
- **File:** `backend/app/core/aggregation.py`
- **Status:** Complete

### ✅ Step 7: Priors (Bayesian)
- **File:** `backend/app/core/priors.py`
- **Status:** Complete

### ✅ Orchestration Layer
- **File:** `backend/app/services/diagnosis.py`
- **Status:** Complete

### ✅ API Endpoint
- **File:** `backend/app/api/diagnosis.py`
- **Status:** Complete
- **Endpoint:** `POST /api/v1/diagnosis`

### ✅ RealTest Script
- **File:** `backend/tests/realtest.py`
- **Status:** Complete
- **Purpose:** End-to-end testing with real Ollama inference

---

## Scoring Formula (Implemented)

```
final_score = (avg(positive_similarities) - avg(negative_similarities))
               × trimester_weight
               × age_risk_multiplier
               × biomarker_risk_multiplier
               × previous_affected_multiplier
```

**Matches README exactly** ✅

---

## Test Results

### RealTest Output (Normal Image)

| Metric | Value |
|--------|-------|
| Symptom extraction | 42.0s |
| Embedding | 0.72s |
| Full pipeline (6 diseases) | 225.7s |

### Extracted Symptoms (Normal 2nd Trimester)
- `cardiac: normal_four_chamber (normal)` [conf: 0.94]
- `femur_length: 45mm (normal)` [conf: 0.91]

### Diagnosis Scores
| Disease | Score | Interpretation |
|---------|-------|-----------------|
| Skeletal Dysplasia | -0.0049 | Low risk (normal) |
| Edwards Syndrome | -0.0053 | Low risk (normal) |
| Patau Syndrome | -0.0418 | Low risk (normal) |
| Neural Tube Defect | -0.0511 | Low risk (normal) |
| Down Syndrome | -0.0556 | Low risk (normal) |
| Cardiac Defect | -0.0564 | Low risk (normal) |

**All negative = image looks more like healthy cases than diseased cases ✅**

---

## Gap Analysis Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Image Processing | ✅ Complete | DICOM/JPEG/PNG supported |
| MedGemma Integration | ✅ Complete | Uses Ollama |
| Embedding Model | ✅ Complete | Using `nomic-embed-text` |
| Vector Store | ✅ Complete | 71 cases seeded |
| Scoring | ✅ Complete | Matches formula |
| Aggregation | ✅ Complete | Trimester weights |
| Priors | ✅ Complete | Age, biomarkers, history |
| API | ✅ Complete | `POST /api/v1/diagnosis` |
| RealTest | ✅ Complete | E2E testing script |

**Conclusion: Pipeline is fully implemented and working.**