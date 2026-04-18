# Backend Task Division — Two Developers

> UI/UX and Marketing are handled by a separate team.

This document coordinates two parallel workstreams. Each developer has their own file:

| Developer | File | Owns |
|-----------|------|------|
| **Dev 1** | `docs/Dev1-AI-Pipeline.md` | Image processing, MedGemma, ChromaDB, scoring, aggregation |
| **Dev 2** | `docs/Dev2-API-Infrastructure.md` | FastAPI, SQLite, Docker, endpoints, services |

---

## Shared Architecture

### Core Constraint: Fully Self-Hostable

The hackathon app must run entirely on a hospital's own machine — no cloud, no external APIs, no managed services.

```
docker compose up
```

Single container, one volume (`./data`), runs offline.

### Stack Decisions

| Need | Choice | Ruled out |
|------|--------|-----------|
| Relational metadata | SQLite | PostgreSQL |
| Async tasks | FastAPI `BackgroundTasks` | Celery + Redis |
| Vector storage | ChromaDB embedded | ChromaDB server |
| Image storage | Local filesystem | MinIO/S3 |
| AI inference | MedGemma local | MedGemma API |

---

## Interface Contract (Day 1)

**Pydantic models** in `backend/app/models/` are the only hard dependency. Agree on these before splitting.

```python
# Dev 1 implements, Dev 2 calls:
async def extract_symptoms(image_bytes: bytes) -> SymptomDescription: ...
async def search_disease(query_embedding, disease_id, trimester, top_k) -> list[RetrievedCase]: ...
def aggregate_scores(similarity_results, trimester, patient_context) -> list[DiagnosisResult]: ...
```

---

## MVP Goal

One disease (Down Syndrome), one trimester (1st), end-to-end, offline via Docker.

| Priority | Dev 1 | Dev 2 |
|----------|-------|-------|
| 1 | MedGemma extracting symptoms | `POST /diagnosis` mock response |
| 2 | ChromaDB seeded with cases | Docker running cleanly |
| 3 | Aggregation + scoring | Service layer wiring |
| 4 | Priors for maternal age | Background comprehensive scan |
