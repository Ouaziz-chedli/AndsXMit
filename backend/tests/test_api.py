"""API endpoint tests for PrenatalAI."""

import os
import sys
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment BEFORE importing app modules
os.environ["DB_PATH"] = ":memory:"
os.environ["DATA_DIR"] = "/tmp/prenatal_test"
os.environ["IMAGE_DIR"] = "/tmp/prenatal_test/images"

# Create test engine at module level
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db():
    """Test database dependency."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create test app without lifespan to avoid init_db
from app.api import cases_router, diagnosis_router, diseases_router

test_app = FastAPI(title="PrenatalAI-Test")
test_app.include_router(diagnosis_router)
test_app.include_router(cases_router)
test_app.include_router(diseases_router)


@test_app.get("/health")
async def health():
    return {"status": "ok"}


@test_app.get("/")
async def root():
    return {"name": "PrenatalAI", "version": "0.1.0", "docs": "/docs"}


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh test database for each test."""
    from app.db import Base
    from app.db.repositories import DiseaseRepository

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Seed default diseases
    session = TestSessionLocal()
    disease_repo = DiseaseRepository(session)
    disease_repo.seed_defaults()
    session.commit()
    session.close()

    yield

    # Cleanup
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with test database."""
    from app.db import get_db

    # Override the get_db dependency
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(test_app)
    test_app.dependency_overrides.clear()


def test_health(client):
    """Health check returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root(client):
    """Root endpoint returns app info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PrenatalAI"
    assert "version" in data


def test_list_diseases(client):
    """List diseases endpoint returns disease list."""
    response = client.get("/api/v1/diseases")
    assert response.status_code == 200
    data = response.json()
    assert "diseases" in data
    # Default diseases should be seeded
    assert len(data["diseases"]) >= 3  # down_syndrome, edwards, patau


def test_get_disease_weights(client):
    """Get disease weights endpoint."""
    response = client.get("/api/v1/diseases/down_syndrome/weights")
    assert response.status_code == 200
    data = response.json()
    assert data["disease_id"] == "down_syndrome"
    assert "weights" in data
    assert "1st" in data["weights"]


def test_get_disease_weights_not_found(client):
    """Get weights for unknown disease returns 404."""
    response = client.get("/api/v1/diseases/unknown_disease/weights")
    assert response.status_code == 404


def test_list_cases_empty(client):
    """List cases returns empty list initially."""
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["cases"] == []


def test_diagnose_missing_fields(client):
    """Diagnosis with missing required fields returns 422."""
    response = client.post("/api/v1/diagnosis", data={})
    assert response.status_code == 422


def test_diagnose_invalid_trimester(client):
    """Diagnosis with invalid trimester returns 422."""
    response = client.post(
        "/api/v1/diagnosis",
        data={
            "trimester": "invalid",
            "mother_age": 30,
            "gestational_age_weeks": 12,
        },
    )
    assert response.status_code == 422


def test_diagnose_mock_response(client):
    """Diagnosis returns mock fast track response."""
    import io

    files = {"images": ("test.jpg", io.BytesIO(b"fake image content"), "image/jpeg")}
    data = {
        "trimester": "1st",
        "mother_age": 35,
        "gestational_age_weeks": 12,
    }

    response = client.post("/api/v1/diagnosis", data=data, files=files)
    assert response.status_code == 200

    result = response.json()
    assert "fast_track" in result
    assert "comprehensive_pending" in result
    assert "comprehensive_callback_url" in result
    assert "fast_track_ms" in result
    assert "timestamp" in result

    # Should return top 5 diseases
    assert len(result["fast_track"]) == 5

    # Down syndrome should be first (highest score for maternal age 35)
    assert result["fast_track"][0]["disease_id"] == "down_syndrome"
    assert "maternal_age_35" in result["fast_track"][0]["applied_priors"]


def test_comprehensive_pending(client):
    """Comprehensive results returns 202 for pending task."""
    import io

    files = {"images": ("test.jpg", io.BytesIO(b"fake image content"), "image/jpeg")}
    data = {
        "trimester": "1st",
        "mother_age": 30,
        "gestational_age_weeks": 12,
    }

    response = client.post("/api/v1/diagnosis", data=data, files=files)
    task_url = response.json()["comprehensive_callback_url"]

    # Extract task_id from URL
    task_id = task_url.split("/")[-2]

    # Get comprehensive results
    response = client.get(f"/api/v1/diagnosis/{task_id}/comprehensive")
    assert response.status_code == 202  # Pending returns 202


def test_comprehensive_not_found(client):
    """Comprehensive results returns 404 for unknown task."""
    response = client.get("/api/v1/diagnosis/nonexistent-task/comprehensive")
    assert response.status_code == 404


def test_upload_case_contributor_not_found(client):
    """Upload case with unknown contributor returns 404."""
    import io

    files = {"images": ("test.jpg", io.BytesIO(b"fake image content"), "image/jpeg")}
    data = {
        "diagnosis": "Normal NT measurement, no anomalies detected",
        "trimester": "1st",
        "gestational_age_weeks": 12.0,
        "contributor_id": "unknown-contributor",
    }

    response = client.post("/api/v1/cases", data=data, files=files)
    assert response.status_code == 404


def test_upload_case_invalid_trimester(client):
    """Upload case with invalid trimester returns 422."""
    import io

    files = {"images": ("test.jpg", io.BytesIO(b"fake image content"), "image/jpeg")}
    data = {
        "diagnosis": "Test diagnosis",
        "trimester": "invalid",
        "gestational_age_weeks": 12.0,
        "contributor_id": "contrib-001",
    }

    response = client.post("/api/v1/cases", data=data, files=files)
    assert response.status_code == 422
