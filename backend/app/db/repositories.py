"""CRUD repositories for PrenatalAI database models."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.db.models import CommunityCase, Contributor, DiagnosisTask, Disease


class DiseaseRepository:
    """Repository for Disease operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, disease_id: str) -> Disease | None:
        return self.session.query(Disease).filter(Disease.disease_id == disease_id).first()

    def list_all(self) -> list[Disease]:
        return self.session.query(Disease).all()

    def create(self, disease: Disease) -> Disease:
        self.session.add(disease)
        self.session.commit()
        self.session.refresh(disease)
        return disease

    def seed_defaults(self) -> None:
        """Seed default diseases if empty."""
        if self.session.query(Disease).count() == 0:
            defaults = [
                Disease(
                    disease_id="down_syndrome",
                    name="Down Syndrome (Trisomy 21)",
                    description="Chromosomal condition with intellectual disability",
                    base_prevalence=1.0,
                    trimester_profiles=json.dumps({
                        "1st": {"weight": 0.85, "nt_cutoff_mm": 3.0},
                        "2nd": {"weight": 0.75},
                        "3rd": {"weight": 0.40},
                    }),
                ),
                Disease(
                    disease_id="edwards_syndrome",
                    name="Edwards Syndrome (Trisomy 18)",
                    description="Severe chromosomal abnormality",
                    base_prevalence=0.3,
                    trimester_profiles=json.dumps({
                        "1st": {"weight": 0.80},
                        "2nd": {"weight": 0.85},
                        "3rd": {"weight": 0.50},
                    }),
                ),
                Disease(
                    disease_id="patau_syndrome",
                    name="Patau Syndrome (Trisomy 13)",
                    description="Chromosomal abnormality with severe defects",
                    base_prevalence=0.1,
                    trimester_profiles=json.dumps({
                        "1st": {"weight": 0.75},
                        "2nd": {"weight": 0.80},
                        "3rd": {"weight": 0.45},
                    }),
                ),
            ]
            for d in defaults:
                self.session.add(d)
            self.session.commit()


class CaseRepository:
    """Repository for CommunityCase operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, case: CommunityCase) -> CommunityCase:
        self.session.add(case)
        self.session.commit()
        self.session.refresh(case)
        return case

    def get_by_id(self, case_id: str) -> CommunityCase | None:
        return self.session.query(CommunityCase).filter(CommunityCase.case_id == case_id).first()

    def list(
        self,
        disease: str | None = None,
        trimester: str | None = None,
        validated: bool | None = None,
    ) -> list[CommunityCase]:
        query = self.session.query(CommunityCase)
        if disease:
            query = query.filter(CommunityCase.disease_id == disease)
        if trimester:
            query = query.filter(CommunityCase.trimester == trimester)
        if validated is not None:
            query = query.filter(CommunityCase.validated == validated)
        return query.order_by(CommunityCase.created_at.desc()).all()


class DiagnosisTaskRepository:
    """Repository for DiagnosisTask operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, task: DiagnosisTask) -> DiagnosisTask:
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_by_id(self, task_id: str) -> DiagnosisTask | None:
        return self.session.query(DiagnosisTask).filter(DiagnosisTask.task_id == task_id).first()

    def update_status(
        self,
        task_id: str,
        status: Literal["pending", "completed", "failed"],
        results: str | None = None,
        error: str | None = None,
    ) -> DiagnosisTask | None:
        task = self.get_by_id(task_id)
        if task:
            task.status = status
            if results is not None:
                task.results = results
            if error is not None:
                task.error = error
            if status in ("completed", "failed"):
                task.completed_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(task)
        return task


class ContributorRepository:
    """Repository for Contributor operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, contributor_id: str) -> Contributor | None:
        return self.session.query(Contributor).filter(
            Contributor.contributor_id == contributor_id
        ).first()

    def create(self, contributor: Contributor) -> Contributor:
        self.session.add(contributor)
        self.session.commit()
        self.session.refresh(contributor)
        return contributor

    def increment_contributions(self, contributor_id: str) -> None:
        contributor = self.get_by_id(contributor_id)
        if contributor:
            contributor.contribution_count += 1
            self.session.commit()
