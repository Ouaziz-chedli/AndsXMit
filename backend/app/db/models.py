"""Database models for SQLAlchemy + SQLite."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Disease(Base):
    """Disease reference table."""

    __tablename__ = "diseases"

    disease_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    base_prevalence: Mapped[float] = mapped_column(Float, default=1.0)
    trimester_profiles: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string


class CommunityCase(Base):
    """Community-contributed case for vector DB."""

    __tablename__ = "community_cases"

    case_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    disease_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trimester: Mapped[Literal["1st", "2nd", "3rd"]] = mapped_column(String(10), nullable=False)
    images: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of paths
    symptom_text: Mapped[str] = mapped_column(Text, nullable=False)
    gestational_age_weeks: Mapped[float] = mapped_column(Float, nullable=False)
    b_hcg_mom: Mapped[float | None] = mapped_column(Float, nullable=True)
    papp_a_mom: Mapped[float | None] = mapped_column(Float, nullable=True)
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    contributor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiagnosisTask(Base):
    """Background diagnosis task tracking."""

    __tablename__ = "diagnosis_tasks"

    task_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[Literal["pending", "completed", "failed"]] = mapped_column(
        String(20), default="pending"
    )
    images: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list
    trimester: Mapped[str] = mapped_column(String(10), nullable=False)
    patient_context: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    results: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON results
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Contributor(Base):
    """Contributor (doctor/institution)."""

    __tablename__ = "contributors"

    contributor_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=True)
    license_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    contribution_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_status: Mapped[Literal["pending", "approved", "rejected"]] = mapped_column(
        String(20), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
