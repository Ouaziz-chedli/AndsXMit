"""API module exports."""

from app.api.cases import router as cases_router
from app.api.diagnosis import router as diagnosis_router
from app.api.diseases import router as diseases_router
from app.api.llm import router as llm_router

__all__ = ["diagnosis_router", "cases_router", "diseases_router", "llm_router"]
