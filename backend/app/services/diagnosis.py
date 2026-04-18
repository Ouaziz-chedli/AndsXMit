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

import json
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
        Perform complete diagnosis from an image file (defaults to down_syndrome for MVP).
        """
        return await self._diagnose_single_disease(image_path, query, "down_syndrome")

    async def _diagnose_single_disease(
        self,
        image_path: str,
        query: DiagnosisQuery,
        disease_id: str,
    ) -> DiagnosisResult:
        """
        Run the full pipeline for a single disease.

        Args:
            image_path: Path to ultrasound image
            query: Diagnosis query with trimester and patient context
            disease_id: Which disease to score

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
        intermediate.symptom_embedding = await self.medgemma.embed_symptoms_async(
            intermediate.symptom_description.symptom_text
        )

        # Step 4: Search for similar cases
        await self._search_similar_cases(
            intermediate.symptom_embedding,
            disease_id,
            trimester,
            intermediate,
        )

        # Step 5: Calculate raw score
        await self._calculate_raw_score(intermediate)

        # Guard: if raw_score is somehow None, default to 0.0
        if intermediate.raw_score is None:
            intermediate.raw_score = 0.0

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
                result = await self._diagnose_single_disease(image_path, query, disease_id)
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
        """Extract symptoms using MedGemma (async, safe inside FastAPI)."""
        return await self.medgemma.extract_symptoms_async(
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


# Mock diagnosis for MVP when core modules not available
MOCK_RESULTS = [
    {
        "disease_id": "down_syndrome",
        "disease_name": "Down Syndrome (Trisomy 21)",
        "final_score": 0.65,
        "confidence_interval": [0.55, 0.75],
        "applied_priors": ["maternal_age_35"],
        "matching_positive_cases": [
            {"case_id": "mock_ds_pos_001", "similarity": 0.82},
            {"case_id": "mock_ds_pos_002", "similarity": 0.78},
        ],
        "matching_negative_cases": [
            {"case_id": "mock_neg_001", "similarity": 0.25},
        ],
    },
    {
        "disease_id": "edwards_syndrome",
        "disease_name": "Edwards Syndrome (Trisomy 18)",
        "final_score": 0.12,
        "confidence_interval": [0.08, 0.18],
        "applied_priors": [],
        "matching_positive_cases": [
            {"case_id": "mock_es_pos_001", "similarity": 0.45},
        ],
        "matching_negative_cases": [
            {"case_id": "mock_neg_002", "similarity": 0.60},
        ],
    },
    {
        "disease_id": "patau_syndrome",
        "disease_name": "Patau Syndrome (Trisomy 13)",
        "final_score": 0.08,
        "confidence_interval": [0.04, 0.15],
        "applied_priors": [],
        "matching_positive_cases": [],
        "matching_negative_cases": [
            {"case_id": "mock_neg_003", "similarity": 0.70},
        ],
    },
]


def run_diagnosis_mock(
    patient_context: PatientContext,
    trimester: str,
) -> list[DiagnosisResult]:
    """
    Mock diagnosis implementation for MVP.

    In production, this would call:
    1. Dev1's image_processor to load images
    2. Dev1's medgemma to extract symptoms
    3. Dev1's vector_store to search disease DBs
    4. Dev1's aggregation to score results
    """
    results = []
    for r in MOCK_RESULTS:
        applied_priors = list(r["applied_priors"])

        # Add maternal age prior if applicable
        if patient_context.mother_age >= 35:
            applied_priors.append(f"maternal_age_{patient_context.mother_age}")

        # Adjust for previous affected pregnancy
        if patient_context.previous_affected_pregnancy:
            applied_priors.append("previous_affected_pregnancy")
            score = r["final_score"] * 1.5
        else:
            score = r["final_score"]

        # Adjust for biomarker patterns if provided — compare using MoM, not raw units
        if patient_context.b_hcg and patient_context.papp_a:
            mom = patient_context.to_mom()
            if r["disease_id"] == "down_syndrome":
                if (mom.b_hcg_mom or 0) > 2.0 and (mom.papp_a_mom or 1) < 0.5:
                    applied_priors.append("biomarker_pattern_ds")
                    score = min(score * 1.3, 1.0)

        results.append(
            DiagnosisResult(
                disease_id=r["disease_id"],
                disease_name=r["disease_name"],
                final_score=round(score, 3),
                confidence_interval=tuple(r["confidence_interval"]),
                applied_priors=applied_priors,
                matching_positive_cases=r["matching_positive_cases"],
                matching_negative_cases=r["matching_negative_cases"],
            )
        )

    results.sort(key=lambda x: x.final_score, reverse=True)
    return results


def run_comprehensive_background(
    task_id: str,
    image_paths: list[str],
    trimester: str,
    patient_context: PatientContext,
) -> None:
    """
    Background task for comprehensive scan.
    Always creates its own DB session — never shares the request session across threads.
    """
    import time
    time.sleep(2)

    results = run_diagnosis_mock(patient_context, trimester)

    from app.db.database import SessionLocal
    from app.db import DiagnosisTaskRepository
    db = SessionLocal()
    try:
        task_repo = DiagnosisTaskRepository(db)
        task_repo.update_status(
            task_id=task_id,
            status="completed",
            results=json.dumps([r.model_dump() for r in results]),
        )
        db.commit()
    except Exception as e:
        print(f"Background task DB write failed for {task_id}: {e}")
    finally:
        db.close()