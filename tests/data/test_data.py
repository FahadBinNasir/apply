import asyncio
import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy.orm import sessionmaker

from app.db.crypto import TokenEncryption
from app.db.models import Base
from app.db.repos import SQLAlchemyInboxRepo, SQLAlchemyJobRepo, SQLAlchemyQueue
from app.db.session import create_db_engine, init_db
from contracts.models import (
    ApplyMethod,
    ExtractedRole,
    IncomingMessage,
    JobCard,
    Status,
    Tier,
    WorkMode,
)
from contracts.protocols import InboxRepo, JobRepo, Queue


def test_token_encryption():
    crypto = TokenEncryption()
    plain = "ya29.a0AfH6SMD_sample_oauth_refresh_token_12345"
    encrypted = crypto.encrypt(plain)
    assert encrypted != plain
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == plain


def test_db_init_and_wal():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_apply.sqlite"
        db_url = f"sqlite:///{db_path.as_posix()}"
        engine = init_db(create_db_engine(db_url))

        try:
            with engine.connect() as conn:
                # Verify WAL pragma
                res = conn.exec_driver_sql("PRAGMA journal_mode;").scalar()
                assert res.upper() == "WAL"

                # Verify tables exist
                tables = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table';").scalars().all()
                assert "jobs" in tables
                assert "inbox" in tables
                assert "queue" in tables
                assert "jobs_fts" in tables
        finally:
            engine.dispose()


def test_sqlalchemy_repos_and_queue():
    async def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_repos.sqlite"
            db_url = f"sqlite:///{db_path.as_posix()}"
            engine = init_db(create_db_engine(db_url))
            try:
                session_factory = sessionmaker(bind=engine)

                job_repo: JobRepo = SQLAlchemyJobRepo(session_factory)
                inbox_repo: InboxRepo = SQLAlchemyInboxRepo(session_factory)
                queue: Queue = SQLAlchemyQueue(session_factory)

                # 1. Test InboxRepo
                msg = IncomingMessage(
                    source_id="msg_001",
                    chat_id="chat_001",
                    chat_name="Group 1",
                    raw_text="Hiring DevOps",
                    message_hash="hash_001",
                )
                inbox_item = await inbox_repo.save_raw_message(msg)
                assert inbox_item.message_id == "msg_001"
                assert await inbox_repo.is_duplicate_message("hash_001")
                assert not await inbox_repo.is_duplicate_message("hash_unknown")

                await inbox_repo.log_noise(msg, "noise_test")

                # 2. Test JobRepo
                role = ExtractedRole(
                    title="DevOps Engineer",
                    company="Paysys Labs",
                    field="DevOps / cloud",
                    location_text="Karachi (On-site)",
                    work_mode=WorkMode.ONSITE,
                    city="Karachi",
                    apply_method=ApplyMethod.EMAIL,
                    apply_email="hiring@paysyslabs.com",
                    exact_subject="DevOps Engineer – Application",
                )
                card = JobCard(
                    id="job_001",
                    role=role,
                    tier=Tier.STRONG,
                    score=90.0,
                    status=Status.NEW,
                    fit_summary="Fit",
                )
                await job_repo.save(card)

                retrieved = await job_repo.get_by_id("job_001")
                assert retrieved is not None
                assert retrieved.role.title == "DevOps Engineer"
                assert retrieved.tier == Tier.STRONG

                # List cards
                strong_cards = await job_repo.list_cards(tier=Tier.STRONG)
                assert len(strong_cards) == 1
                stretch_cards = await job_repo.list_cards(tier=Tier.STRETCH)
                assert len(stretch_cards) == 0

                # Search cards
                search_results = await job_repo.search("paysys")
                assert len(search_results) == 1
                assert search_results[0].id == "job_001"

                # Update status
                ok = await job_repo.update_status("job_001", Status.APPROVED.value)
                assert ok
                updated = await job_repo.get_by_id("job_001")
                assert updated.status == Status.APPROVED

                # 3. Test Queue (Priority & Retry)
                q_id1 = await queue.enqueue({"task": "low_prio"}, priority=0)
                q_id2 = await queue.enqueue({"task": "high_prio"}, priority=10)

                # High priority should dequeue first
                first_deq = await queue.dequeue()
                assert first_deq is not None
                item_id, payload = first_deq
                assert item_id == q_id2
                assert payload["task"] == "high_prio"
                await queue.ack(item_id)

                # Low priority dequeues second
                second_deq = await queue.dequeue()
                assert second_deq is not None
                item_id, payload = second_deq
                assert item_id == q_id1
                assert payload["task"] == "low_prio"
                # Nack with retry_after_sec=0 to allow immediate re-run
                await queue.nack(item_id, "simulated_error", retry_after_sec=0)

                # Low priority should be retried
                retry_deq = await queue.dequeue()
                assert retry_deq is not None
                assert retry_deq[0] == q_id1
                await queue.ack(q_id1)

                # Queue empty
                empty_deq = await queue.dequeue()
                assert empty_deq is None

                # 4. Queue survives restart
                await queue.enqueue({"task": "persisted_job"}, priority=5)

                # Re-create queue pointing to same db
                restarted_queue = SQLAlchemyQueue(sessionmaker(bind=engine))
                deq_after_restart = await restarted_queue.dequeue()
                assert deq_after_restart is not None
                assert deq_after_restart[1]["task"] == "persisted_job"
                await restarted_queue.ack(deq_after_restart[0])
            finally:
                engine.dispose()

    asyncio.run(_run())
