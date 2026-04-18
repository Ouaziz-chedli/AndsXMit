"""Diagnosis service layer - orchestrates AI pipeline calls."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import DiagnosisTaskRepository
from app.db.models import DiagnosisTask
from app.models import DiagnosisResult, PatientContext

# Mock diagnosis results for MVP
MOCK_RESULTS = [
    {
        "disease_id": "down_syndrome",
        "disease_name": "Down Syndrome (Trisomy 21)",
        "final_score": 0.65,
        "confidence_interval": [0.55, 0.75],
        "applied_priors": ["maternal_age_35", "ivf_conception"],
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
    {
        "disease_id": "cardiac_defect",
        "disease_name": "Congenital Cardiac Defect",
        "final_score": 0.15,
        "confidence_interval": [0.10, 0.22],
        "applied_priors": [],
        "matching_positive_cases": [
            {"case_id": "mock_cd_pos_001", "similarity": 0.38},
        ],
        "matching_negative_cases": [
            {"case_id": "mock_neg_004", "similarity": 0.55},
        ],
    },
    {
        "disease_id": "neural_tube_defect",
        "disease_name": "Neural Tube Defect",
        "final_score": 0.05,
        "confidence_interval": [0.02, 0.10],
        "applied_priors": [],
        "matching_positive_cases": [],
        "matching_negative_cases": [
            {"case_id": "mock_neg_005", "similarity": 0.80},
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
    # Adjust mock results based on patient context
    results = []
    for r in MOCK_RESULTS:
        applied_priors = list(r["applied_priors"])

        # Add maternal age prior if applicable
        if patient_context.mother_age >= 35:
            applied_priors.append(f"maternal_age_{patient_context.mother_age}")

        # Adjust score for IVF
        if patient_context.ivf_conception and r["disease_id"] == "down_syndrome":
            applied_priors.append("ivf_conception")

        # Adjust for previous affected pregnancy
        if patient_context.previous_affected_pregnancy:
            applied_priors.append("previous_affected_pregnancy")
            score = r["final_score"] * 1.5  # Increase risk
        else:
            score = r["final_score"]

        # Adjust for biomarker patterns if provided
        if patient_context.b_hcg and patient_context.papp_a:
            if r["disease_id"] == "down_syndrome":
                # High b-hCG + low PAPP-A = increased risk
                if patient_context.b_hcg > 50000 and patient_context.papp_a < 1500:
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

    # Sort by score descending
    results.sort(key=lambda x: x.final_score, reverse=True)

    return results


def run_comprehensive_background(
    task_id: str,
    image_paths: list[str],
    trimester: str,
    patient_context: PatientContext,
    db: Session | None = None,
) -> None:
    """
    Background task for comprehensive scan.

    In production, would query ALL diseases in the knowledge base,
    not just top 5. For MVP, this just simulates processing.
    """
    # Simulate processing time
    time.sleep(2)

    # Generate comprehensive results (same as fast track for MVP)
    results = run_diagnosis_mock(patient_context, trimester)

    # In production, would store results in DB
    # For MVP, we just update the task status
    if db:
        task_repo = DiagnosisTaskRepository(db)
        task_repo.update_status(
            task_id=task_id,
            status="completed",
            results=json.dumps([r.model_dump() for r in results]),
        )
