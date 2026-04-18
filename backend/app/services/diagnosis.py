"""
Diagnosis Service - Orchestrates the complete diagnosis pipeline.

This service coordinates all core modules to perform a complete prenatal
disease diagnosis from ultrasound images.

Pipeline:
1. Image Processing → PIL Image + Metadata
2. MedGemma → Symptom Extraction
3. Vector Store → Similar Case Retrieval
4. Scoring → Raw Score Calculation
5. Aggregation → Trimester Weighting
6. Priors → Bayesian Prior Application
7. Result → Final Diagnosis Report
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field

from ..core.medgemma import (
    get_medgemma,
    SymptomDescription,
)
from ..core.vector_store import (
    get_vector_store,
    RetrievedCase,
)
from ..core.scoring import (
    calculate_raw_score,
    calculate_confidence_interval,
)
from ..core.aggregation import (
    aggregate_scores,
    get_available_diseases,
)
from ..core.priors import (
    apply_priors,
    get_applied_priors,
)
from ..core.image_processor import (
    load_ultrasound_image,
    image_to_bytes,
    UltrasoundMetadata,
)
from ..models.diagnosis import (
    DiagnosisQuery,
    DiagnosisResult,
    DiagnosisReport,
)
from ..models.patient import PatientContext


@dataclass
class DiagnosisIntermediateResults:
    """Intermediate results during diagnosis pipeline."""
    image_metadata: Optional[UltrasoundMetadata] = None
    symptom_description: Optional[SymptomDescription] = None
    symptom_embedding: Optional[List[float]] = None
    positive_cases: List[RetrievedCase] = field(default_factory=list)
    negative_cases: List[RetrievedCase] = field(default_factory=list)
    raw_score: Optional[float] = None
    weighted_score: Optional[float] = None
    final_score: Optional[float] = None
    confidence_interval: Optional[tuple[float, float]] = None


class DiagnosisService:
    """Service for orchestrating prenatal diagnosis."""

    def __init__(
        self,
        vector_store_path: str = "/data/vector_db",
    ):
        """
        Initialize the diagnosis service.

        Args:
            vector_store_path: Path to ChromaDB storage
        """
        self.vector_store = get_vector_store(persist_directory=vector_store_path)
        self.medgemma = get_medgemma()

    async def diagnose_from_image(
        self,
        image_path: str,
        query: DiagnosisQuery,
    ) -> DiagnosisResult:
        """
        Perform complete diagnosis from an image file.

        Args:
            image_path: Path to ultrasound image
            query: Diagnosis query with trimester and patient context

        Returns:
            DiagnosisResult with final score and explanation
        """
        intermediate = DiagnosisIntermediateResults()

        # Step 1: Load image and extract metadata
        intermediate.image_metadata = await self._load_image(image_path)

        # Determine trimester (from query or metadata)
        trimester = query.trimester or intermediate.image_metadata.trimester
        if trimester is None:
            raise ValueError(
                "Trimester must be provided either in query or "
                "extractable from image metadata."
            )

        # Step 2: Extract symptoms using MedGemma
        intermediate.symptom_description = await self._extract_symptoms(
            image_path,
            trimester,
            intermediate.image_metadata.gestational_age_weeks
        )

        # Step 3: Generate symptom embedding
        intermediate.symptom_embedding = self.medgemma.embed_symptoms(
            intermediate.symptom_description.symptom_text
        )

        # Step 4: Search for similar cases (single disease for MVP)
        disease_id = "down_syndrome"  # MVP: single disease
        await self._search_similar_cases(
            intermediate.symptom_embedding,
            disease_id,
            trimester,
            intermediate,
        )

        # Step 5: Calculate raw score
        await self._calculate_raw_score(intermediate)

        # Step 6: Apply trimester weighting
        await self._apply_trimester_weighting(
            intermediate,
            disease_id,
            trimester,
        )

        # Step 7: Apply priors
        await self._apply_priors(
            intermediate,
            disease_id,
            query.patient_context,
        )

        # Step 8: Calculate confidence interval
        await self._calculate_confidence_interval(intermediate)

        # Step 9: Generate result
        return self._generate_result(
            intermediate,
            disease_id,
            trimester,
            query.patient_context,
        )

    async def diagnose_multiple_diseases(
        self,
        image_path: str,
        query: DiagnosisQuery,
        disease_ids: Optional[List[str]] = None,
    ) -> List[DiagnosisResult]:
        """
        Perform diagnosis for multiple diseases.

        Args:
            image_path: Path to ultrasound image
            query: Diagnosis query
            disease_ids: List of diseases to check (default: all)

        Returns:
            List of DiagnosisResults, sorted by final_score descending
        """
        if disease_ids is None:
            disease_ids = get_available_diseases()

        results = []

        for disease_id in disease_ids:
            try:
                result = await self.diagnose_from_image(image_path, query)
                # Update disease_id in result
                result = DiagnosisResult(
                    disease_id=disease_id,
                    disease_name=self._get_disease_name(disease_id),
                    final_score=result.final_score,
                    confidence_interval=result.confidence_interval,
                    applied_priors=result.applied_priors,
                )
                results.append(result)
            except Exception as e:
                # Log error and continue with other diseases
                print(f"Error diagnosing {disease_id}: {e}")

        # Sort by final_score (descending)
        results.sort(key=lambda x: x.final_score, reverse=True)

        return results

    async def _load_image(self, image_path: str) -> UltrasoundMetadata:
        """Load image and extract metadata."""
        image, metadata = load_ultrasound_image(image_path)
        return metadata

    async def _extract_symptoms(
        self,
        image_path: str,
        trimester: str,
        gestational_age_weeks: Optional[float],
    ) -> SymptomDescription:
        """Extract symptoms using MedGemma."""
        return self.medgemma.extract_symptoms(
            image_path=image_path,
            user_provided_trimester=trimester,
        )

    async def _search_similar_cases(
        self,
        embedding: List[float],
        disease_id: str,
        trimester: str,
        intermediate: DiagnosisIntermediateResults,
    ) -> None:
        """Search for similar cases in vector store."""
        # Search positive cases
        intermediate.positive_cases = self.vector_store.search_disease(
            query_embedding=embedding,
            disease_id=disease_id,
            trimester=trimester,
            top_k=10,
            filter_positive=True,
        )

        # Search negative cases
        intermediate.negative_cases = self.vector_store.search_disease(
            query_embedding=embedding,
            disease_id=disease_id,
            trimester=trimester,
            top_k=10,
            filter_positive=False,
        )

    async def _calculate_raw_score(
        self,
        intermediate: DiagnosisIntermediateResults,
    ) -> None:
        """Calculate raw score from similarity scores."""
        positive_sims = [c.similarity for c in intermediate.positive_cases]
        negative_sims = [c.similarity for c in intermediate.negative_cases]

        intermediate.raw_score = calculate_raw_score(positive_sims, negative_sims)

    async def _apply_trimester_weighting(
        self,
        intermediate: DiagnosisIntermediateResults,
        disease_id: str,
        trimester: str,
    ) -> None:
        """Apply trimester-specific weighting."""
        intermediate.weighted_score = aggregate_scores(
            intermediate.raw_score,
            disease_id,
            trimester,
        )

    async def _apply_priors(
        self,
        intermediate: DiagnosisIntermediateResults,
        disease_id: str,
        patient_context: PatientContext,
    ) -> None:
        """Apply Bayesian priors."""
        intermediate.final_score = apply_priors(
            intermediate.weighted_score,
            disease_id,
            patient_context,
        )

    async def _calculate_confidence_interval(
        self,
        intermediate: DiagnosisIntermediateResults,
    ) -> None:
        """Calculate confidence interval for the result."""
        positive_sims = [c.similarity for c in intermediate.positive_cases]
        negative_sims = [c.similarity for c in intermediate.negative_cases]

        intermediate.confidence_interval = calculate_confidence_interval(
            positive_sims,
            negative_sims,
            confidence=0.95,
        )

    def _generate_result(
        self,
        intermediate: DiagnosisIntermediateResults,
        disease_id: str,
        trimester: str,
        patient_context: PatientContext,
    ) -> DiagnosisResult:
        """Generate final DiagnosisResult."""
        # Get list of applied priors for explanation
        applied_priors = get_applied_priors(disease_id, patient_context)

        return DiagnosisResult(
            disease_id=disease_id,
            disease_name=self._get_disease_name(disease_id),
            final_score=intermediate.final_score,
            confidence_interval=intermediate.confidence_interval,
            applied_priors=applied_priors,
        )

    def _get_disease_name(self, disease_id: str) -> str:
        """Get human-readable disease name."""
        disease_names = {
            "down_syndrome": "Down Syndrome (Trisomy 21)",
            "edwards_syndrome": "Edwards Syndrome (Trisomy 18)",
            "patau_syndrome": "Patau Syndrome (Trisomy 13)",
            "cardiac_defect": "Cardiac Defect",
            "neural_tube_defect": "Neural Tube Defect",
            "skeletal_dysplasia": "Skeletal Dysplasia",
        }
        return disease_names.get(disease_id, disease_id)


# Global service instance
_diagnosis_service: Optional[DiagnosisService] = None


def get_diagnosis_service(
    vector_store_path: str = "/data/vector_db",
) -> DiagnosisService:
    """
    Get or create the global diagnosis service instance.

    Args:
        vector_store_path: Path to ChromaDB storage

    Returns:
        DiagnosisService instance
    """
    global _diagnosis_service
    if _diagnosis_service is None:
        _diagnosis_service = DiagnosisService(vector_store_path=vector_store_path)
    return _diagnosis_service


def reset_diagnosis_service() -> None:
    """Reset the global diagnosis service instance."""
    global _diagnosis_service
    _diagnosis_service = None


# Convenience function for diagnosis
async def diagnose(
    image_path: str,
    query: DiagnosisQuery,
) -> DiagnosisResult:
    """
    Convenience function for single disease diagnosis.

    Args:
        image_path: Path to ultrasound image
        query: Diagnosis query

    Returns:
        DiagnosisResult
    """
    service = get_diagnosis_service()
    return await service.diagnose_from_image(image_path, query)
