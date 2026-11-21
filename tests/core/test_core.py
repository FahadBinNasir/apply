import asyncio
import os
import pytest
from starlette.testclient import TestClient

from app.auth.security import (
    LockoutManager,
    create_session_token,
    generate_csrf_token,
    hash_password,
    verify_csrf_token,
    verify_password,
    verify_session_token,
)
from app.main import app, load_profile
from app.viewmodels.builders import (
    build_inbox_viewmodel,
    build_job_detail_viewmodel,
    build_sent_log_viewmodel,
    build_skipped_viewmodel,
)
from contracts.fakes import (
    FakeCVBuilder,
    FakeDeduper,
    FakeExtractor,
    FakeInboxRepo,
    FakeJobRepo,
    FakeLinkFetcher,
    FakeMailer,
    FakePreFilter,
    FakeRulesEngine,
    FakeScorer,
)
from contracts.models import (
    ApplyMethod,
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    IncomingMessage,
    JobCard,
    Status,
    Tier,
)
from app.worker.pipeline import PipelineEngine


def test_auth_and_lockout():
    plain = "SuperSecretPassword123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPassword", hashed)

    secret = "test_session_secret"
    token = create_session_token(secret, user_id="fahad")
    assert verify_session_token(token, secret)
    assert not verify_session_token("invalid:token", secret)

    csrf = generate_csrf_token(token, secret)
    assert verify_csrf_token(csrf, token, secret)
    assert not verify_csrf_token("bad_csrf", token, secret)

    # Test lockout manager
    lm = LockoutManager(max_attempts=3, lockout_seconds=10)
    client_ip = "192.168.1.50"
    assert not lm.is_locked_out(client_ip)[0]
    lm.record_failure(client_ip)
    lm.record_failure(client_ip)
    assert not lm.is_locked_out(client_ip)[0]
    lm.record_failure(client_ip)
    is_locked, cooldown = lm.is_locked_out(client_ip)
    assert is_locked
    assert cooldown > 0


def test_viewmodel_builders():
    role = ExtractedRole(
        title="DevOps Engineer",
        company="Paysys Labs",
        field="DevOps / cloud",
        apply_email="hiring@paysyslabs.com",
        exact_subject="DevOps Engineer – Application",
        deadline="2026-11-28",
    )
    job = JobCard(
        id="job_paysys",
        role=role,
        tier=Tier.STRONG,
        score=92.5,
        status=Status.DRAFTED,
        tier_reasons=["Target match"],
    )

    inbox_vm = build_inbox_viewmodel([job], active_tab=Tier.STRONG)
    assert inbox_vm["active_tab"] == "STRONG"
    assert inbox_vm["counts"]["strong"] == 1
    assert len(inbox_vm["jobs"]) == 1

    detail_vm = build_job_detail_viewmodel(job)
    assert detail_vm["job"]["company"] == "Paysys Labs"
    assert detail_vm["job"]["exact_subject"] == "DevOps Engineer – Application"

    sent_vm = build_sent_log_viewmodel([{"id": "1", "company": "Paysys Labs", "status": "sent"}])
    assert sent_vm["total_sent"] == 1

    skipped_job = JobCard(
        id="job_pentaloop",
        role=ExtractedRole(title="ASE iOS", company="Pentaloop", field="Mobile"),
        tier=Tier.SKIPPED,
        tier_reasons=["Lahore onsite"],
    )
    skipped_vm = build_skipped_viewmodel([skipped_job])
    assert skipped_vm["total_skipped"] == 1
    assert "location" in skipped_vm["by_reason"]


def test_pipeline_engine_processing():
    async def _test():
        profile = load_profile()
        job_repo = FakeJobRepo()
        inbox_repo = FakeInboxRepo()

        pipeline = PipelineEngine(
            prefilter=FakePreFilter(),
            extractor=FakeExtractor(),
            link_fetcher=FakeLinkFetcher(),
            rules_engine=FakeRulesEngine(),
            scorer=FakeScorer(),
            deduper=FakeDeduper(),
            cv_builder=FakeCVBuilder(),
            mailer=FakeMailer(),
            job_repo=job_repo,
            inbox_repo=inbox_repo,
            profile=profile,
        )

        msg = IncomingMessage(
            source_id="msg_f1",
            chat_id="alumni_group",
            chat_name="Bahria Alumni",
            raw_text="We're Hiring – DevOps Engineer at Paysys Labs. Karachi On-site.",
        )

        cards = await pipeline.process_message(msg)
        assert len(cards) == 1
        card = cards[0]
        assert card.tier == Tier.STRONG
        assert card.role.company == "Paysys Labs"

        saved_card = await job_repo.get_by_id(card.id)
        assert saved_card is not None

    asyncio.run(_test())


def test_fastapi_endpoints():
    os.environ["USE_FAKES"] = "true"
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

        # 2. Login redirect
        res = client.get("/")
        assert res.status_code == 303 or res.status_code == 200
