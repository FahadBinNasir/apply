from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class InboxModel(Base):
    __tablename__ = "inbox"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), index=True)
    chat_id: Mapped[str] = mapped_column(String(128), index=True)
    chat_name: Mapped[str] = mapped_column(String(256), default="")
    sender: Mapped[str] = mapped_column(String(128), default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    media_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    media_mime: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    message_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    sources: Mapped[List[JobSourceModel]] = relationship("JobSourceModel", back_populates="inbox_item")


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    primary_inbox_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(256), index=True)
    company: Mapped[str] = mapped_column(String(256), index=True)
    field: Mapped[str] = mapped_column(String(128), index=True)
    location_text: Mapped[str] = mapped_column(String(256), default="")
    work_mode: Mapped[str] = mapped_column(String(32), default="unknown")
    city: Mapped[str] = mapped_column(String(128), default="")
    experience_min_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    experience_max_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    responsibilities: Mapped[List[str]] = mapped_column(JSON, default=list)
    deadline: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    shift_text: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    night_shift: Mapped[bool] = mapped_column(Boolean, default=False)
    gender_requirement: Mapped[str] = mapped_column(String(32), default="any")
    apply_method: Mapped[str] = mapped_column(String(32), default="unknown")
    apply_email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    apply_whatsapp: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    apply_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    exact_subject: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    from_image: Mapped[bool] = mapped_column(Boolean, default=False)
    walkin_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    fresh_grad_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tier: Mapped[str] = mapped_column(String(32), index=True, default="STRONG")
    tier_reasons: Mapped[List[str]] = mapped_column(JSON, default=list)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), index=True, default="new")
    fit_summary: Mapped[str] = mapped_column(Text, default="")
    matches: Mapped[List[str]] = mapped_column(JSON, default=list)
    gaps: Mapped[List[str]] = mapped_column(JSON, default=list)
    source_messages: Mapped[List[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)

    sources: Mapped[List[JobSourceModel]] = relationship("JobSourceModel", back_populates="job", cascade="all, delete-orphan")
    draft: Mapped[Optional[DraftModel]] = relationship("DraftModel", back_populates="job", uselist=False, cascade="all, delete-orphan")
    cv_artifact: Mapped[Optional[CVArtifactModel]] = relationship("CVArtifactModel", back_populates="job", uselist=False, cascade="all, delete-orphan")
    sends: Mapped[List[SendModel]] = relationship("SendModel", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_jobs_tier_status", "tier", "status", "created_at"),
        Index("idx_jobs_company_title", "company", "title"),
    )


class JobSourceModel(Base):
    __tablename__ = "job_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), index=True)
    inbox_id: Mapped[str] = mapped_column(String(64), ForeignKey("inbox.id"), index=True)
    source_chat: Mapped[str] = mapped_column(String(256), default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    job: Mapped[JobModel] = relationship("JobModel", back_populates="sources")
    inbox_item: Mapped[InboxModel] = relationship("InboxModel", back_populates="sources")


class DraftModel(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), unique=True, index=True)
    recipient: Mapped[str] = mapped_column(String(256))
    subject: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    is_customized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)

    job: Mapped[JobModel] = relationship("JobModel", back_populates="draft")


class CVArtifactModel(Base):
    __tablename__ = "cv_artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), unique=True, index=True)
    pdf_path: Mapped[str] = mapped_column(String(512))
    preview_png_paths: Mapped[List[str]] = mapped_column(JSON, default=list)
    passes_verifier: Mapped[bool] = mapped_column(Boolean, default=True)
    verifier_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    job: Mapped[JobModel] = relationship("JobModel", back_populates="cv_artifact")


class SendModel(Base):
    __tablename__ = "sends"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), index=True)
    recipient: Mapped[str] = mapped_column(String(256))
    subject: Mapped[str] = mapped_column(String(512))
    gmail_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="sent")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)

    job: Mapped[JobModel] = relationship("JobModel", back_populates="sends")


class SettingsModel(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


class ProfileModel(Base):
    __tablename__ = "profile"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default="default")
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


class QueueModel(Base):
    __tablename__ = "queue"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    queue_name: Mapped[str] = mapped_column(String(64), default="default", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        Index("idx_queue_status_prio", "status", "priority", "next_run_at"),
    )


class LLMUsageModel(Base):
    __tablename__ = "llm_usage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    post_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)


class NoiseLogModel(Base):
    __tablename__ = "noise_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(128))
    chat_id: Mapped[str] = mapped_column(String(128))
    preview: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, index=True)
