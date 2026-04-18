from pydantic import BaseModel
from typing import List, Optional, Literal, Tuple
from datetime import datetime
from .patient import PatientContext
from .case import BiometricContext


class Symptom(BaseModel):
    type: str
    value: str
    assessment: str
    normal_range: Optional[str] = None


class SymptomDescription(BaseModel):
    symptoms: List[Symptom]
    overall: str


class RetrievedCase(BaseModel):
    case_id: str
    similarity: float
    is_positive: bool


class DiagnosisResult(BaseModel):
    disease_id: str
    disease_name: str
    final_score: float
    confidence_interval: Tuple[float, float]
    applied_priors: List[str]
    matching_positive_cases: List[dict] = []
    matching_negative_cases: List[dict] = []


class DiagnosisQuery(BaseModel):
    trimester: Literal["1st", "2nd", "3rd"]
    patient_context: PatientContext
    biometric_context: Optional[BiometricContext] = None
    top_k: int = 10


class DiagnosisReport(BaseModel):
    fast_track: List[DiagnosisResult]
    comprehensive: Optional[List[DiagnosisResult]] = None
    processing_time_ms: int
    timestamp: datetime


class DiagnosisResponse(BaseModel):
    """Response from diagnosis endpoint."""

    fast_track: list[DiagnosisResult]
    comprehensive_pending: bool
    comprehensive_callback_url: str | None = None
    fast_track_ms: int
    timestamp: datetime


class ComprehensiveResult(BaseModel):
    """Comprehensive scan result (async)."""

    task_id: str
    status: Literal["pending", "completed", "failed"]
    results: list[DiagnosisResult] | None = None
    completed_at: datetime | None = None