"""
Contract verification tests (Gate G0).
Verifies that all models, protocols, fakes, and mocks conform to the contracts.
"""

import json
from pathlib import Path
import pytest

from contracts.models import (
    ApplyMethod,
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    ExtractionResult,
    InboxItem,
    IncomingMessage,
    JobCard,
    PostType,
    Profile,
    SendResult,
    Settings,
    Status,
    TailorPlan,
    Tier,
    WorkMode,
)
from contracts.protocols import (
    CalendarExporter,
    CVBuilder,
    Deduper,
    Extractor,
    InboxRepo,
    IntakeSource,
    JobRepo,
    LinkFetcher,
    LLMProvider,
    Mailer,
    PreFilter,
    Queue,
    RulesEngine,
    Scorer,
)
from contracts.fakes import (
    FakeCalendarExporter,
    FakeCVBuilder,
    FakeDeduper,
    FakeExtractor,
    FakeInboxRepo,
    FakeIntakeSource,
    FakeJobRepo,
    FakeLinkFetcher,
    FakeLLMProvider,
    FakeMailer,
    FakePreFilter,
    FakeQueue,
    FakeRulesEngine,
    FakeScorer,
)


def test_contract_version():
    version_file = Path("contracts/VERSION")
    assert version_file.exists(), "contracts/VERSION must exist"
    assert version_file.read_text().strip() == "1", "contracts/VERSION must be '1'"


def test_fakes_satisfy_protocols():
    assert isinstance(FakeIntakeSource(), IntakeSource)
    assert isinstance(FakeLLMProvider(), LLMProvider)
    assert isinstance(FakePreFilter(), PreFilter)
    assert isinstance(FakeExtractor(), Extractor)
    assert isinstance(FakeLinkFetcher(), LinkFetcher)
    assert isinstance(FakeRulesEngine(), RulesEngine)
    assert isinstance(FakeScorer(), Scorer)
    assert isinstance(FakeDeduper(), Deduper)
    assert isinstance(FakeCVBuilder(), CVBuilder)
    assert isinstance(FakeMailer(), Mailer)
    assert isinstance(FakeCalendarExporter(), CalendarExporter)
    assert isinstance(FakeJobRepo(), JobRepo)
    assert isinstance(FakeInboxRepo(), InboxRepo)
    assert isinstance(FakeQueue(), Queue)


def test_models_instantiation():
    msg = IncomingMessage(
        source_id="msg_001",
        chat_id="chat_123",
        chat_name="Test Group",
        raw_text="We are hiring a DevOps Engineer",
    )
    assert msg.source_id == "msg_001"

    role = ExtractedRole(
        title="DevOps Engineer",
        company="Paysys Labs",
        field="DevOps / cloud",
        location_text="Karachi",
        work_mode=WorkMode.ONSITE,
        city="Karachi",
        apply_method=ApplyMethod.EMAIL,
        apply_email="hiring@paysyslabs.com",
        exact_subject="DevOps Engineer – Application",
    )
    assert role.title == "DevOps Engineer"

    card = JobCard(
        id="job_001",
        role=role,
        tier=Tier.STRONG,
        status=Status.NEW,
    )
    assert card.tier == Tier.STRONG
    assert card.status == Status.NEW

    plan = TailorPlan(
        relevant_project_ids=["knowledge-brain"],
        project_ordering=["knowledge-brain"],
        skill_emphasis=["CI/CD", "Linux"],
        summary_2_3_lines="7th semester student.",
    )
    assert len(plan.relevant_project_ids) == 1

    draft = EmailDraft(
        id="draft_001",
        job_id="job_001",
        recipient="hiring@paysyslabs.com",
        subject="DevOps Engineer – Application",
        body="Dear Hiring Team...",
    )
    assert draft.recipient == "hiring@paysyslabs.com"


def test_fixtures_expected_json_exists_and_valid():
    fixtures_path = Path("contracts/fixtures.expected.json")
    assert fixtures_path.exists(), "contracts/fixtures.expected.json must exist"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "fixtures" in data
    assert "F1" in data["fixtures"]
    assert data["fixtures"]["F1"]["expected_tier"] == "STRONG"
    assert "F2" in data["fixtures"]
    assert data["fixtures"]["F2"]["expected_tier"] == "STRONG"
    assert "F3" in data["fixtures"]
    assert data["fixtures"]["F3"]["expected_tier"] == "STRETCH"
    assert "F4" in data["fixtures"]
    assert data["fixtures"]["F4"]["expected_tier"] == "SKIPPED"


def test_mock_json_files():
    mock_dir = Path("contracts/mocks")
    assert mock_dir.exists() and mock_dir.is_dir()
    required_mocks = [
      "inbox_normal.json",
      "inbox_empty.json",
      "job_detail_f1.json",
      "job_detail_f2.json",
      "job_detail_f3.json",
      "sent_log.json",
      "skipped_list.json",
      "opportunities.json",
      "whatsapp_status.json",
      "whatsapp_disconnected.json",
      "settings.json",
      "health_normal.json",
      "health_quota_exhausted.json",
      "health_gmail_expired.json",
    ]
    for mock_file in required_mocks:
        fp = mock_dir / mock_file
        assert fp.exists(), f"Mock file {mock_file} is missing"
        with open(fp, "r", encoding="utf-8") as f:
            content = json.load(f)
            assert isinstance(content, dict), f"Mock {mock_file} must be a JSON object"


import asyncio

def test_fake_workflow_end_to_end():
    async def _run():
        intake = FakeIntakeSource()
        prefilter = FakePreFilter()
        extractor = FakeExtractor()
        rules = FakeRulesEngine()
        scorer = FakeScorer()
        cv_builder = FakeCVBuilder()
        mailer = FakeMailer()
        job_repo = FakeJobRepo()

        raw_msg = IncomingMessage(
            source_id="msg_paysys_01",
            chat_id="group_alumni",
            chat_name="Bahria Alumni",
            raw_text="We're Hiring – DevOps Engineer at Paysys Labs. Location: Karachi. Send CV to hiring@paysyslabs.com with exact subject 'DevOps Engineer – Application'",
        )

        is_noise, _ = prefilter.evaluate(raw_msg)
        assert not is_noise

        extracted = await extractor.extract(raw_msg)
        assert extracted.is_job
        role = extracted.roles[0]

        from contracts.models import Profile, ProfileMatching, ProfileStatus, ProfileMatchingExperience
        profile = Profile(
            name="Fahad Bin Nasir",
            email="fahadabbasi17025@gmail.com",
            phone="+92 327 8262810",
            location="Karachi, Pakistan",
            status=ProfileStatus(degree="Bachelor of Software Engineering", university="Bahria University", semester=7),
            matching=ProfileMatching(
                hard_locations=["Karachi onsite", "Karachi hybrid", "Remote"],
                target_fields=["DevOps / cloud", "software engineering"],
                avoid_fields=["sales", "HR"],
                experience=ProfileMatchingExperience(comfortable_max_years=2.0, stretch_max_years=3.0, skip_above_years=3.0),
            ),
        )

        tier, reasons, score_mod, matches, gaps = rules.evaluate(role, profile)
        final_tier, score, summary = scorer.score(role, tier, reasons, score_mod, profile)
        assert final_tier == Tier.STRONG
        assert score >= 70.0

        plan = await cv_builder.plan_tailoring(role, profile)
        cv = await cv_builder.build_cv(role, profile, plan)
        assert cv.passes_verifier

        draft = mailer.create_draft(role, profile, role.exact_subject)
        assert draft.subject == "DevOps Engineer – Application"

        card = JobCard(
            id="job_f1",
            role=role,
            tier=final_tier,
            score=score,
            fit_summary=summary,
            matches=matches,
            gaps=gaps,
        )
        await job_repo.save(card)
        saved = await job_repo.get_by_id("job_f1")
        assert saved is not None
        assert saved.role.company == "Paysys Labs"

    asyncio.run(_run())
