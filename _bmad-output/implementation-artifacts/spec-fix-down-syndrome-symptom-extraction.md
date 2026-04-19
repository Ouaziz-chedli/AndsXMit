---
title: 'fix-down-syndrome-symptom-extraction'
type: 'bugfix'
created: '2026-04-19'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** MedGemma symptom extraction was reporting raw ultrasound measurements as "normal" without DS-specific clinical interpretation. When given an image with elevated nuchal translucency (3.2mm) and absent nasal bone, it reported "normal" findings because the prompt didn't ask for DS-marker assessment.

**Approach:** Enhanced the MedGemma system prompt to explicitly instruct the model to assess Down Syndrome markers with risk-based language, updated the symptom_text property to include assessment context, and fixed mock analysis to return realistic DS-like findings for pipeline testing.

## Boundaries & Constraints

**Always:**
- SymptomText must include assessment (elevated/normal/absent) not just raw values
- Mock data returns DS-positive patterns to test full pipeline
- All 24 medgemma tests pass

**Ask First:** None

**Never:**
- Don't modify the vector store or scoring logic (those are correct)
- Don't change the mock case JSON files (they already have correct data)

## Code Map

- `backend/app/core/medgemma.py` -- Enhanced prompt, SymptomDescription.ds_risk_level field, improved _mock_analysis
- `backend/tests/test_medgemma.py` -- Updated assertions for DS marker patterns

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/core/medgemma.py` -- Enhanced SYMPTOM_EXTRACTION_PROMPT with DS-specific markers and risk thresholds
- [x] `backend/app/core/medgemma.py` -- Added ds_risk_level field to SymptomDescription
- [x] `backend/app/core/medgemma.py` -- Updated symptom_text property to include assessment context
- [x] `backend/app/core/medgemma.py` -- Fixed _mock_analysis to return elevated NT, absent nasal bone, cardiac abnormality
- [x] `backend/tests/test_medgemma.py` -- Updated tests to expect DS-risk mock findings

**Acceptance Criteria:**
- Given first-trimester ultrasound with DS markers, when MedGemma extracts symptoms, then symptom_text contains "elevated" and "absent" (not just raw values)
- Given Ollama unavailable, when _mock_analysis("1st") is called, then returns ds_risk_level="high" with 4 symptoms including elevated NT and absent nasal bone
- Given all tests run, when pytest executes, then 24/24 medgemma tests pass

## Verification

**Commands:**
- `cd backend && ./.venv/bin/python -m pytest tests/test_medgemma.py -v` -- expected: 24 passed
- `cd backend && ./.venv/bin/python -m pytest tests/ -v` -- expected: 185+ passed (2 env-related failures acceptable)

## Spec Change Log

<!-- Empty - no review loops occurred -->

## Design Notes

**Why the original approach failed:**
1. Original prompt: "Focus on markers relevant to prenatal screening" → led to neutral reporting
2. Mock returned normal values → pipeline couldn't detect DS even in test
3. symptom_text format: `"nuchal_translucency=2.5mm"` → no assessment context for embedding

**What the fix does:**
1. Explicit DS marker thresholds: "Normal: <3.0mm, Elevated: >3.5mm (HIGH RISK)"
2. Mock returns: `"nuchal_translucency=3.2mm(elevated)"` → matches mock_cases/down_syndrome_1st.json pattern
3. SymptomDescription.symptom_text: includes assessment in format `type=value(assessment)`

**Embedding alignment:**
- Before: `"nuchal_translucency=2.5mm"` embedded differently from `"nuchal_translucency=3.2mm elevated"`
- After: Both include assessment, embeddings now semantically closer to stored cases
