# PrenatalAI Documentation Index

> **Central entry point** for PrenatalAI project documentation.
> See also: [README.md](../README.md) for product vision and system overview.

---

## Documentation Map

```
prenatal-ai/
├── README.md                    # Product vision, goals, technology philosophy
│
├── docs/
│   ├── ARCHITECTURE.md          # ⭐ Complete architectural reference (SOURCE OF TRUTH)
│   ├── ARCHITECTURE_INDEX.md    # This file — navigation hub
│   │
│   ├── Dev1-AI-Pipeline.md      # Dev1: MedGemma, ChromaDB, scoring, priors
│   ├── Dev2-API-Infrastructure.md # Dev2: FastAPI, SQLite, Docker, endpoints
│   ├── Dev1-Plan-Implementation.md # Dev1 implementation plan (French)
│   │
│   ├── STRATEGIE.md             # European strategy (EHDS, RGPD, open source)
│   └── RepatitionBackend.md      # Dev coordination
│
├── backend/                     # Python/FastAPI — AI pipeline
│   ├── app/                    # FastAPI application
│   ├── tests/                  # Python tests (155 passing)
│   ├── scripts/                # Seed scripts
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── pipeline-detection.md    # 7-step diagnosis pipeline
│   └── pipeline-doctor.md       # Doctor case upload workflow
│
├── api/                        # Node.js/Express — REST API
│   ├── src/                   # Express routes, controllers, middleware
│   ├── prisma/                # Prisma ORM (auth, users)
│   ├── package.json
│   ├── Dockerfile
│   └── check_db.js            # DB diagnostic script
│
└── frontend/                   # React/Vite — UI
    ├── src/
    ├── package.json
    └── Dockerfile
```

---

## By Role / Need

| If you are... | Read this first |
|---------------|-----------------|
| **Understanding the product** | `README.md` |
| **Implementing backend** | `docs/ARCHITECTURE.md` + `backend/README.md` |
| **Working on AI/ML pipeline** | `docs/Dev1-AI-Pipeline.md` |
| **Building API/endpoints** | `docs/Dev2-API-Infrastructure.md` |
| **Understanding diagnosis flow** | `backend/pipeline-detection.md` |
| **Setting up community uploads** | `backend/pipeline-doctor.md` |
| **Presenting to stakeholders** | `docs/STRATEGIE.md` |

---

## Key Architecture Decisions

| Decision | Rationale | Documented In |
|----------|-----------|---------------|
| **MedGemma + RAG** | No training required, community learning | `README.md` §Core Architecture |
| **Per-disease vector DBs** | Isolated, scalable, maintainable | `docs/ARCHITECTURE.md` §Data Layer |
| **Trimester-aware weighting** | Symptoms manifest differently per period | `docs/ARCHITECTURE.md` §Aggregation |
| **Two-stage inference** | Fast (urgent) + Comprehensive (background) | `docs/ARCHITECTURE.md` §Two-Stage |
| **Self-hostable Docker** | Hospital local deployment, no cloud | `docs/Dev2-API-Infrastructure.md` §Core Constraint |

---

## Scoring Formula

```
final_score = (avg(positive_similarities) - avg(negative_similarities))
              × trimester_weight
              × prior_multiplier
```

| Component | Description | Module |
|-----------|-------------|--------|
| `avg(positive_similarities)` | Mean similarity to top-K diseased cases | `vector_store.py` |
| `avg(negative_similarities)` | Mean similarity to top-K healthy cases | `vector_store.py` |
| `trimester_weight` | Disease/trimester-specific (0.40–0.90) | `aggregation.py` |
| `prior_multiplier` | Maternal age, biomarkers, history (1.0–5.0+) | `priors.py` |

---

## Critical Risk

> **MedGemma was trained on CT/MRI/X-ray, NOT ultrasound.**
> Empirical testing on actual ultrasound images is required before committing to this architecture.

Reference: `README.md` §Risks & Concerns

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Architecture defined | ✅ | `docs/ARCHITECTURE.md` |
| Backend exists | ✅ | `backend/` |
| AI pipeline (Dev1) | 🔄 | `docs/Dev1-AI-Pipeline.md` |
| API (Dev2) | 🔄 | `docs/Dev2-API-Infrastructure.md` |
| Frontend/UI | ⬜ | — |
| Clinical validation | ⬜ | — |

---

*Last updated: 2026-04-18*
*Project: PrenatalAI — AndsXMit Hackaton*
