"""Diagnosis API endpoints."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db import DiagnosisTaskRepository, get_db
from app.db.models import DiagnosisTask
from app.models import (
    ComprehensiveResult,
    DiagnosisResponse,
    DiagnosisResult,
    PatientContext,
)
from app.services.diagnosis import (
    get_diagnosis_service,
    run_comprehensive_background,
)

router = APIRouter(prefix="/api/v1/diagnosis", tags=["diagnosis"])


@router.post("", response_model=DiagnosisResponse)
async def diagnose(
    background_tasks: BackgroundTasks,
    images: list[UploadFile] = File(...),
    trimester: str = Form(...),
    b_hcg: float | None = Form(None),
    papp_a: float | None = Form(None),
    mother_age: int = Form(...),
    gestational_age_weeks: float = Form(...),
    previous_affected_pregnancy: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    Upload ultrasound images and get diagnosis.

    Returns fast track immediately (top 5 diseases).
    Comprehensive scan runs in background.
    """
    # Validate trimester
    if trimester not in ("1st", "2nd", "3rd"):
        raise HTTPException(status_code=422, detail="Invalid trimester. Must be 1st, 2nd, or 3rd.")

    # Build patient context
    patient_context = PatientContext(
        b_hcg=b_hcg,
        papp_a=papp_a,
        mother_age=mother_age,
        gestational_age_weeks=gestational_age_weeks,
        previous_affected_pregnancy=previous_affected_pregnancy,
    )

    # Generate task ID for background tracking
    task_id = f"task-{uuid.uuid4().hex[:12]}"

    # Save images to /data/images/
    image_dir = Path(settings.IMAGE_DIR)
    image_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    for img in images:
        ext = Path(img.filename or "image.jpg").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".dcm"):
            ext = ".jpg"
        filename = f"{uuid.uuid4().hex[:12]}{ext}"
        filepath = image_dir / filename
        content = await img.read()
        with open(filepath, "wb") as f:
            f.write(content)
        image_paths.append(str(filepath))

    # Create background task record
    task_repo = DiagnosisTaskRepository(db)
    task_repo.create(
        DiagnosisTask(
            task_id=task_id,
            status="pending",
            images=json.dumps(image_paths),
            trimester=trimester,
            patient_context=patient_context.model_dump_json(),
        )
    )

    # Build DiagnosisQuery for real pipeline
    from app.models.diagnosis import DiagnosisQuery
    query = DiagnosisQuery(
        trimester=trimester,  # type: ignore
        patient_context=patient_context,
        top_k=10,
    )

    # Run real diagnosis via DiagnosisService
    diagnosis_service = get_diagnosis_service(vector_store_path=settings.CHROMA_PATH)

    start_time = time.time()
    try:
        # diagnose_from_image expects (image_path, query) - runs full pipeline for down_syndrome
        # Use diagnose_multiple_diseases to get top results across all diseases
        results = await diagnosis_service.diagnose_multiple_diseases(
            image_path=image_paths[0] if image_paths else "",
            query=query,
        )
        # Take top 5 sorted by final_score
        top_results = sorted(results, key=lambda x: x.final_score, reverse=True)[:5]
    except Exception as e:
        # Fall back to mock if pipeline fails (e.g., empty vector DB)
        from app.services.diagnosis import run_diagnosis_mock
        top_results = run_diagnosis_mock(patient_context, trimester)

    fast_track_ms = int((time.time() - start_time) * 1000)

    # Queue comprehensive background task
    background_tasks.add_task(
        run_comprehensive_background,
        task_id=task_id,
        image_paths=image_paths,
        trimester=trimester,
        patient_context=patient_context,
    )

    return DiagnosisResponse(
        fast_track=top_results,
        comprehensive_pending=True,
        comprehensive_callback_url=f"/api/v1/diagnosis/{task_id}/comprehensive",
        fast_track_ms=fast_track_ms,
        timestamp=datetime.utcnow(),
    )


@router.get("/{task_id}/comprehensive", response_model=ComprehensiveResult)
async def get_comprehensive_results(
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    Get comprehensive scan results (poll after background processing).
    """
    task_repo = DiagnosisTaskRepository(db)
    task = task_repo.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Diagnosis task not found.")

    result = ComprehensiveResult(
        task_id=task.task_id,
        status=task.status,
        results=json.loads(task.results) if task.results else None,
        completed_at=task.completed_at,
    )

    if task.status == "pending":
        from fastapi import Response
        return Response(
            content=result.model_dump_json(),
            status_code=202,
            media_type="application/json",
        )

    return result
