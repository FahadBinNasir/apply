from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.models import CVArtifact, EmailDraft, InboxItem, IncomingMessage, JobCard, Tier
from contracts.protocols import InboxRepo, JobRepo


class FakeJobRepo:
    def __init__(self):
        self.jobs: Dict[str, JobCard] = {}
        self._drafts: Dict[str, EmailDraft] = {}
        self._cvs: Dict[str, CVArtifact] = {}
        self._sends: List[Dict[str, Any]] = []

    async def save(self, job: JobCard) -> JobCard:
        job.updated_at = datetime.now(timezone.utc)
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, job_id: str) -> Optional[JobCard]:
        return self.jobs.get(job_id)

    async def list_cards(
        self,
        tier: Optional[Tier] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[JobCard]:
        results = list(self.jobs.values())
        if tier is not None:
            results = [j for j in results if j.tier == tier]
        if status is not None:
            results = [j for j in results if j.status == status]
        return results[offset : offset + limit]

    async def search(self, query: str) -> List[JobCard]:
        q = query.lower()
        return [
            j
            for j in self.jobs.values()
            if q in j.role.title.lower()
            or q in j.role.company.lower()
            or q in j.role.field.lower()
        ]

    async def update_status(self, job_id: str, status: str) -> bool:
        if job_id in self.jobs:
            self.jobs[job_id].status = status  # type: ignore
            self.jobs[job_id].updated_at = datetime.now(timezone.utc)
            return True
        return False

    async def save_draft(self, draft: EmailDraft) -> EmailDraft:
        self._drafts[draft.job_id] = draft
        return draft

    async def get_draft(self, job_id: str) -> Optional[EmailDraft]:
        return self._drafts.get(job_id)

    async def save_cv(self, cv: CVArtifact) -> CVArtifact:
        self._cvs[cv.job_id] = cv
        return cv

    async def get_cv(self, job_id: str) -> Optional[CVArtifact]:
        return self._cvs.get(job_id)

    async def record_send(
        self,
        job_id: str,
        recipient: str,
        subject: str,
        status: str = "sent",
        gmail_message_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        company = "Unknown"
        title = "Position"
        if job_id in self.jobs:
            company = self.jobs[job_id].role.company
            title = self.jobs[job_id].role.title
        record = {
            "id": f"send_{len(self._sends) + 1}",
            "job_id": job_id,
            "company": company,
            "title": title,
            "recipient": recipient,
            "subject": subject,
            "gmail_message_id": gmail_message_id,
            "status": status,
            "error": error,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self._sends.append(record)
        return record

    async def get_sends(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self._sends))[:limit]

    async def check_recent_send(self, company: str, email: str, days: int = 14) -> bool:
        for s in self._sends:
            if s.get("status") in ["sent", "dry_run"]:
                if s.get("recipient", "").lower() == email.lower() or s.get("company", "").lower() == company.lower():
                    return True
        return False


class FakeInboxRepo:
    def __init__(self):
        self.inbox_items: Dict[str, InboxItem] = {}
        self.noise_items: List[Dict[str, str]] = []
        self.seen_hashes: set[str] = set()

    async def save_raw_message(self, message: IncomingMessage) -> InboxItem:
        item = InboxItem(
            id=f"inbox_{len(self.inbox_items) + 1}",
            message_id=message.source_id,
            chat_id=message.chat_id,
            raw_payload=message.model_dump(),
            status="received",
            created_at=datetime.now(timezone.utc),
        )
        self.inbox_items[item.id] = item
        if message.message_hash:
            self.seen_hashes.add(message.message_hash)
        return item

    async def log_noise(self, message: IncomingMessage, reason: str) -> None:
        self.noise_items.append(
            {
                "message_id": message.source_id,
                "text": message.raw_text[:200],
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def is_duplicate_message(self, message_hash: str) -> bool:
        return message_hash in self.seen_hashes
