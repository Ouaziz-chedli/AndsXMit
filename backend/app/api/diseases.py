"""Diseases API endpoints for reference data."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import DiseaseRepository, get_db
from app.db.models import Disease

router = APIRouter(prefix="/api/v1/diseases", tags=["diseases"])


@router.get("")
async def list_diseases(db: Session = Depends(get_db)):
    """
    List all supported diseases with trimester weights.
    """
    repo = DiseaseRepository(db)
    diseases = repo.list_all()

    return {
        "diseases": [
            {
                "disease_id": d.disease_id,
                "name": d.name,
                "description": d.description,
                "base_prevalence": d.base_prevalence,
                "trimester_profiles": json.loads(d.trimester_profiles) if d.trimester_profiles else {},
            }
            for d in diseases
        ]
    }


@router.get("/{disease_id}/weights")
async def get_disease_weights(
    disease_id: str,
    db: Session = Depends(get_db),
):
    """
    Get trimester-specific symptom weights for a disease.
    """
    repo = DiseaseRepository(db)
    disease = repo.get_by_id(disease_id)

    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")

    profiles = json.loads(disease.trimester_profiles) if disease.trimester_profiles else {}

    # Return weights for each trimester
    weights = {}
    for trimester, profile in profiles.items():
        weights[trimester] = profile.get("weight", 1.0)

    return {
        "disease_id": disease.disease_id,
        "name": disease.name,
        "weights": weights,
    }
