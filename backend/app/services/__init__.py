"""
Services package - Orchestration layer for business logic.

This package contains services that coordinate the core modules
to implement complete business workflows.
"""

from .diagnosis import (
    DiagnosisService,
    DiagnosisIntermediateResults,
    get_diagnosis_service,
    reset_diagnosis_service,
    diagnose,
)

from .case_upload import (
    CaseUploadService,
    CaseUploadResult,
    UploadedCaseData,
    get_case_upload_service,
    reset_case_upload_service,
)

from .validation import (
    ValidationService,
    ValidationIssue,
    ValidationResult,
    Severity,
    validate_case_submission,
)

__all__ = [
    # Diagnosis
    "DiagnosisService",
    "DiagnosisIntermediateResults",
    "get_diagnosis_service",
    "reset_diagnosis_service",
    "diagnose",
    # Case Upload
    "CaseUploadService",
    "CaseUploadResult",
    "UploadedCaseData",
    "get_case_upload_service",
    "reset_case_upload_service",
    # Validation
    "ValidationService",
    "ValidationIssue",
    "ValidationResult",
    "Severity",
    "validate_case_submission",
]
