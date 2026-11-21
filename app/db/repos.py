from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, desc, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    CVArtifactModel,
    DraftModel,
    InboxModel,
    JobModel,
    JobSourceModel,
    NoiseLogModel,
    QueueModel,
    SendModel,
)
from contracts.models import (
    ApplyMethod,
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    InboxItem,
    IncomingMessage,
    JobCard,
    Status,
    Tier,
    WalkinDetails,
    WorkMode,
)
from contracts.protocols import InboxRepo, JobRepo, Queue


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _model_to_jobcard(m: JobModel) -> JobCard:
    walkin = None
    if m.walkin_details:
        walkin = WalkinDetails(**m.walkin_details)

    role = ExtractedRole(
        title=m.title,
        company=m.company,
        field=m.field,
        location_text=m.location_text,
        work_mode=WorkMode(m.work_mode) if m.work_mode in WorkMode.__members__.values() else WorkMode.UNKNOWN,
        city=m.city,
        experience_min_years=m.experience_min_years,
        experience_max_years=m.experience_max_years,
        education=m.education,
        skills=m.skills or [],
        responsibilities=m.responsibilities or [],
        deadline=m.deadline,
        shift_text=m.shift_text,
        night_shift=m.night_shift,
        gender_requirement=m.gender_requirement,
        apply_method=ApplyMethod(m.apply_method) if m.apply_method in ApplyMethod.__members__.values() else ApplyMethod.UNKNOWN,
        apply_email=m.apply_email,
        apply_whatsapp=m.apply_whatsapp,
        apply_link=m.apply_link,
        exact_subject=m.exact_subject,
        from_image=m.from_image,
        walkin=walkin,
        fresh_grad_ok=m.fresh_grad_ok,
        notes=m.notes,
    )
    return JobCard(
        id=m.id,
        role=role,
        tier=Tier(m.tier) if m.tier in Tier.__members__.values() else Tier.STRONG,
        tier_reasons=m.tier_reasons or [],
        score=m.score,
        status=Status(m.status) if m.status in Status.__members__.values() else Status.NEW,
        fit_summary=m.fit_summary,
        matches=m.matches or [],
        gaps=m.gaps or [],
        source_messages=m.source_messages or [],
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyJobRepo:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    async def save(self, job: JobCard) -> JobCard:
        with self.session_factory() as session:
            existing = session.get(JobModel, job.id)
            walkin_dict = job.role.walkin.model_dump() if job.role.walkin else None

            if existing:
                existing.title = job.role.title
                existing.company = job.role.company
                existing.field = job.role.field
                existing.location_text = job.role.location_text
                existing.work_mode = job.role.work_mode.value
                existing.city = job.role.city
                existing.experience_min_years = job.role.experience_min_years
                existing.experience_max_years = job.role.experience_max_years
                existing.education = job.role.education
                existing.skills = job.role.skills
                existing.responsibilities = job.role.responsibilities
                existing.deadline = job.role.deadline
                existing.shift_text = job.role.shift_text
                existing.night_shift = job.role.night_shift
                existing.gender_requirement = job.role.gender_requirement
                existing.apply_method = job.role.apply_method.value
                existing.apply_email = job.role.apply_email
                existing.apply_whatsapp = job.role.apply_whatsapp
                existing.apply_link = job.role.apply_link
                existing.exact_subject = job.role.exact_subject
                existing.from_image = job.role.from_image
                existing.walkin_details = walkin_dict
                existing.fresh_grad_ok = job.role.fresh_grad_ok
                existing.notes = job.role.notes

                existing.tier = job.tier.value
                existing.tier_reasons = job.tier_reasons
                existing.score = job.score
                existing.status = job.status.value
                existing.fit_summary = job.fit_summary
                existing.matches = job.matches
                existing.gaps = job.gaps
                existing.source_messages = job.source_messages
                existing.updated_at = _utc_now()
            else:
                new_model = JobModel(
                    id=job.id,
                    title=job.role.title,
                    company=job.role.company,
                    field=job.role.field,
                    location_text=job.role.location_text,
                    work_mode=job.role.work_mode.value,
                    city=job.role.city,
                    experience_min_years=job.role.experience_min_years,
                    experience_max_years=job.role.experience_max_years,
                    education=job.role.education,
                    skills=job.role.skills,
                    responsibilities=job.role.responsibilities,
                    deadline=job.role.deadline,
                    shift_text=job.role.shift_text,
                    night_shift=job.role.night_shift,
                    gender_requirement=job.role.gender_requirement,
                    apply_method=job.role.apply_method.value,
                    apply_email=job.role.apply_email,
                    apply_whatsapp=job.role.apply_whatsapp,
                    apply_link=job.role.apply_link,
                    exact_subject=job.role.exact_subject,
                    from_image=job.role.from_image,
                    walkin_details=walkin_dict,
                    fresh_grad_ok=job.role.fresh_grad_ok,
                    notes=job.role.notes,
                    tier=job.tier.value,
                    tier_reasons=job.tier_reasons,
                    score=job.score,
                    status=job.status.value,
                    fit_summary=job.fit_summary,
                    matches=job.matches,
                    gaps=job.gaps,
                    source_messages=job.source_messages,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
                session.add(new_model)

            session.commit()
            return job

    async def get_by_id(self, job_id: str) -> Optional[JobCard]:
        with self.session_factory() as session:
            m = session.get(JobModel, job_id)
            if not m:
                return None
            return _model_to_jobcard(m)

    async def list_cards(
        self,
        tier: Optional[Tier] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[JobCard]:
        with self.session_factory() as session:
            stmt = select(JobModel)
            if tier is not None:
                stmt = stmt.where(JobModel.tier == tier.value)
            if status is not None:
                stmt = stmt.where(JobModel.status == status)
            stmt = stmt.order_by(desc(JobModel.created_at)).offset(offset).limit(limit)
            models = session.scalars(stmt).all()
            return [_model_to_jobcard(m) for m in models]

    async def search(self, query: str) -> List[JobCard]:
        q = query.lower()
        with self.session_factory() as session:
            stmt = select(JobModel).where(
                (JobModel.title.ilike(f"%{q}%"))
                | (JobModel.company.ilike(f"%{q}%"))
                | (JobModel.field.ilike(f"%{q}%"))
            )
            models = session.scalars(stmt).all()
            return [_model_to_jobcard(m) for m in models]

    async def update_status(self, job_id: str, status: str) -> bool:
        with self.session_factory() as session:
            m = session.get(JobModel, job_id)
            if not m:
                return False
            m.status = status
            m.updated_at = _utc_now()
            session.commit()
            return True


class SQLAlchemyInboxRepo:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    async def save_raw_message(self, message: IncomingMessage) -> InboxItem:
        with self.session_factory() as session:
            item_id = f"inbox_{uuid.uuid4().hex[:12]}"
            model = InboxModel(
                id=item_id,
                source_id=message.source_id,
                chat_id=message.chat_id,
                chat_name=message.chat_name,
                sender=message.sender,
                timestamp=message.timestamp,
                raw_text=message.raw_text,
                media_path=message.media_path,
                media_mime=message.media_mime,
                message_hash=message.message_hash,
                status="received",
                created_at=_utc_now(),
            )
            session.add(model)
            session.commit()
            return InboxItem(
                id=model.id,
                message_id=model.source_id,
                chat_id=model.chat_id,
                raw_payload=message.model_dump(),
                status="received",
                created_at=model.created_at,
            )

    async def log_noise(self, message: IncomingMessage, reason: str) -> None:
        with self.session_factory() as session:
            model = NoiseLogModel(
                id=f"noise_{uuid.uuid4().hex[:12]}",
                message_id=message.source_id,
                chat_id=message.chat_id,
                preview=message.raw_text[:200],
                reason=reason,
                created_at=_utc_now(),
            )
            session.add(model)
            session.commit()

    async def is_duplicate_message(self, message_hash: str) -> bool:
        if not message_hash:
            return False
        with self.session_factory() as session:
            stmt = select(InboxModel.id).where(InboxModel.message_hash == message_hash)
            return session.scalar(stmt) is not None


class SQLAlchemyQueue:
    def __init__(self, session_factory: sessionmaker, queue_name: str = "default"):
        self.session_factory = session_factory
        self.queue_name = queue_name

    async def enqueue(self, payload: Dict[str, Any], priority: int = 0) -> str:
        with self.session_factory() as session:
            item_id = f"q_{uuid.uuid4().hex[:12]}"
            model = QueueModel(
                id=item_id,
                queue_name=self.queue_name,
                priority=priority,
                payload=payload,
                status="pending",
                retries=0,
                next_run_at=_utc_now(),
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            session.add(model)
            session.commit()
            return item_id

    async def dequeue(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        with self.session_factory() as session:
            now = _utc_now()
            stmt = (
                select(QueueModel)
                .where(
                    QueueModel.queue_name == self.queue_name,
                    QueueModel.status == "pending",
                    QueueModel.next_run_at <= now,
                )
                .order_by(desc(QueueModel.priority), QueueModel.created_at.asc())
                .limit(1)
            )
            item = session.scalar(stmt)
            if not item:
                return None

            item.status = "processing"
            item.updated_at = now
            session.commit()
            return item.id, item.payload

    async def ack(self, item_id: str) -> None:
        with self.session_factory() as session:
            item = session.get(QueueModel, item_id)
            if item:
                item.status = "done"
                item.updated_at = _utc_now()
                session.commit()

    async def nack(self, item_id: str, error: str, retry_after_sec: int = 60) -> None:
        with self.session_factory() as session:
            item = session.get(QueueModel, item_id)
            if item:
                from datetime import timedelta
                item.retries += 1
                item.last_error = error
                if item.retries > 3:
                    item.status = "failed"
                else:
                    item.status = "pending"
                    item.next_run_at = _utc_now() + timedelta(seconds=retry_after_sec)
                item.updated_at = _utc_now()
                session.commit()
