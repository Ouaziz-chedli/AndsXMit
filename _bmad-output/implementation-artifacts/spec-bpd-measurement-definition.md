---
title: 'BPD Measurement Scale for AI-Enhanced Ultrasound Inspection'
type: 'feature'
baseline_commit: '385a5a43e83121a8cc9b5406163be1683c0c4caf'
status: 'in-review'
context:
  - 'docs/Aug_2009_Fetal_Measurements_D3NApK5.pdf'
  - 'docs/ARCHITECTURE.md'
  - 'docs/Dev1-AI-Pipeline.md'
  - 'backend/app/core/image_processor.py'
  - 'backend/app/core/medgemma.py'
  - 'backend/app/models/case.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** PrenatalAI's AI pipeline (MedGemma + RAG) lacks standardized fetal biometric context. Without BPD-derived scale information, the AI cannot contextualize whether the fetus is small, average, or large for gestational age — reducing diagnostic accuracy for growth-related conditions.

**Approach:** Define a complete BPD measurement workflow that: (1) standardizes how BPD is measured from ultrasound images, (2) computes centile/size assessment, and (3) injects structured biometric context into the AI prompt to improve disease detection accuracy.

## Boundaries & Constraints

**Always:**
- BPD measurement uses "outer-to-outer" calliper positioning on parietal bones (BMUS standard)
- BPD centiles follow Altman & Chitty 1997 reference data (5th, 50th, 95th centiles, 12–42 weeks GA)
- AI prompt receives structured biometric context: BPD value, GA, centile, size category, head shape warning
- Measurement input is optional — system functions with or without BPD data
- When BPD is provided, AI uses it as contextual prior to adjust disease probability

**Ask First:**
- Semi-automatic vs manual BPD measurement approach
- Whether AI should flag discordance between BPD-derived GA and reported GA

**Never:**
- BPD as sole pregnancy dating parameter (CRL for 6-13 weeks, HC for 13+ weeks)
- Hard-coded centile values outside 12–42 weeks without validation
- Unicode subscripts in any generated PDFs or reports

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MEASURE_BPD | Ultrasound image + reported GA | Returns BPD_mm, centile, size_category, head_shape_warning | Returns None if image lacks head cross-section |
| AI_CONTEXT_BUILD | BPD result + trimeter + disease_prior | Returns structured AI prompt fragment | Fallback to generic prompt if BPD unavailable |
| CENTILE_LOOKUP | BPD_mm + GA_weeks | Returns 5th/50th/95th centile flags | Raises ValueError if GA outside 12-42 weeks |
| SIZE_ASSESSMENT | BPD_mm + GA_weeks | Returns "small" (<5th), "average" (5th-95th), "large" (>95th) | None |
| HEAD_SHAPE_FLAG | BPD_mm + measured_OFD_mm | Returns dolicocephalic_warning if BPD/OFD ratio < 0.75 | None (informational) |

</frozen-after-approval>

## Code Map

- `backend/app/core/fetal_measurements.py` -- New: BPD measurement functions, centile tables, size assessment
- `backend/app/core/image_processor.py` -- Extend: Add optional BPD extraction from DICOM tags
- `backend/app/core/biometric_context.py` -- New: Builds AI prompt fragment from BPD + GA + priors
- `backend/app/core/medgemma.py` -- Extend: Inject biometric_context into MedGemma prompt
- `backend/app/models/case.py` -- Extend: Add BPDMeasurement and BiometricContext to DiseaseCase
- `backend/app/models/diagnosis.py` -- Extend: Add biometric_context field to DiagnosisQuery

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/core/fetal_measurements.py` -- Create BPD measurement module -- Centile lookup, size assessment, head shape detection
- [x] `backend/app/core/biometric_context.py` -- Create AI context builder -- Generates structured BPD context for MedGemma prompts
- [x] `backend/app/core/medgemma.py` -- Extend MedGemma inference -- Inject biometric_context into symptom_extraction prompt
- [x] `backend/app/models/case.py` -- Add BPDMeasurement, BiometricContext schemas -- Structured data for case storage
- [x] `backend/app/models/diagnosis.py` -- Add biometric_context to DiagnosisQuery -- Input model for diagnosis requests
- [x] `backend/tests/test_fetal_measurements.py` -- Unit tests for centile lookup and size assessment
- [x] `backend/tests/test_biometric_context.py` -- Unit tests for AI context generation

**Acceptance Criteria:**
- Given BPD=50mm at 20 weeks GA, when compute_biometric_context(), then returns centile="50th", size_category="average"
- Given GA=50 weeks, when get_bpd_centile(), then raises ValueError with message "GA must be 12-42 weeks"
- Given BPD=30mm at 20 weeks with OFD=45mm, when check_head_shape(), then returns dolicocephalic_warning=True
- Given a diagnosis query with BPD data, when run_diagnosis(), then AI prompt includes "BPD: 50.0mm at 20 weeks (50th centile, average for GA)"

## Spec Change Log

<!-- Empty until the first bad_spec loopback -->

## Design Notes

### Measurement Process (How BPD is Obtained)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     BPD MEASUREMENT WORKFLOW                         │
├─────────────────────────────────────────────────────────────────────┤
│ 1. IMAGE_INPUT     │ Ultrasound image (DICOM/JPEG/PNG)              │
│ 2. HEAD_DETECTION  │ AI detects if head cross-section is present    │
│ 3a. DICOM_TAG      │ If DICOM: extract BPD from BiometryMeasurement │
│ 3b. MANUAL_INPUT   │ Else: doctor enters BPD value manually (mm)    │
│ 3c. AI_ASSISTED    │ Optional: AI suggests BPD measurement points   │
│ 4. COMPUTE         │ Calculate centile, size category, warnings     │
│ 5. BUILD_CONTEXT   │ Generate structured AI prompt fragment          │
│ 6. INJECT_PROMPT   │ Append biometric context to MedGemma input      │
└─────────────────────────────────────────────────────────────────────┘
```

### AI Prompt Enhancement (What Gets Sent to MedGemma)

**Without BPD:**
```
Analyze this ultrasound image. Patient is in {trimester} trimester.
```

**With BPD (enhanced):**
```
Analyze this ultrasound image. Patient is in {trimester} trimester.
Fetal biometry: BPD={bpd_mm}mm at {ga_weeks} weeks ({centile} centile, {size_category}).
Head shape: {head_shape_warning if dolicocephalic else "normal"}.
```

### Why This Improves AI Accuracy

1. **Scale Context**: AI understands whether fetus is small/average/large — relevant for detecting IUGR, macrosomia
2. **Deviation Flag**: Discordance between reported GA and BPD-derived size triggers increased suspicion for growth disorders
3. **Head Shape Awareness**: Dolicocephalic warning reminds AI that BPD may underestimate true gestational age
4. **Trimester Weighting**: BPD centile at 2nd trimester helps calibrate risk for trimester-specific diseases

### BPD Reference Data (Partial — Full Table 12-42 weeks)

| GA (weeks) | 5th (mm) | 50th (mm) | 95th (mm) |
|------------|----------|-----------|----------|
| 12 | 17 | 21 | 25 |
| 14 | 24 | 28 | 32 |
| 16 | 31 | 35 | 40 |
| 18 | 38 | 43 | 48 |
| 20 | 44 | 50 | 56 |
| 22 | 50 | 57 | 64 |
| 24 | 56 | 64 | 72 |
| 26 | 62 | 70 | 79 |
| 28 | 67 | 76 | 85 |
| 30 | 72 | 82 | 92 |
| 35 | 82 | 93 | 104 |
| 40 | 89 | 101 | 113 |
| 42 | 92 | 104 | 116 |

## Verification

**Commands:**
- `cd backend && python -c "from app.core.fetal_measurements import compute_biometric_context; print(compute_biometric_context(45, 20, '2nd'))"` -- expected: structured context dict
- `cd backend && python -c "from app.core.fetal_measurements import get_bpd_reference; get_bpd_reference(50)"` -- expected: ValueError
- `cd backend && python -m pytest tests/test_fetal_measurements.py tests/test_biometric_context.py -v` -- expected: all pass

**Manual checks (if no CLI):**
- Inspect MedGemma prompt in logs to verify biometric_context is injected
- Verify diagnosis result includes biometric_context when BPD was provided
