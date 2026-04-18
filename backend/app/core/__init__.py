"""
Core modules for the AI/ML pipeline.

This package contains the core AI/ML functionality:
- MedGemma: Symptom extraction from images
- Vector Store: ChromaDB similarity search
- Scoring: Raw score calculation
- Aggregation: Trimester-weighted scores
- Priors: Bayesian prior calculations
- Image Processor: DICOM/JPEG/PNG handling
- Fetal Measurements: BPD centile lookup and size assessment
- Biometric Context: AI prompt fragment builder
"""

from .medgemma import (
    MedGemma,
    MedGemmaError,
    Symptom,
    SymptomDescription,
    get_medgemma,
    extract_symptoms,
    extract_symptoms_from_bytes,
)

from .ollama_client import (
    OllamaClient,
    get_ollama_client,
    reset_ollama_client,
)

from .vector_store import (
    VectorStore,
    RetrievedCase,
    StoredCase,
    get_vector_store,
    reset_vector_store,
)

from .scoring import (
    calculate_raw_score,
    calculate_confidence_interval,
)

from .aggregation import (
    TRIMESTER_WEIGHTS,
    aggregate_scores,
    get_available_diseases,
    get_disease_weight,
    update_trimester_weight,
)

from .priors import (
    calculate_age_risk,
    calculate_biomarker_risk,
    apply_priors,
    get_applied_priors,
)

from .image_processor import (
    UltrasoundMetadata,
    load_ultrasound_image,
    image_to_bytes,
    anonymize_dicom,
    get_image_format,
    validate_image,
)

from .fetal_measurements import (
    get_bpd_reference,
    get_bpd_centile,
    compute_size_assessment,
    check_head_shape,
    BPDReference,
    BPDCentileResult,
    SizeAssessment,
    HeadShapeResult,
)

from .biometric_context import (
    compute_biometric_context,
    build_biometric_prompt,
)

__all__ = [
    # MedGemma
    "MedGemma",
    "MedGemmaError",
    "Symptom",
    "SymptomDescription",
    "get_medgemma",
    "extract_symptoms",
    "extract_symptoms_from_bytes",
    # Vector Store
    "VectorStore",
    "RetrievedCase",
    "StoredCase",
    "get_vector_store",
    "reset_vector_store",
    # Scoring
    "calculate_raw_score",
    "calculate_confidence_interval",
    # Aggregation
    "TRIMESTER_WEIGHTS",
    "aggregate_scores",
    "get_available_diseases",
    "get_disease_weight",
    "update_trimester_weight",
    # Priors
    "calculate_age_risk",
    "calculate_biomarker_risk",
    "apply_priors",
    "get_applied_priors",
    # Image Processor
    "UltrasoundMetadata",
    "load_ultrasound_image",
    "image_to_bytes",
    "anonymize_dicom",
    "get_image_format",
    "validate_image",
    # Fetal Measurements
    "get_bpd_reference",
    "get_bpd_centile",
    "compute_size_assessment",
    "check_head_shape",
    "BPDReference",
    "BPDCentileResult",
    "SizeAssessment",
    "HeadShapeResult",
    # Biometric Context
    "compute_biometric_context",
    "build_biometric_prompt",
]