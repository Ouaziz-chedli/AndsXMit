---
title: 'PDF Upload & Vector Indexing'
type: 'feature'
created: '2026-04-18'
status: 'done'
baseline_commit: '5b0b618bde62364b234e848c615c47e3f70ac015'
context:
  - 'backend/app/core/vector_store.py'
  - 'backend/app/main.py'
  - 'docs/Dev1-AI-Pipeline.md'
---

## Intent

**Problem:** Users need to upload PDF medical documents and have them indexed into ChromaDB vector database for similarity search.

**Approach:** Create an API endpoint that accepts PDF uploads, extracts text, chunks it, generates embeddings, and stores in ChromaDB collection `medical_docs`.

## Boundaries & Constraints

**Always:**
- Single endpoint: `POST /api/v1/documents/upload`
- PDF only (validate file type)
- ChromaDB collection: `medical_docs`
- Text extraction via pypdf
- Embedding via sentence-transformers (all-MiniLM-L6-v2)
- Chunk size: 500 chars, overlap: 50

**Never:**
- Other file types (DICOM, JPEG handled elsewhere)
- External API calls for embeddings
- Multi-container setup

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| VALID_PDF | PDF file, properly formatted | 200 + {"chunks_indexed": N, "document_id": "uuid"} | N/A |
| EMPTY_PDF | PDF with no extractable text | 200 + {"chunks_indexed": 0, "document_id": "uuid"} | Warning in response |
| CORRUPT_PDF | Invalid PDF structure | 422 + {"detail": "Invalid PDF format"} | pypdf exception |
| MISSING_FILE | No file provided | 422 + {"detail": "File is required"} | FastAPI validation |
| WRONG_TYPE | Non-PDF file | 422 + {"detail": "File must be a PDF"} | MIME type check |

## Code Map

- `backend/app/api/documents.py` -- New router with POST /upload
- `backend/app/core/document_processor.py` -- PDF text extraction + chunking + embedding
- `backend/app/models/documents.py` -- UploadResponse, DocumentMetadata models

## Tasks & Acceptance

**Execution:**
- [x] `backend/app/models/documents.py` -- UploadResponse, DocumentMetadata Pydantic models
- [x] `backend/app/core/document_processor.py` -- extract_text, chunk_text, process_and_index functions
- [x] `backend/app/api/documents.py` -- POST /documents/upload endpoint
- [x] `backend/app/main.py` -- Include documents_router
- [x] Update `backend/requirements.txt` -- Already has pypdf, sentence-transformers

## Acceptance Criteria

- Given a valid PDF file, when POST /api/v1/documents/upload, then file is processed and chunks stored in ChromaDB
- Given no file provided, when calling the endpoint, then 422 error with "File is required"
- Given a non-PDF file, when calling the endpoint, then 422 error with "File must be a PDF"
- Given a PDF with extractable text, when processed, then chunks are indexed with embeddings
- Given ChromaDB is running, when indexing completes, then chunks searchable via vector search

## Design Notes

**Flow:**
```
PDF Upload → Validate MIME → Extract Text (pypdf) → Chunk (500 chars, 50 overlap)
→ Generate Embeddings (sentence-transformers) → Store in ChromaDB (collection: medical_docs)
→ Return document_id + chunk_count
```

**Chunking Strategy:**
- Smart chunking: Break at sentence boundaries (period, question mark, exclamation)
- Preserve medical terminology
- Store source filename as metadata

## Verification

```bash
# Test upload
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test_medical_doc.pdf"

# Expected: {"document_id": "...", "chunks_indexed": 10, "status": "success"}

# Verify in ChromaDB (via Python)
from backend.app.core.vector_store import VectorStore
vs = VectorStore("/data/vector_db")
# Query the medical_docs collection
```

## Suggested Review Order

**API Entry Point**

- PDF upload endpoint with content-type validation
  [`documents.py:13`](backend/app/api/documents.py#L13)

- Document response models
  [`documents.py:5`](backend/app/models/documents.py#L5)

**Document Processing**

- PDF text extraction and error handling
  [`document_processor.py:61`](backend/app/core/document_processor.py#L61)

- Sentence-boundary chunking with overlap
  [`document_processor.py:85`](backend/app/core/document_processor.py#L85)

- ChromaDB indexing with embeddings
  [`document_processor.py:125`](backend/app/core/document_processor.py#L125)

- Search with similarity scoring
  [`document_processor.py:173`](backend/app/core/document_processor.py#L173)

**Application Wiring**

- Router inclusion in FastAPI app
  [`main.py:9`](backend/app/main.py#L9)

- Router registration
  [`main.py:43`](backend/app/main.py#L43)