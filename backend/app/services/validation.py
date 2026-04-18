"""Validation service for admin case validation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import CaseRepository, DiagnosisTaskRepository


def validate_case(
    db: Session,
    case_id: str,
    validator_id: str,
    approved: bool,
) -> dict:
    """
    Mark case as validated (or rejected) by admin.

    In production, would check validator permissions.
    """
    case_repo = CaseRepository(db)
    case = case_repo.get_by_id(case_id)

    if not case:
        return {"success": False, "error": "Case not found"}

    if approved:
        case.validated = True
        db.commit()

        # TODO: Trigger re-embedding with validated flag
        return {"success": True, "case_id": case_id, "status": "approved"}
    else:
        # Soft delete or mark as rejected
        # For MVP, just leave as not validated
        return {"success": True, "case_id": case_id, "status": "rejected"}
