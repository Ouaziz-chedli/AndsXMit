# AGENTS.md — PrenatalAI

## Project State

**This is a planning-only repository.** No implementation code exists yet. The architecture is defined in docs; code implementation has not started.

## Key Architecture Decision

**MedGemma sees ONLY the ultrasound image.** All patient context (age, genetics, history) is processed algorithmically in the aggregation layer — never passed to the AI model.

## Critical Risk

- **MedGemma was trained on CT/MRI/X-ray, NOT ultrasound.** Empirical testing on ultrasound images is required before committing to this architecture. If MedGemma fails on ultrasound, the entire approach needs revision.

## Known Scoring Formula

```
disease_score = (avg(positive_similarities) - avg(negative_similarities)) × trimester_weight × prior_multiplier
```

## Two Output Paths

| Mode | Scope | Latency |
|------|-------|---------|
| Fast Track | Top 5 diseases | < 1 second, sync |
| Comprehensive | All diseases | Background, async |

## Key Files

- `README.md` — Full system design, scoring logic, medical context
- `docs/ARCHITECTURE.md` — Complete architectural reference with API design, data models, project structure
- `CLAUDE.md` — Compact guidance for Claude Code

## When Implementing

1. **Start with MedGemma integration testing** on actual ultrasound images before building anything else
2. **Use ChromaDB** (not Qdrant) for hackaton — simpler, local, embedded
3. **Build Down Syndrome as proof-of-concept** with 1st trimester only
4. **Key principle**: AI does symptom extraction only; all contextual scoring is algorithmic

## Two Data Pipelines

| Pipeline | Input | Model | ChromaDB Collection |
|----------|-------|-------|-------------------|
| **Image** | Ultrasound (DICOM, JPEG, PNG) | MedGemma (vision → text) | `disease_cases` |
| **Document** | PDF, TXT (medical literature) | Sentence Transformers | `medical_docs` |

- Document processing uses `pypdf` for PDF extraction and `sentence-transformers` for embeddings
- **DICOM is the primary clinical format** (~90% of ultrasound); use `pydicom` library
- Documents are **reference context**, not diagnosis input
- Keep the two pipelines separate; don't mix document chunks with disease case embeddings

## What NOT to Do

- Do not implement full multi-disease coverage in hackaton timeframe
- Do not pass patient context to MedGemma
- Do not use fixed thresholds — the system should learn from community data
- Do not commit to production infrastructure (PostgreSQL, S3) until validated
