# Doctor Case Upload Pipeline

How doctors contribute validated cases to improve the community knowledge base.

## Overview

Doctors upload confirmed prenatal cases to help the community. These cases are validated before being added to the vector database, where they improve future diagnoses.

## Complete Flow

```
Doctor uploads case
        │
        ▼
┌───────────────────┐
│ Save images       │
│ Anonymize DICOM  │
│ Store in SQLite  │
└───────────────────┘
        │
        ▼ (validated=FALSE)
┌───────────────────┐
│ Pending Review    │◄────────── Admin reviews
└───────────────────┘
        │                   │
        │ Admin approves     │ Admin rejects
        ▼                   ▼
┌───────────────┐    ┌───────────────┐
│ Add to        │    │ Flag as       │
│ Vector DB     │    │ rejected      │
│ (ChromaDB)    │    │ (not used)    │
└───────────────┘    └───────────────┘
        │
        ▼
┌───────────────┐
│ Improves      │
│ future        │
│ diagnoses     │
└───────────────┘
```

## Step 1: Doctor Uploads Case

**Endpoint:** `POST /api/v1/cases`

```bash
curl -X POST http://localhost:8000/api/v1/cases \
  -F "images=@ultrasound.jpg" \
  -F "diagnosis=NT 3.2mm, absent nasal bone, cardiac AV canal defect" \
  -F "trimester=1st" \
  -F "gestational_age_weeks=12" \
  -F "contributor_id=dr-123" \
  -F "disease_id=down_syndrome" \
  -F "b_hcg_mom=2.1" \
  -F "papp_a_mom=0.48" \
  -F "outcome=confirmed_at_birth"
```

### Form Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | file(s) | Yes | Ultrasound image(s) |
| `diagnosis` | string | Yes | Symptom text description |
| `trimester` | string | Yes | `"1st"`, `"2nd"`, or `"3rd"` |
| `gestational_age_weeks` | float | Yes | Gestational age |
| `contributor_id` | string | Yes | Doctor's contributor ID |
| `disease_id` | string | No | Confirmed diagnosis |
| `b_hcg_mom` | float | No | MoM-normalized b-hCG |
| `papp_a_mom` | float | No | MoM-normalized PAPP-A |
| `outcome` | string | No | Pregnancy outcome |

**Response:**
```json
{
  "case_id": "case-a1b2c3d4",
  "status": "uploaded",
  "message": "Case submitted for validation"
}
```

## Step 2: Case Processing

When a case is uploaded, the system:

1. **Saves images** to `/data/images/`
   - Generates unique filenames (UUID-based)
   - Converts to standard format if needed

2. **Anonymizes DICOM metadata**
   - Removes: PatientName, PatientID, PatientBirthDate
   - Removes: StudyDate, PatientSex, PatientAddress
   - Ensures patient privacy before storage

3. **Stores in SQLite database**
   - `CommunityCase` table
   - `validated = FALSE` (requires admin approval)

## Step 3: Admin Validation

Cases are **not immediately available** for diagnosis. An admin must review and approve.

### Validation Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Required fields present | ERROR | disease_id, trimester, label, images |
| Valid disease | ERROR | Must be in supported diseases |
| Valid trimester | ERROR | Must be "1st", "2nd", or "3rd" |
| Gestational age consistency | WARNING | Age should match trimester range |
| Biomarker ranges | WARNING | b-hCG: 0-500,000, PAPP-A: 0-10,000 |
| Biomarker consistency | INFO | Pattern should match disease |

### Validation Issues

```python
@dataclass
class ValidationIssue:
    severity: Severity  # ERROR, WARNING, INFO
    field: str
    message: str
```

- **ERROR**: Prevents case from being approved
- **WARNING**: Case can be approved but flagged
- **INFO**: Advisory information

## Step 4: Approved → Vector Database

Once admin approves, the case enters ChromaDB:

### What's Stored

| Field | Storage | Purpose |
|-------|---------|---------|
| `symptom_text` | ChromaDB | Embedding for similarity search |
| `disease_id` | ChromaDB metadata | Filter positive/negative |
| `trimester` | ChromaDB metadata | Match query trimester |
| `b_hcg_mom`, `papp_a_mom` | ChromaDB metadata | Biomarker matching |
| `images` | File system | Path reference for review |

### ChromaDB Collection Structure

```
Per Disease Database (e.g., Down Syndrome):

down_syndrome_1st/
├── POSITIVE cases (confirmed diseased)
│   ├── case-a1b2c3d4
│   │   ├── embedding: [0.12, 0.34, ...]
│   │   ├── symptom_text: "NT 3.2mm, absent nasal bone"
│   │   └── metadata: {b_hcg_mom: 2.1, papp_a_mom: 0.48}
│   └── case-e5f6g7h8
│       └── ...
└── NEGATIVE cases (confirmed healthy)
    ├── case-i9j0k1l2
    └── ...
```

## Query Cases (Read-Only)

Doctors can browse submitted cases without approval:

```bash
# List all approved cases
GET /api/v1/cases?validated=true

# Filter by disease
GET /api/v1/cases?disease=down_syndrome

# Filter by trimester
GET /api/v1/cases?trimester=1st

# Filter pending validation
GET /api/v1/cases?validated=false
```

**Response:**
```json
{
  "total": 2,
  "cases": [
    {
      "case_id": "case-001",
      "disease_id": "down_syndrome",
      "trimester": "1st",
      "symptom_text": "NT 3.5mm, absent nasal bone",
      "gestational_age_weeks": 12.0,
      "validated": true,
      "created_at": "2026-04-18T10:00:00Z"
    }
  ]
}
```

## Privacy Protection

Before any case enters the system:

### DICOM Anonymization

```python
def anonymize_dicom(ds: Dataset) -> Dataset:
    """Remove PII from DICOM metadata."""
    pii_fields = [
        'PatientName', 'PatientID', 'PatientBirthDate',
        'PatientSex', 'PatientAddress', 'PatientTelephoneNumbers',
        'OtherPatientIDs', 'OtherPatientNames',
        'StudyDate', 'StudyTime',
    ]
    for field in pii_fields:
        if hasattr(ds, field):
            setattr(ds, field, None)
    return ds
```

### What Remains (Non-PII)

- Ultrasound image pixels (anonymized)
- Gestational age
- Biomarker values (MoM, not absolute)
- Trimester
- Symptom descriptions (doctor-provided, no patient info)

## Impact on Diagnosis

A validated case contributes to future diagnoses:

```
New case uploaded & approved
        │
        ▼
Case stored in ChromaDB
        │
        ▼
Doctor diagnoses similar patient
        │
        ▼
Vector search finds similar case
        │
        ▼
Similarity score improves
        │
        ▼
Better diagnosis accuracy
```

**More cases = Better AI = Fewer missed diagnoses**

## File Structure

```
backend/app/
├── api/
│   └── cases.py              # POST /api/v1/cases
├── services/
│   ├── case_upload.py        # process_case_upload()
│   └── validation.py        # ValidationService
└── db/
    ├── models.py            # CommunityCase ORM
    └── repositories.py       # CaseRepository
```

## Summary

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Upload | ✅ | Doctor uploads case via API |
| 2. Process | ✅ | Images saved, DICOM anonymized |
| 3. Store | ✅ | SQLite with validated=FALSE |
| 4. Validate | ⏳ | Admin reviews and approves |
| 5. Vectorize | ⏳ | Case embedded and searchable |
| 6. Improve | ⏳ | Contributes to future diagnoses |

**Note:** Steps 4-6 are partially implemented. Full admin validation UI and vector embedding on upload are TODO items for future development.
