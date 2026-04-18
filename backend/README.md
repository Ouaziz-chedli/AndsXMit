# PrenatalAI Backend Usage Guide

## Quick Start

### 1. Development Mode

```bash
cd backend

# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Docker Mode

```bash
cd backend

# Build image
docker build -t prenatal-ai .

# Run container
docker compose up
```

The API will be available at **http://localhost:8000**

### 3. API Documentation

Once running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/data` | Base directory for all data |
| `DB_PATH` | `/data/db.sqlite` | SQLite database path |
| `CHROMA_PATH` | `/data/vector_db` | ChromaDB persistence path |
| `IMAGE_DIR` | `/data/images` | Uploaded image storage |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `medgemma` | Ollama model name |

---

## API Endpoints

### Health Check

```
GET /health
```

Returns server status.

**Response:**
```json
{"status": "ok"}
```

---

### Diagnosis

#### Submit Diagnosis Request

```
POST /api/v1/diagnosis
Content-Type: multipart/form-data
```

**Parameters (form-data):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | file | Yes | Ultrasound image(s) (JPEG, PNG, DICOM) |
| `trimester` | string | Yes | `"1st"`, `"2nd"`, or `"3rd"` |
| `mother_age` | integer | Yes | Mother's age at due date |
| `gestational_age_weeks` | float | Yes | Weeks since last menstrual period |
| `b_hcg` | float | No | Beta-hCG biomarker (IU/L) |
| `papp_a` | float | No | PAPP-A biomarker (IU/L) |
| `previous_affected_pregnancy` | boolean | No | Prior chromosomal anomaly (default: false) |

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/diagnosis \
  -F "images=@ultrasound.jpg" \
  -F "trimester=1st" \
  -F "mother_age=35" \
  -F "gestational_age_weeks=12" \
  -F "b_hcg=55000" \
  -F "papp_a=1200"
```

**Response:**
```json
{
  "fast_track": [
    {
      "disease_id": "down_syndrome",
      "disease_name": "Down Syndrome (Trisomy 21)",
      "final_score": 0.65,
      "confidence_interval": [0.55, 0.75],
      "applied_priors": ["maternal_age_35", "biomarker_pattern_ds"],
      "matching_positive_cases": [
        {"case_id": "mock_ds_pos_001", "similarity": 0.82}
      ],
      "matching_negative_cases": [
        {"case_id": "mock_neg_001", "similarity": 0.25}
      ]
    }
  ],
  "comprehensive_pending": true,
  "comprehensive_callback_url": "/api/v1/diagnosis/task-abc123/comprehensive",
  "fast_track_ms": 150,
  "timestamp": "2026-04-18T12:00:00Z"
}
```

---

#### Get Comprehensive Results

```
GET /api/v1/diagnosis/{task_id}/comprehensive
```

**Response (pending):**
```json
HTTP 202 Accepted
{
  "task_id": "task-abc123",
  "status": "pending",
  "results": null,
  "completed_at": null
}
```

**Response (completed):**
```json
HTTP 200 OK
{
  "task_id": "task-abc123",
  "status": "completed",
  "results": [...],
  "completed_at": "2026-04-18T12:01:00Z"
}
```

---

### Cases

#### Upload Case

```
POST /api/v1/cases
Content-Type: multipart/form-data
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `images` | file | Yes | Case ultrasound image(s) |
| `diagnosis` | string | Yes | Symptom text description |
| `trimester` | string | Yes | `"1st"`, `"2nd"`, `"3rd"` |
| `gestational_age_weeks` | float | Yes | Gestational age |
| `contributor_id` | string | Yes | Contributor ID |
| `disease_id` | string | No | Disease ID (if diagnosed) |
| `b_hcg_mom` | float | No | MoM-normalized b-hCG |
| `papp_a_mom` | float | No | MoM-normalized PAPP-A |
| `outcome` | string | No | Pregnancy outcome |

**Response:**
```json
{
  "case_id": "case-abc123def",
  "status": "uploaded",
  "message": "Case submitted for validation"
}
```

---

#### List Cases

```
GET /api/v1/cases
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `disease` | string | Filter by disease ID |
| `trimester` | string | Filter by trimester |
| `validated` | boolean | Filter by validation status |

**Example:**
```bash
curl "http://localhost:8000/api/v1/cases?disease=down_syndrome&validated=true"
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

---

### Diseases

#### List Diseases

```
GET /api/v1/diseases
```

**Response:**
```json
{
  "diseases": [
    {
      "disease_id": "down_syndrome",
      "name": "Down Syndrome (Trisomy 21)",
      "description": "Chromosomal condition",
      "base_prevalence": 1.0,
      "trimester_profiles": {
        "1st": {"weight": 0.85, "nt_cutoff_mm": 3.0},
        "2nd": {"weight": 0.75},
        "3rd": {"weight": 0.40}
      }
    }
  ]
}
```

---

#### Get Disease Weights

```
GET /api/v1/diseases/{disease_id}/weights
```

**Response:**
```json
{
  "disease_id": "down_syndrome",
  "name": "Down Syndrome (Trisomy 21)",
  "weights": {
    "1st": 0.85,
    "2nd": 0.75,
    "3rd": 0.40
  }
}
```

---

## Data Storage

```
/data/
├── db.sqlite          # SQLite database (metadata)
├── vector_db/         # ChromaDB vector database
└── images/            # Uploaded ultrasound images
```

---

## Docker Deployment

### Build and Run

```bash
cd backend
docker build -t prenatal-ai .
docker compose up
```

### With Ollama (for AI inference)

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
      - ollama_data:/root/.ollama
    environment:
      - DATA_DIR=/data
      - OLLAMA_HOST=http://localhost:11434
    runtime: nvidia  # Optional: only if GPU available

volumes:
  ollama_data:
```

### GPU Support

For faster inference with GPU:

```bash
docker compose up
```

Make sure NVIDIA drivers and `nvidia-container-toolkit` are installed on the host.

---

## Troubleshooting

### Port Already in Use

```bash
docker compose down
docker compose up
```

### Database Errors

Ensure the `/data` directory exists and is writable:

```bash
mkdir -p data
chmod 777 data
```

### Ollama Connection Issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check model is available
curl http://localhost:11434/api/show -d '{"name":"medgemma"}'
```

---

## File Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Environment settings
│   ├── api/
│   │   ├── diagnosis.py     # Diagnosis endpoints
│   │   ├── cases.py         # Case management endpoints
│   │   └── diseases.py      # Reference data endpoints
│   ├── models/
│   │   └── diagnosis.py     # Pydantic models
│   ├── db/
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models.py        # ORM models
│   │   └── repositories.py  # Data access layer
│   └── services/
│       ├── diagnosis.py     # Diagnosis business logic
│       ├── case_upload.py   # Case upload logic
│       └── validation.py    # Admin validation
├── tests/
│   └── test_api.py         # API tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```
