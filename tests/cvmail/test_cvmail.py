import asyncio
import os
import tempfile
from pathlib import Path
import yaml
import pytest

from app.calendar.exporter import ProductionCalendarExporter
from app.cv.builder import ProductionCVBuilder
from app.cv.verifier import AntiFabricationVerifier
from app.mail.drafting import generate_email_draft
from app.mail.sender import ProductionMailer
from app.mail.whatsapp_helper import generate_wa_apply_link
from contracts.models import (
    ApplyMethod,
    CVArtifact,
    ExtractedRole,
    JobCard,
    Profile,
    ProfileEducation,
    ProfileMatching,
    ProfileMatchingExperience,
    ProfilePersonal,
    ProfileProject,
    ProfileSkills,
    ProfileStatus,
    TailorPlan,
    Tier,
    WalkinDetails,
)


@pytest.fixture
def profile():
    profile_path = Path("profile.seed.yaml")
    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    projects = [
        ProfileProject(
            id=p["id"],
            name=p["name"],
            years=p.get("years", ""),
            context=p.get("context", ""),
            tech=p.get("tech", []),
            tags=p.get("tags", []),
            bullets=p.get("bullets", []),
        )
        for p in data.get("projects", [])
    ]

    return Profile(
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        location=data["location"],
        links=data.get("links", {}),
        personal=ProfilePersonal(languages=data["personal"].get("languages", [])),
        status=ProfileStatus(degree=data["status"]["degree"], university=data["status"]["university"], semester=7),
        matching=ProfileMatching(
            hard_locations=data["matching"]["hard_locations"],
            target_fields=data["matching"]["target_fields"],
            avoid_fields=data["matching"]["avoid_fields"],
            experience=ProfileMatchingExperience(comfortable_max_years=2.0, stretch_max_years=3.0, skip_above_years=3.0),
        ),
        skills=ProfileSkills(
            languages=data["skills"]["languages"],
            ai_ml=data["skills"]["ai_ml"],
            web_backend=data["skills"]["web_backend"],
            mobile_tools=data["skills"]["mobile_tools"],
            concepts=data["skills"]["concepts"],
        ),
        projects=projects,
    )


def test_anti_fabrication_verifier(profile):
    verifier = AntiFabricationVerifier()

    # 1. Legitimate plan should pass
    valid_plan = TailorPlan(
        relevant_project_ids=["knowledge-brain", "churnvision"],
        summary_2_3_lines="7th semester student at Bahria University applying for DevOps Engineer.",
    )
    is_valid, violations = verifier.verify_plan(valid_plan, profile)
    assert is_valid, f"Violations: {violations}"

    # 2. Invented project ID must fail
    fake_plan = TailorPlan(
        relevant_project_ids=["invented-crypto-trading-bot"],
        summary_2_3_lines="7th semester student at Bahria University.",
    )
    is_valid, violations = verifier.verify_plan(fake_plan, profile)
    assert not is_valid
    assert any("invented project" in v.lower() for v in violations)

    # 3. Fabricated WebForms claim must fail
    webforms_plan = TailorPlan(
        relevant_project_ids=["knowledge-brain"],
        summary_2_3_lines="7th semester student with extensive WebForms experience in enterprise systems.",
    )
    is_valid, violations = verifier.verify_plan(webforms_plan, profile)
    assert not is_valid
    assert any("webforms" in v.lower() for v in violations)

    # 4. Fabricated prior employer must fail in text check
    is_valid, violations = verifier.verify_cv_text("Previous role: Software Engineer at Google", profile)
    assert not is_valid
    assert any("google" in v.lower() for v in violations)


def test_cv_builder_renders_pdf(profile):
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = ProductionCVBuilder(output_dir=Path(tmpdir))
            role = ExtractedRole(
                title="DevOps Engineer",
                company="Paysys Labs",
                field="DevOps / cloud",
                location_text="Karachi (On-site)",
                apply_email="hiring@paysyslabs.com",
                exact_subject="DevOps Engineer – Application",
                fresh_grad_ok=True,
            )
            plan = await builder.plan_tailoring(role, profile)
            artifact = await builder.build_cv(role, profile, plan)

            assert artifact.passes_verifier
            pdf_path = Path(artifact.pdf_path)
            assert pdf_path.exists()
            assert pdf_path.stat().st_size > 1000

    asyncio.run(_test())


def test_email_drafting_and_mailer(profile):
    async def _test():
        # F1 Draft check: exact subject line with en dash
        role_f1 = ExtractedRole(
            title="DevOps Engineer",
            company="Paysys Labs",
            field="DevOps / cloud",
            apply_email="hiring@paysyslabs.com",
            exact_subject="DevOps Engineer – Application",
            skills=["CI/CD pipelines", "Linux administration"],
            fresh_grad_ok=True,
        )
        draft_f1 = generate_email_draft(role_f1, profile)
        assert draft_f1.subject == "DevOps Engineer – Application"
        assert draft_f1.recipient == "hiring@paysyslabs.com"
        assert "7th semester" in draft_f1.body
        assert "Bahria University" in draft_f1.body

        # Word count check (90 to 130 words target)
        word_count = len(draft_f1.body.split())
        assert 70 <= word_count <= 150

        # F2 Draft check: MTO - Dot Net Developer
        role_f2 = ExtractedRole(
            title="MTO - Dot Net Developer",
            company="Decibel HRMS",
            field=".NET / C# junior",
            apply_email="careers@decibel360.com",
            exact_subject="MTO - Dot Net Developer",
            skills=["C#", "SQL databases"],
            fresh_grad_ok=True,
        )
        draft_f2 = generate_email_draft(role_f2, profile)
        assert draft_f2.subject == "MTO - Dot Net Developer"

        # Mailer dry-run dispatch
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 dummy cv content")
            dummy_pdf = f.name

        try:
            mailer = ProductionMailer()
            job = JobCard(id="job_f1", role=role_f1, tier=Tier.STRONG)
            cv = CVArtifact(id="cv_1", job_id="job_f1", pdf_path=dummy_pdf)

            result = await mailer.send_application(job, draft_f1, cv)
            assert result.success
            assert "dry_run" in (result.message_id or "")

            # 1. Missing CV file fails
            missing_cv = CVArtifact(id="cv_missing", job_id="job_f1", pdf_path="nonexistent_cv.pdf")
            res_missing = await mailer.send_application(job, draft_f1, missing_cv)
            assert not res_missing.success
            assert "missing on disk" in res_missing.error.lower()

            # 2. Invalid recipient fails
            bad_draft = draft_f1.model_copy(update={"recipient": "not-an-email"})
            res_bad_email = await mailer.send_application(job, bad_draft, cv)
            assert not res_bad_email.success
            assert "invalid email format" in res_bad_email.error.lower()

            # 3. Header injection in subject fails
            injected_draft = draft_f1.model_copy(update={"subject": "Injected\r\nBcc: evil@attacker.com"})
            res_inj = await mailer.send_application(job, injected_draft, cv)
            assert not res_inj.success
            assert "newline" in res_inj.error.lower()

        finally:
            if os.path.exists(dummy_pdf):
                os.remove(dummy_pdf)

    asyncio.run(_test())


def test_calendar_exporter_and_wa_helper():
    exporter = ProductionCalendarExporter()
    job = JobCard(
        id="job_walkin_01",
        role=ExtractedRole(
            title="Junior Software Engineer",
            company="Walkin Tech",
            field="software engineering",
            walkin=WalkinDetails(
                date="2026-11-26",
                time="10:00 AM - 2:00 PM",
                address="Shahra-e-Faisal, Karachi",
            ),
        ),
    )
    ics = exporter.export_walkin_ics(job)
    assert ics is not None
    assert "BEGIN:VCALENDAR" in ics
    assert "Walk-in Interview" in ics
    assert "Shahra-e-Faisal, Karachi" in ics

    wa_link = generate_wa_apply_link("0313-1234567", "DevOps Engineer", "Paysys Labs", "Fahad Bin Nasir")
    assert "wa.me/923131234567" in wa_link
    assert "DevOps%20Engineer" in wa_link
