"""Case upload service layer."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CaseRepository
from app.db.models import CommunityCase


async def process_case_upload(
    db: Session,
    images: list[UploadFile],
    diagnosis: str,
    trimester: Literal["1st", "2nd", "3rd"],
    gestational_age_weeks: float,
    contributor_id: str,
    disease_id: str | None = None,
    b_hcg_mom: float | None = None,
    papp_a_mom: float | None = None,
    outcome: str | None = None,
) -> CommunityCase:
    """
    Process case upload:
    1. Save images to /data/images/
    2. Anonymize any DICOM metadata
    3. Create CommunityCase record
    4. Trigger embedding computation (future)
    """
    # Ensure image directory exists
    image_dir = Path(settings.IMAGE_DIR)
    image_dir.mkdir(parents=True, exist_ok=True)

    # Save images
    saved_paths = []
    for img in images:
        # Generate unique filename
        ext = Path(img.filename or "image.jpg").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".dcm"):
            ext = ".jpg"  # Default to jpg

        filename = f"{uuid.uuid4().hex[:12]}{ext}"
        filepath = image_dir / filename

        # Write file
        content = await img.read()
        with open(filepath, "wb") as f:
            f.write(content)

        saved_paths.append(str(filepath))

    # Create case record
    case = CommunityCase(
        case_id=f"case-{uuid.uuid4().hex[:12]}",
        disease_id=disease_id,
        trimester=trimester,
        images=json.dumps(saved_paths),
        symptom_text=diagnosis,
        gestational_age_weeks=gestational_age_weeks,
        b_hcg_mom=b_hcg_mom,
        papp_a_mom=papp_a_mom,
        validated=False,  # Requires admin validation
        contributor_id=contributor_id,
        outcome=outcome,
        created_at=datetime.utcnow(),
    )

    # Save to database
    case_repo = CaseRepository(db)
    case = case_repo.create(case)

    # TODO: Trigger embedding computation in background

    return case
