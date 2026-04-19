---
status: done
title: Data Saving to /save Folder
route: one-shot
created: 2026-04-19
---

# Data Saving to /save Folder

## Intent

**Problem:** Diagnosis input/output data was not persisted locally for review/debugging.

**Approach:** After each diagnosis via API, save three files to `/save/{timestamp}/{task_id}/`.

---

## Implementation

### Scope 1: Image Copy
- **Path:** `save/{timestamp}/{task_id}/image.{ext}`
- **Content:** Binary copy of uploaded image

### Scope 2: Results JSON
- **Path:** `save/{timestamp}/{task_id}/results.json`
- **Content:**
  ```json
  {
    "task_id": "...",
    "timestamp": "...",
    "trimester": "...",
    "fast_track_ms": ...,
    "results": [...]
  }
  ```

### Scope 3: Patient Context (Anonymized)
- **Path:** `save/{timestamp}/{task_id}/context.json`
- **Content:**
  ```json
  {
    "task_id": "...",
    "timestamp": "...",
    "trimester": "...",
    "gestational_age_weeks": ...,
    "mother_age": ...,
    "previous_affected_pregnancy": ...
  }
  ```
- **Note:** Biomarkers omitted for privacy

---

## Files Changed

- `backend/app/api/diagnosis.py:81-87,129-165` - Added save logic after diagnosis

---

## Suggested Review Order

1. `backend/app/api/diagnosis.py` - Main save implementation