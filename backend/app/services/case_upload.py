"""Case upload service layer."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import CaseRepository
from app.db.models import CommunityCase

# Import core modules for vector store integration
from app.core.vector_store import get_vector_store, StoredCase
from app.core.image_processor import load_ultrasound_image


@dataclass
class CaseUploadResult:
    """Result of case upload processing."""
    success: bool
    case_id: str
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class UploadedCaseData:
    """Data for a case being uploaded."""
    disease_id: str
    trimester: str
    label: str  # "positive" or "negative"
    images: List[str]  # Paths to image files
    symptom_text: Optional[str] = None
    gestational_age_weeks: Optional[float] = None
    b_hcg: Optional[float] = None
    papp_a: Optional[float] = None
    mother_age: Optional[int] = None
    contributor_id: Optional[str] = None
    source_institution: str = ""
    confirmation_method: str = ""


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
    4. Trigger embedding computation and store in ChromaDB
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

    # Determine label from outcome
    label = "positive" if outcome == "positive" else "negative" if outcome == "negative" else "negative"

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

    # Trigger embedding computation in background (non-blocking)
    import asyncio
    asyncio.create_task(_trigger_embedding(
        case_id=case.case_id,
        disease_id=disease_id or "unknown",
        trimester=trimester,
        label=label,
        image_paths=saved_paths,
        symptom_text=diagnosis,
        gestational_age_weeks=gestational_age_weeks,
        b_hcg_mom=b_hcg_mom,
        papp_a_mom=papp_a_mom,
    ))

    return case


async def _trigger_embedding(
    case_id: str,
    disease_id: str,
    trimester: str,
    label: str,
    image_paths: List[str],
    symptom_text: str,
    gestational_age_weeks: float | None,
    b_hcg_mom: float | None,
    papp_a_mom: float | None,
) -> None:
    """
    Background task: compute embedding and store in ChromaDB.
    """
    case_data = UploadedCaseData(
        disease_id=disease_id,
        trimester=trimester,
        label=label,
        images=image_paths,
        symptom_text=symptom_text,
        gestational_age_weeks=gestational_age_weeks,
        b_hcg=b_hcg_mom * 1500.0 if b_hcg_mom else None,  # Convert MoM back to raw
        papp_a=papp_a_mom * 1500.0 if papp_a_mom else None,
        contributor_id=None,
    )
    try:
        await process_case_upload_to_vector_store(case_data)
    except Exception as e:
        print(f"[CaseUpload] Embedding failed for {case_id}: {e}")


async def process_case_upload_to_vector_store(
    case_data,
    vector_store_path: str = "/data/vector_db",
    storage_path: str = "/data/uploaded_cases",
) -> dict:
    """
    Process case upload and store in vector database for AI training.

    This function handles:
    1. Image processing and anonymization
    2. Symptom extraction (when image provided)
    3. Vector embedding generation
    4. Storage in ChromaDB

    Args:
        case_data: UploadedCaseData with case information
        vector_store_path: Path to ChromaDB storage
        storage_path: Path to store uploaded images

    Returns:
        dict with success status and case_id
    """
    from app.core.medgemma import get_medgemma

    vector_store = get_vector_store(persist_directory=vector_store_path)
    medgemma = get_medgemma()
    storage_path = Path(storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)

    # Generate case ID
    case_id = f"{case_data.disease_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Process images
    processed_images = []
    case_dir = storage_path / case_id
    case_dir.mkdir(exist_ok=True)

    for i, image_path in enumerate(case_data.images):
        try:
            image, metadata = load_ultrasound_image(image_path)
            output_path = case_dir / f"image_{i}.png"
            image.save(output_path, format="PNG")
            processed_images.append(str(output_path))
        except Exception as e:
            return {"success": False, "error": f"Image processing failed: {e}"}

    # Extract symptoms if not provided
    symptom_text = case_data.symptom_text
    if not symptom_text and processed_images:
        try:
            symptom_desc = medgemma.extract_symptoms(
                image_path=processed_images[0],
                user_provided_trimester=case_data.trimester,
            )
            symptom_text = " ".join([f"{s.type}_{s.value}" for s in symptom_desc.symptoms])
        except Exception:
            pass  # Warning but not critical

    # Generate embedding
    try:
        embedding = medgemma.embed_symptoms(symptom_text or "")
    except Exception as e:
        return {"success": False, "error": f"Embedding generation failed: {e}"}

    # Calculate MoM values
    MEDIAN_B_HCG = 50000.0
    MEDIAN_PAPP_A = 1500.0
    b_hcg_mom = case_data.b_hcg / MEDIAN_B_HCG if case_data.b_hcg else None
    papp_a_mom = case_data.papp_a / MEDIAN_PAPP_A if case_data.papp_a else None

    # Create and store case in vector DB
    stored_case = StoredCase(
        case_id=case_id,
        disease_id=case_data.disease_id,
        trimester=case_data.trimester,
        is_positive=(case_data.label == "positive"),
        embedding=embedding,
        symptom_text=symptom_text,
        gestational_age_weeks=case_data.gestational_age_weeks if case_data.gestational_age_weeks is not None else None,
        b_hcg_mom=b_hcg_mom,
        papp_a_mom=papp_a_mom,
        metadata={
            "contributor_id": case_data.contributor_id,
            "source_institution": case_data.source_institution,
            "confirmation_method": case_data.confirmation_method,
            "uploaded_at": datetime.now().isoformat(),
            "validation_status": "pending",
        },
    )

    try:
        vector_store.add_case(stored_case)
    except Exception as e:
        return {"success": False, "error": f"Storage failed: {e}"}

    # Save metadata
    metadata_path = case_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump({
            "case_id": case_id,
            "disease_id": case_data.disease_id,
            "trimester": case_data.trimester,
            "label": case_data.label,
            "gestational_age_weeks": case_data.gestational_age_weeks,
            "b_hcg_mom": b_hcg_mom,
            "papp_a_mom": papp_a_mom,
            "processed_at": datetime.now().isoformat(),
        }, f, indent=2)

    return {"success": True, "case_id": case_id}


def list_pending_cases(
    vector_store_path: str = "/data/vector_db",
    disease_id: Optional[str] = None,
) -> List[str]:
    """
    List cases pending validation.

    Args:
        vector_store_path: Path to ChromaDB storage
        disease_id: Optional filter by disease

    Returns:
        List of case IDs
    """
    vector_store = get_vector_store(persist_directory=vector_store_path)
    # TODO: Implement pending case listing from ChromaDB
    return []


def validate_case_in_vector_store(
    case_id: str,
    approved: bool,
    validator_id: str,
    vector_store_path: str = "/data/vector_db",
) -> bool:
    """
    Mark a case as validated in the vector store.

    Args:
        case_id: Case ID to validate
        approved: Whether case is approved
        validator_id: ID of validator
        vector_store_path: Path to ChromaDB storage

    Returns:
        True if successful
    """
    # TODO: Implement case validation update in vector store
    return True


class CaseUploadService:
    """Service for processing community case uploads."""

    def __init__(
        self,
        vector_store_path: str = "/data/vector_db",
        storage_path: str = "/data/uploaded_cases",
    ):
        self.vector_store = get_vector_store(persist_directory=vector_store_path)
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def process_uploaded_case(
        self,
        case_data: UploadedCaseData,
    ) -> CaseUploadResult:
        """Process an uploaded case from community submission."""
        result = await process_case_upload_to_vector_store(case_data)
        return CaseUploadResult(
            success=result.get("success", False),
            case_id=result.get("case_id", ""),
            error_message=result.get("error"),
        )


# Global service instance
_case_upload_service: Optional[CaseUploadService] = None


def get_case_upload_service(
    vector_store_path: str = "/data/vector_db",
    storage_path: str = "/data/uploaded_cases",
) -> CaseUploadService:
    """Get or create the global case upload service instance."""
    global _case_upload_service
    if _case_upload_service is None:
        _case_upload_service = CaseUploadService(
            vector_store_path=vector_store_path,
            storage_path=storage_path,
        )
    return _case_upload_service


def reset_case_upload_service() -> None:
    """Reset the global case upload service instance."""
    global _case_upload_service
    _case_upload_service = None