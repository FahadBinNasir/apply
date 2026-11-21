"""
Protocol interfaces for WhatsApp Job Agent.
Contracts are frozen in Phase 0. No agent except LEAD may modify this file.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from contracts.models import (
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    ExtractionResult,
    InboxItem,
    IncomingMessage,
    JobCard,
    Profile,
    SendResult,
    TailorPlan,
    Tier,
)


@runtime_checkable
class IntakeSource(Protocol):
    """Listens or fetches incoming WhatsApp messages in a read-only manner."""

    async def poll_or_receive(self) -> List[IncomingMessage]:
        ...

    def get_status(self) -> Dict[str, Any]:
        """Returns connection state, battery, and phone info."""
        ...

    def get_qr(self) -> Optional[str]:
        """Returns QR data or base64 if unauthenticated."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Standardized LLM client interface with structured output support."""

    async def generate_json(
        self,
        schema: Dict[str, Any],
        prompt: str,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        ...

    def get_quota_status(self) -> Dict[str, Any]:
        ...


@runtime_checkable
class PreFilter(Protocol):
    """Fast regex/keyword pre-filter before invoking any LLM."""

    def evaluate(self, message: IncomingMessage) -> Tuple[bool, Optional[str]]:
        """Returns (is_noise, noise_reason)."""
        ...


@runtime_checkable
class Extractor(Protocol):
    """Extracts structured roles from raw post text or poster image."""

    async def extract(
        self,
        message: IncomingMessage,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> ExtractionResult:
        ...


@runtime_checkable
class LinkFetcher(Protocol):
    """Safely fetches and extracts text from external URLs with SSRF protection."""

    async def fetch_link(self, url: str) -> Tuple[bool, str, Optional[str]]:
        """Returns (success, cleaned_content, error_message)."""
        ...


@runtime_checkable
class RulesEngine(Protocol):
    """Deterministic, pure-code decision engine matching roles against profile."""

    def evaluate(
        self,
        role: ExtractedRole,
        profile: Profile,
        now_override: Optional[datetime] = None,
    ) -> Tuple[Tier, List[str], float, List[str], List[str]]:
        """Returns (tier, reasons, score_modifier, matches, gaps)."""
        ...


@runtime_checkable
class Scorer(Protocol):
    """Combines rule evaluation and semantic matching into final score and tier."""

    def score(
        self,
        role: ExtractedRole,
        rules_tier: Tier,
        rules_reasons: List[str],
        base_score: float,
        profile: Profile,
    ) -> Tuple[Tier, float, str]:
        """Returns (final_tier, final_score, fit_summary)."""
        ...


@runtime_checkable
class Deduper(Protocol):
    """Deduplicates incoming jobs across multiple channels and groups."""

    def find_duplicate(
        self,
        role: ExtractedRole,
        existing_jobs: List[JobCard],
    ) -> Optional[str]:
        """Returns matching existing job_id if duplicate, else None."""
        ...


@runtime_checkable
class CVBuilder(Protocol):
    """Generates tailored, verified ATS-friendly CV PDFs from profile seed facts."""

    async def plan_tailoring(
        self,
        role: ExtractedRole,
        profile: Profile,
    ) -> TailorPlan:
        ...

    async def build_cv(
        self,
        role: ExtractedRole,
        profile: Profile,
        plan: TailorPlan,
    ) -> CVArtifact:
        ...

    def verify_no_fabrication(
        self,
        cv_text: str,
        profile: Profile,
    ) -> Tuple[bool, List[str]]:
        """Validates that no invented facts exist in the tailored CV."""
        ...


@runtime_checkable
class Mailer(Protocol):
    """Generates drafts and safely sends emails via Gmail API."""

    def create_draft(
        self,
        role: ExtractedRole,
        profile: Profile,
        exact_subject: Optional[str] = None,
    ) -> EmailDraft:
        ...

    async def send_application(
        self,
        job: JobCard,
        draft: EmailDraft,
        cv: CVArtifact,
    ) -> SendResult:
        ...


@runtime_checkable
class CalendarExporter(Protocol):
    """Generates .ics calendar events for walk-in interviews."""

    def export_walkin_ics(self, job: JobCard) -> Optional[str]:
        ...


@runtime_checkable
class JobRepo(Protocol):
    """Async repository for JobCard persistence and querying."""

    async def save(self, job: JobCard) -> JobCard:
        ...

    async def get_by_id(self, job_id: str) -> Optional[JobCard]:
        ...

    async def list_cards(
        self,
        tier: Optional[Tier] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[JobCard]:
        ...

    async def search(self, query: str) -> List[JobCard]:
        ...

    async def update_status(self, job_id: str, status: str) -> bool:
        ...


@runtime_checkable
class InboxRepo(Protocol):
    """Async repository for raw intake messages and noise audit log."""

    async def save_raw_message(self, message: IncomingMessage) -> InboxItem:
        ...

    async def log_noise(self, message: IncomingMessage, reason: str) -> None:
        ...

    async def is_duplicate_message(self, message_hash: str) -> bool:
        ...


@runtime_checkable
class Queue(Protocol):
    """Persistent FIFO queue with priority, retry, and crash-resumption."""

    async def enqueue(self, payload: Dict[str, Any], priority: int = 0) -> str:
        ...

    async def dequeue(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        ...

    async def ack(self, item_id: str) -> None:
        ...

    async def nack(self, item_id: str, error: str, retry_after_sec: int = 60) -> None:
        ...
