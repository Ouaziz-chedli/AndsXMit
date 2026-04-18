"""Cases API endpoints for community case management."""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import CaseRepository, ContributorRepository, get_db
from app.db.models import CommunityCase, Contributor
from app.services.case_upload import process_case_upload

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.post("")
async def upload_case(
    images: list[UploadFile] = File(...),
    diagnosis: str = Form(...),
    trimester: str = Form(...),
    gestational_age_weeks: float = Form(...),
    contributor_id: str = Form(...),
    disease_id: str | None = Form(None),
    b_hcg_mom: float | None = Form(None),
    papp_a_mom: float | None = Form(None),
    outcome: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a diagnosed case to the community database.

    Cases are anonymized before storage.
    """
    # Validate trimester
    if trimester not in ("1st", "2nd", "3rd"):
        raise HTTPException(status_code=422, detail="Invalid trimester")

    # Verify contributor exists
    contributor_repo = ContributorRepository(db)
    contributor = contributor_repo.get_by_id(contributor_id)
    if not contributor:
        raise HTTPException(status_code=404, detail="Contributor not found")

    # Process upload
    result = await process_case_upload(
        db=db,
        images=images,
        diagnosis=diagnosis,
        trimester=trimester,
        gestational_age_weeks=gestational_age_weeks,
        contributor_id=contributor_id,
        disease_id=disease_id,
        b_hcg_mom=b_hcg_mom,
        papp_a_mom=papp_a_mom,
        outcome=outcome,
    )

    return {
        "case_id": result.case_id,
        "status": "uploaded",
        "message": "Case submitted for validation",
    }


@router.get("")
async def list_cases(
    disease: str | None = None,
    trimester: str | None = None,
    validated: bool | None = None,
    db: Session = Depends(get_db),
):
    """
    List cases with optional filters.
    """
    case_repo = CaseRepository(db)
    cases = case_repo.list(disease=disease, trimester=trimester, validated=validated)

    return {
        "total": len(cases),
        "cases": [
            {
                "case_id": c.case_id,
                "disease_id": c.disease_id,
                "trimester": c.trimester,
                "symptom_text": c.symptom_text,
                "gestational_age_weeks": c.gestational_age_weeks,
                "validated": c.validated,
                "created_at": c.created_at.isoformat(),
            }
            for c in cases
        ],
    }
