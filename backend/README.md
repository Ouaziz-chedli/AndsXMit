# PrenatalAI Backend

## Local Development

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
cd backend
docker build -t prenatal-ai .
docker compose up
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
