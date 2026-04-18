---
stepsCompleted: [1, 2]
inputDocuments:
  - /Users/chedli/Code/Hackaton/MitXAnds/README.md
workflowType: 'architecture'
project_name: 'PrenatalAI'
user_name: 'Chedli'
date: '2026-04-18'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

- AI-powered prenatal disease detection via ultrasound image analysis
- MedGemma-based symptom extraction (no model training required)
- Per-disease RAG vector databases with positive (diseased) + negative (healthy) examples
- Per-trimester organization (1st, 2nd, 3rd trimester symptom weights differ)
- Two-stage inference: Fast track (synchronous) + Comprehensive scan (background/async)
- Community learning platform: doctors contribute diagnosed/undiagnosed cases
- Equipment standardization layer: accepts any file upload (DICOM, JPEG, PNG)
- Patient context integration: maternal age, genetic history, etc. as algorithmic Bayesian priors

**Key Architectural Principle:**
- **AI scope is limited**: MedGemma sees ONLY the ultrasound image
- **All contextual factors are algorithmic**: Age, genetics, history processed in aggregation layer, not by AI

**Non-Functional Requirements:**

| NFR | Implication |
|-----|-------------|
| **Medical Device Compliance** | CE marking (Class IIa/IIb) + FDA 510(k)/De Novo required |
| **Privacy-First** | GDPR compliance, anonymization, local processing capability |
| **Explainability** | Every diagnosis shows similar cases + reasoning + scores |
| **Medical Liability** | Audit trails, confidence intervals, "AI-assisted not AI-diagnosis" labeling |
| **No Vendor Lock-in** | File upload approach, not equipment API integration |
| **Latency** | Fast track < 1 second; comprehensive in background |

### Scale & Complexity

- **Project complexity**: Medium-High (AI/ML + Medical + Community Platform)
- **Primary technical domain**: Medical AI / RAG / Vector Search
- **Estimated architectural components**: 8-12 major components
- **Integration complexity**: Medium (vector DBs, embedding models, MedGemma, FastAPI, frontend)
- **Regulatory complexity**: High (medical device certification)

### Technical Constraints & Dependencies

- **MedGemma limitation**: Trained on CT/MRI/X-ray, NOT ultrasound — requires empirical testing
- **Score ≠ calibrated probability**: Validation dataset needed for clinical use
- **Bootstrapping problem**: Empty community at start; need data to be useful
- **False negative consequences**: Medical context demands validated sensitivity/specificity

### Cross-Cutting Concerns Identified

1. **Privacy & Security**: Patient data anonymization, GDPR, local processing option
2. **Regulatory Compliance**: Medical device certification path (CE/FDA)
3. **Explainability**: Symptom reasoning, similar cases, confidence scores
4. **Data Quality**: Community case validation before entering database
5. **Medical Liability**: Clear "AI-assisted" messaging, audit trails
