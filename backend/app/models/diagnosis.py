"""Pydantic models for PrenatalAI diagnosis."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PatientContext(BaseModel):
    """
    First-trimester screening context.
    Based on French NT-prenatal screening protocol (11-14 weeks).
    """

    b_hcg: float | None = Field(None, description="IU/L, serum biomarker")
    papp_a: float | None = Field(None, description="IU/L, serum biomarker")
    mother_age: int = Field(..., description="Age at due date")
    gestational_age_weeks: float = Field(..., description="Weeks since LMP")
    # Optional modifiers
    fetal_count: int = Field(1, description="Number of fetuses")
    ivf_conception: bool = Field(False, description="IVF conception")
    previous_affected_pregnancy: bool = Field(False, description="Prior chromosomal anomaly")


class PatientContextMoM(BaseModel):
    """MoM-normalized patient context for risk calculation."""

    b_hcg_mom: float | None = None
    papp_a_mom: float | None = None
    mother_age: int
    gestational_age_weeks: float
    previous_affected_pregnancy: bool = False


class DiagnosisResult(BaseModel):
    """Single disease diagnosis result."""

    disease_id: str
    disease_name: str
    final_score: float
    confidence_interval: tuple[float, float]
    applied_priors: list[str]
    matching_positive_cases: list[dict] = Field(default_factory=list)
    matching_negative_cases: list[dict] = Field(default_factory=list)


class DiagnosisResponse(BaseModel):
    """Response from diagnosis endpoint."""

    fast_track: list[DiagnosisResult]
    comprehensive_pending: bool
    comprehensive_callback_url: str | None = None
    fast_track_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ComprehensiveResult(BaseModel):
    """Comprehensive scan result (async)."""

    task_id: str
    status: Literal["pending", "completed", "failed"]
    results: list[DiagnosisResult] | None = None
    completed_at: datetime | None = None


class ImageData(BaseModel):
    """Image data for diagnosis."""

    filename: str
    content_type: str
    # Stored as bytes in memory, not persisted path
