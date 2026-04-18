"""
Case Upload Service - Handle community case submissions.

This service processes cases uploaded by medical professionals,
including validation, anonymization, and storage in the vector database.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field

from ..core.medgemma import get_medgemma
from ..core.vector_store import get_vector_store, StoredCase
from ..core.image_processor import (
    load_ultrasound_image,
    anonymize_dicom,
    image_to_bytes,
)
from ..models.case import DiseaseCase, ImageData
from .validation import (
    validate_case_submission,
    ValidationResult,
)


@dataclass
class CaseUploadResult:
    """Result of case upload processing."""
    success: bool
    case_id: str
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    validation_results: Optional[ValidationResult] = None


@dataclass
class UploadedCaseData:
    """Data for a case being uploaded."""
    # Required fields
    disease_id: str
    trimester: str
    label: str  # "positive" or "negative"
    images: List[str]  # Paths to image files

    # Optional fields
    symptom_text: Optional[str] = None
    gestational_age_weeks: Optional[float] = None
    b_hcg: Optional[float] = None
    papp_a: Optional[float] = None
    mother_age: Optional[int] = None

    # Metadata
    contributor_id: Optional[str] = None
    source_institution: str = ""
    confirmation_method: str = ""


class CaseUploadService:
    """Service for processing community case uploads."""

    def __init__(
        self,
        vector_store_path: str = "/data/vector_db",
        storage_path: str = "/data/uploaded_cases",
    ):
        """
        Initialize the case upload service.

        Args:
            vector_store_path: Path to ChromaDB storage
            storage_path: Path to store uploaded images
        """
        self.vector_store = get_vector_store(persist_directory=vector_store_path)
        self.medgemma = get_medgemma()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def process_uploaded_case(
        self,
        case_data: UploadedCaseData,
    ) -> CaseUploadResult:
        """
        Process an uploaded case from community submission.

        Args:
            case_data: Data for the case being uploaded

        Returns:
            CaseUploadResult with processing status
        """
        # Generate case ID
        case_id = self._generate_case_id(case_data.disease_id)

        # Step 1: Validate the submission
        validation_result = validate_case_submission(case_data)
        if not validation_result.is_valid:
            return CaseUploadResult(
                success=False,
                case_id=case_id,
                error_message="Validation failed",
                validation_results=validation_result,
            )

        # Step 2: Process images
        try:
            processed_images = await self._process_images(
                case_data.images,
                case_id,
            )
        except Exception as e:
            return CaseUploadResult(
                success=False,
                case_id=case_id,
                error_message=f"Image processing failed: {str(e)}",
            )

        # Step 3: Extract symptoms if not provided
        symptom_text = case_data.symptom_text
        if not symptom_text and processed_images:
            try:
                symptom_text = await self._extract_symptoms(
                    processed_images[0],
                    case_data.trimester,
                )
            except Exception as e:
                # Warning but not critical
                pass

        # Step 4: Generate embeddings
        try:
            embedding = self._generate_embedding(symptom_text)
        except Exception as e:
            return CaseUploadResult(
                success=False,
                case_id=case_id,
                error_message=f"Embedding generation failed: {str(e)}",
            )

        # Step 5: Calculate MoM values
        b_hcg_mom, papp_a_mom = self._calculate_mom_values(
            case_data.b_hcg,
            case_data.papp_a,
            case_data.gestational_age_weeks,
        )

        # Step 6: Create and store the case
        try:
            stored_case = StoredCase(
                case_id=case_id,
                disease_id=case_data.disease_id,
                trimester=case_data.trimester,
                is_positive=(case_data.label == "positive"),
                embedding=embedding,
                symptom_text=symptom_text,
                gestational_age_weeks=case_data.gestational_age_weeks or 0.0,
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

            self.vector_store.add_case(stored_case)

        except Exception as e:
            return CaseUploadResult(
                success=False,
                case_id=case_id,
                error_message=f"Storage failed: {str(e)}",
            )

        # Step 7: Save metadata
        self._save_case_metadata(case_id, case_data, stored_case)

        return CaseUploadResult(
            success=True,
            case_id=case_id,
            validation_results=validation_result,
        )

    async def batch_upload(
        self,
        cases: List[UploadedCaseData],
    ) -> List[CaseUploadResult]:
        """
        Process multiple uploaded cases.

        Args:
            cases: List of case data

        Returns:
            List of upload results
        """
        results = []

        for case_data in cases:
            result = await self.process_uploaded_case(case_data)
            results.append(result)

        return results

    async def _process_images(
        self,
        image_paths: List[str],
        case_id: str,
    ) -> List[str]:
        """
        Process and store uploaded images.

        Args:
            image_paths: Paths to original images
            case_id: ID of the case

        Returns:
            List of paths to processed images
        """
        processed_paths = []

        # Create directory for this case
        case_dir = self.storage_path / case_id
        case_dir.mkdir(exist_ok=True)

        for i, image_path in enumerate(image_paths):
            # Load image
            image, metadata = load_ultrasound_image(image_path)

            # Anonymize if DICOM
            if image_path.lower().endswith(('.dcm', '.dicom')):
                # TODO: Implement DICOM anonymization
                pass

            # Convert to PNG for consistent format
            output_path = case_dir / f"image_{i}.png"
            image.save(output_path, format="PNG")
            processed_paths.append(str(output_path))

        return processed_paths

    async def _extract_symptoms(
        self,
        image_path: str,
        trimester: str,
    ) -> str:
        """
        Extract symptoms from image using MedGemma.

        Args:
            image_path: Path to image
            trimester: Trimester context

        Returns:
            Symptom description text
        """
        symptom_desc = self.medgemma.extract_symptoms(
            image_path=image_path,
            user_provided_trimester=trimester,
        )

        # Format symptoms as text
        symptoms_list = [
            f"{s.type}_{s.value}" for s in symptom_desc.symptoms
        ]
        return " ".join(symptoms_list)

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding from symptom text.

        Args:
            text: Symptom description text

        Returns:
            Embedding vector
        """
        return self.medgemma.embed_symptoms(text)

    def _calculate_mom_values(
        self,
        b_hcg: Optional[float],
        papp_a: Optional[float],
        gestational_age_weeks: Optional[float],
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Calculate MoM (Multiple of Median) values for biomarkers.

        Args:
            b_hcg: Raw b-hCG value (IU/L)
            papp_a: Raw PAPP-A value (IU/L)
            gestational_age_weeks: Gestational age

        Returns:
            Tuple of (b_hcg_mom, papp_a_mom)
        """
        # Median values at 12 weeks (typical screening)
        MEDIAN_B_HCG = 50000.0
        MEDIAN_PAPP_A = 1500.0

        b_hcg_mom = b_hcg / MEDIAN_B_HCG if b_hcg else None
        papp_a_mom = papp_a / MEDIAN_PAPP_A if papp_a else None

        return b_hcg_mom, papp_a_mom

    def _generate_case_id(self, disease_id: str) -> str:
        """
        Generate a unique case ID.

        Args:
            disease_id: Disease identifier

        Returns:
            Unique case ID string
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = os.urandom(4).hex()
        return f"{disease_id}_{timestamp}_{random_suffix}"

    def _save_case_metadata(
        self,
        case_id: str,
        case_data: UploadedCaseData,
        stored_case: StoredCase,
    ) -> None:
        """
        Save case metadata to JSON file.

        Args:
            case_id: Case ID
            case_data: Original uploaded data
            stored_case: Processed stored case
        """
        metadata_path = self.storage_path / case_id / "metadata.json"

        metadata = {
            "case_id": case_id,
            "original_submission": {
                "disease_id": case_data.disease_id,
                "trimester": case_data.trimester,
                "label": case_data.label,
                "gestational_age_weeks": case_data.gestational_age_weeks,
                "b_hcg": case_data.b_hcg,
                "papp_a": case_data.papp_a,
                "mother_age": case_data.mother_age,
            },
            "stored_case": {
                "disease_id": stored_case.disease_id,
                "trimester": stored_case.trimester,
                "is_positive": stored_case.is_positive,
                "gestational_age_weeks": stored_case.gestational_age_weeks,
                "b_hcg_mom": stored_case.b_hcg_mom,
                "papp_a_mom": stored_case.papp_a_mom,
            },
            "processed_at": datetime.now().isoformat(),
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def list_pending_cases(
        self,
        disease_id: Optional[str] = None,
    ) -> List[str]:
        """
        List cases pending validation.

        Args:
            disease_id: Optional filter by disease

        Returns:
            List of case IDs
        """
        # TODO: Implement pending case listing
        # This would query cases with validation_status="pending"
        return []

    def validate_case(
        self,
        case_id: str,
        approved: bool,
        validator_id: str,
        comments: Optional[str] = None,
    ) -> bool:
        """
        Mark a case as validated.

        Args:
            case_id: Case ID to validate
            approved: Whether case is approved
            validator_id: ID of validator
            comments: Optional validation comments

        Returns:
            True if successful
        """
        # TODO: Implement case validation
        # This would update validation_status in metadata
        return True


# Global service instance
_case_upload_service: Optional[CaseUploadService] = None


def get_case_upload_service(
    vector_store_path: str = "/data/vector_db",
    storage_path: str = "/data/uploaded_cases",
) -> CaseUploadService:
    """
    Get or create the global case upload service instance.

    Args:
        vector_store_path: Path to ChromaDB storage
        storage_path: Path to store uploaded images

    Returns:
        CaseUploadService instance
    """
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
