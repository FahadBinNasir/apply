from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional
from contracts.models import InboxItem, IncomingMessage, JobCard, Tier
from contracts.protocols import InboxRepo, JobRepo


class FakeJobRepo:
    def __init__(self):
        self.jobs: Dict[str, JobCard] = {}

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
