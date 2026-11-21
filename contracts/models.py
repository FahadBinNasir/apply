"""
Core Pydantic models for the WhatsApp Job Agent.
Contracts are frozen in Phase 0. No agent except LEAD may modify this file.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tier(str, Enum):
    STRONG = "STRONG"
    STRETCH = "STRETCH"
    MANUAL = "MANUAL"
    WALKIN = "WALKIN"
    OPPORTUNITY = "OPPORTUNITY"
    SKIPPED = "SKIPPED"
    NOISE = "NOISE"


class Status(str, Enum):
    NEW = "new"
    DRAFTED = "drafted"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
    REJECTED = "rejected"
    SNOOZED = "snoozed"
    EXPIRED = "expired"
    APPLIED_MANUALLY = "applied_manually"


class ApplyMethod(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    LINK = "link"
    FORM = "form"
    LINKEDIN = "linkedin"
    WALKIN = "walkin"
    UNKNOWN = "unknown"


class WorkMode(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class PostType(str, Enum):
    JOB = "job"
    INTERNSHIP = "internship"
    TRAINEE = "trainee"
    FREELANCE = "freelance"
    VOLUNTEER = "volunteer"
    WALKIN = "walkin"
    SCHOLARSHIP = "scholarship"
    FELLOWSHIP = "fellowship"
    HACKATHON = "hackathon"
    COURSE = "course"
    OTHER = "other"


class WalkinDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: Optional[str] = None
    time: Optional[str] = None
    address: Optional[str] = None


class IncomingMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_id: str
    chat_id: str
    chat_name: str = ""
    sender: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)
    raw_text: str = ""
    media_path: Optional[str] = None
    media_mime: Optional[str] = None
    is_group: bool = True
    is_channel: bool = False
    is_self_forward: bool = False
    message_hash: str = ""


class InboxItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    message_id: str
    chat_id: str
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = "received"
    noise_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    processed_at: Optional[datetime] = None


class ExtractedRole(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    company: str
    field: str
    location_text: str = ""
    work_mode: WorkMode = WorkMode.UNKNOWN
    city: str = ""
    experience_min_years: Optional[float] = 0.0
    experience_max_years: Optional[float] = None
    education: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    deadline: Optional[str] = None  # ISO format string or None
    shift_text: Optional[str] = None
    night_shift: bool = False
    gender_requirement: str = "any"  # 'male' | 'female' | 'any'
    apply_method: ApplyMethod = ApplyMethod.UNKNOWN
    apply_email: Optional[str] = None
    apply_whatsapp: Optional[str] = None
    apply_link: Optional[str] = None
    exact_subject: Optional[str] = None
    from_image: bool = False
    walkin: Optional[WalkinDetails] = None
    fresh_grad_ok: bool = True
    notes: Optional[str] = None


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_job: bool
    post_type: PostType = PostType.JOB
    roles: List[ExtractedRole] = Field(default_factory=list)
    confidence: float = 1.0


class JobCard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    role: ExtractedRole
    tier: Tier = Tier.STRONG
    tier_reasons: List[str] = Field(default_factory=list)
    score: float = 0.0
    status: Status = Status.NEW
    fit_summary: str = ""
    matches: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    source_messages: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class TailorPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    relevant_project_ids: List[str] = Field(default_factory=list)
    project_ordering: List[str] = Field(default_factory=list)
    skill_emphasis: List[str] = Field(default_factory=list)
    summary_2_3_lines: str = ""
    honest_notes: List[str] = Field(default_factory=list)


class CVArtifact(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    job_id: str
    pdf_path: str
    preview_png_paths: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utc_now)
    passes_verifier: bool = True
    verifier_notes: Optional[str] = None


class EmailDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    job_id: str
    recipient: str
    subject: str
    body: str
    generated_at: datetime = Field(default_factory=_utc_now)
    is_customized: bool = False


class SendResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


class ProfilePersonal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    gender: Optional[str] = None
    accepts_night_shift: Optional[bool] = False
    languages: List[str] = Field(default_factory=list)


class ProfileStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    degree: str = ""
    university: str = ""
    semester: int = 7
    expected_graduation: Optional[str] = None
    available_as: List[str] = Field(default_factory=list)


class ProfileMatchingExperience(BaseModel):
    model_config = ConfigDict(extra="ignore")
    comfortable_max_years: float = 2.0
    stretch_max_years: float = 3.0
    skip_above_years: float = 3.0


class ProfileMatching(BaseModel):
    model_config = ConfigDict(extra="ignore")
    hard_locations: List[str] = Field(default_factory=list)
    remote_must_accept_pakistan: bool = True
    target_fields: List[str] = Field(default_factory=list)
    avoid_fields: List[str] = Field(default_factory=list)
    experience: ProfileMatchingExperience = Field(default_factory=ProfileMatchingExperience)
    notes: Optional[str] = None


class ProfileProject(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    years: str = ""
    context: str = ""
    tech: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)


class ProfileEducation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    degree: str
    school: str
    years: str
    note: Optional[str] = None


class ProfileSkills(BaseModel):
    model_config = ConfigDict(extra="ignore")
    languages: List[str] = Field(default_factory=list)
    ai_ml: List[str] = Field(default_factory=list)
    web_backend: List[str] = Field(default_factory=list)
    mobile_tools: List[str] = Field(default_factory=list)
    concepts: List[str] = Field(default_factory=list)


class Profile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    email: str
    phone: str
    location: str
    links: Dict[str, str] = Field(default_factory=dict)
    personal: ProfilePersonal = Field(default_factory=ProfilePersonal)
    status: ProfileStatus = Field(default_factory=ProfileStatus)
    matching: ProfileMatching = Field(default_factory=ProfileMatching)
    skills: ProfileSkills = Field(default_factory=ProfileSkills)
    education: List[ProfileEducation] = Field(default_factory=list)
    projects: List[ProfileProject] = Field(default_factory=list)
    courses: List[Dict[str, Any]] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    achievements: List[Dict[str, Any]] = Field(default_factory=list)


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    send_enabled: bool = False
    daily_send_cap: int = 25
    min_gap_seconds: int = 60
    gemini_model_fast: str = "gemini-2.5-flash"
    gemini_model_smart: str = "gemini-2.5-flash"
    groq_fallback_enabled: bool = True
    groq_model: str = "llama-3.3-70b-versatile"
    watched_chats: List[str] = Field(default_factory=list)
    now_override: Optional[str] = None
