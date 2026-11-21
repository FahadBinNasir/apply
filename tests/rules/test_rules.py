from datetime import datetime
from pathlib import Path
import yaml
import pytest

from app.pipeline.rules.dedupe import ProductionDeduper
from app.pipeline.rules.engine import ProductionRulesEngine
from app.pipeline.rules.scoring import ProductionScorer
from contracts.models import (
    ApplyMethod,
    ExtractedRole,
    JobCard,
    Profile,
    ProfileMatching,
    ProfileMatchingExperience,
    ProfilePersonal,
    ProfileSkills,
    ProfileStatus,
    Tier,
    WalkinDetails,
    WorkMode,
)


@pytest.fixture
def profile():
    profile_path = Path("profile.seed.yaml")
    assert profile_path.exists()
    with open(profile_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Profile(
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        location=data["location"],
        links=data.get("links", {}),
        personal=ProfilePersonal(
            gender=None,  # unknown per TODO in seed
            accepts_night_shift=False,
            languages=data["personal"].get("languages", []),
        ),
        status=ProfileStatus(
            degree=data["status"]["degree"],
            university=data["status"]["university"],
            semester=data["status"]["semester"],
            available_as=data["status"]["available_as"],
        ),
        matching=ProfileMatching(
            hard_locations=data["matching"]["hard_locations"],
            remote_must_accept_pakistan=data["matching"]["remote_must_accept_pakistan"],
            target_fields=data["matching"]["target_fields"],
            avoid_fields=data["matching"]["avoid_fields"],
            experience=ProfileMatchingExperience(
                comfortable_max_years=data["matching"]["experience"]["comfortable_max_years"],
                stretch_max_years=data["matching"]["experience"]["stretch_max_years"],
                skip_above_years=data["matching"]["experience"]["skip_above_years"],
            ),
        ),
        skills=ProfileSkills(
            languages=data["skills"]["languages"],
            ai_ml=data["skills"]["ai_ml"],
            web_backend=data["skills"]["web_backend"],
            mobile_tools=data["skills"]["mobile_tools"],
            concepts=data["skills"]["concepts"],
        ),
        education=[],
        projects=[],
    )


NOW = datetime(2026, 11, 21, 0, 0, 0)


def test_f1_paysys_devops(profile):
    engine = ProductionRulesEngine()
    scorer = ProductionScorer()
    role = ExtractedRole(
        title="DevOps Engineer",
        company="Paysys Labs",
        field="DevOps / cloud",
        location_text="Karachi (On-site)",
        work_mode=WorkMode.ONSITE,
        city="Karachi",
        experience_min_years=0.0,
        experience_max_years=1.0,
        education="Bachelor's degree in Computer Science, Software Engineering, IT",
        skills=["CI/CD pipelines", "Linux administration", "SQL", "Git", "Scripting", "API testing"],
        responsibilities=["CI/CD", "Linux"],
        apply_method=ApplyMethod.EMAIL,
        apply_email="hiring@paysyslabs.com",
        exact_subject="DevOps Engineer – Application",
        fresh_grad_ok=True,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    final_tier, final_score, summary = scorer.score(role, tier, reasons, score, profile)

    assert final_tier == Tier.STRONG
    assert final_score >= 70.0
    assert role.exact_subject == "DevOps Engineer – Application"
    assert role.apply_email == "hiring@paysyslabs.com"


def test_f2_decibel_mto(profile):
    engine = ProductionRulesEngine()
    scorer = ProductionScorer()
    role = ExtractedRole(
        title="MTO - Dot Net Developer",
        company="Decibel HRMS",
        field=".NET / C# junior",
        location_text="Shahra-e-Faisal, Karachi",
        work_mode=WorkMode.ONSITE,
        city="Karachi",
        experience_min_years=0.0,
        experience_max_years=1.0,
        skills=["C#", "ASP .NET with webforms", "REST APIs", "SQL"],
        apply_method=ApplyMethod.EMAIL,
        apply_email="careers@decibel360.com",
        exact_subject="MTO - Dot Net Developer",
        fresh_grad_ok=True,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    final_tier, final_score, summary = scorer.score(role, tier, reasons, score, profile)

    assert final_tier == Tier.STRONG
    assert final_score >= 70.0


def test_f3_ebg_storage_compute(profile):
    engine = ProductionRulesEngine()
    scorer = ProductionScorer()
    role = ExtractedRole(
        title="Storage & Compute Intern",
        company="EBG Partner",
        field="IT infrastructure (Enterprise Storage, Compute Technologies)",
        location_text="Karachi, Pakistan",
        work_mode=WorkMode.ONSITE,
        city="Karachi",
        experience_min_years=0.0,
        experience_max_years=0.0,
        skills=["Enterprise Storage", "Compute Technologies", "Data Center Infrastructure"],
        apply_method=ApplyMethod.EMAIL,
        apply_email="muhammad.bilal.ahmed30@gmail.com",
        fresh_grad_ok=True,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    final_tier, final_score, summary = scorer.score(role, tier, reasons, score, profile)

    assert final_tier == Tier.STRETCH
    assert any("infrastructure" in r.lower() or "stretch" in r.lower() for r in reasons)


def test_f4_pentaloop_ios_lahore(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="ASE - iOS Developer",
        company="Pentaloop",
        field="mobile (Flutter/iOS)",
        location_text="Johar Town, Lahore",
        work_mode=WorkMode.ONSITE,
        city="Lahore",
        experience_min_years=0.0,
        apply_method=ApplyMethod.EMAIL,
        apply_email="hr@pentaloop.com",
        fresh_grad_ok=True,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("lahore" in r.lower() for r in reasons)


def test_f5_techtimize_lahore(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="MERN + AI Intern",
        company="Techtimize",
        field="full-stack web",
        location_text="Lahore onsite",
        work_mode=WorkMode.ONSITE,
        city="Lahore",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@techtimize.co",
        fresh_grad_ok=True,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("lahore" in r.lower() for r in reasons)


def test_f6_superior_university_ms_required(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="Lecturer for CS & IT",
        company="Superior University",
        field="software engineering",
        location_text="Karachi",
        education="MS in SE, CS, IT & DA Required",
        apply_method=ApplyMethod.EMAIL,
        apply_email="hr@superior.edu.pk",
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("ms" in r.lower() for r in reasons)


def test_f7_wenawa_bd_trainee(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="Business Development Trainee",
        company="Wenawa",
        field="Business Development",
        location_text="Hybrid Karachi",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@wenawa.com",
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("avoid" in r.lower() or "business development" in r.lower() for r in reasons)


def test_f10_code_avenue_senior_pm(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="Senior Project Manager",
        company="Code Avenue",
        field="software engineering",
        location_text="Karachi",
        experience_min_years=4.0,
        experience_max_years=6.0,
        apply_method=ApplyMethod.EMAIL,
        apply_email="hr@codeavenue.com",
        fresh_grad_ok=False,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("experience" in r.lower() for r in reasons)


def test_f11_alkhidmat_expired(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="HR & Admin Officer",
        company="Alkhidmat",
        field="HR, admin",
        location_text="Karachi",
        deadline="2026-11-20",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@alkhidmat.org",
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("expired" in r.lower() or "avoid" in r.lower() for r in reasons)


def test_f12_nimir_expired_and_lahore(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="MTO Chemical Engineer",
        company="Nimir Chemicals",
        field="engineering",
        location_text="Lahore",
        deadline="2026-11-16",
        apply_method=ApplyMethod.EMAIL,
        apply_email="careers@nimir.com.pk",
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED


def test_deduper():
    deduper = ProductionDeduper()
    existing_job = JobCard(
        id="job_001",
        role=ExtractedRole(
            title="DevOps Engineer",
            company="Paysys Labs",
            field="DevOps",
            apply_email="hiring@paysyslabs.com",
        ),
    )
    # Same company & title
    duplicate_role = ExtractedRole(
        title="DevOps Engineer (Karachi)",
        company="Paysys Labs Inc.",
        field="DevOps",
        apply_email="hiring@paysyslabs.com",
    )
    assert deduper.find_duplicate(duplicate_role, [existing_job]) == "job_001"

    different_role = ExtractedRole(
        title="Flutter Developer",
        company="Folio3",
        field="Mobile",
        apply_email="careers@folio3.com",
    )
    assert deduper.find_duplicate(different_role, [existing_job]) is None


def test_gender_unknown_flags_stretch(profile):
    engine = ProductionRulesEngine()
    scorer = ProductionScorer()
    role = ExtractedRole(
        title="Associate Software Engineer",
        company="Tech Women Org",
        field="software engineering",
        location_text="Karachi",
        gender_requirement="female",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@techwomen.org",
        fresh_grad_ok=True,
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    final_tier, final_score, summary = scorer.score(role, tier, reasons, score, profile)
    assert final_tier == Tier.STRETCH
    assert any("female" in r.lower() for r in reasons)


def test_night_shift_rejection(profile):
    engine = ProductionRulesEngine()
    role = ExtractedRole(
        title="Junior Support Engineer",
        company="Night Ops Co",
        field="software engineering",
        location_text="Karachi",
        night_shift=True,
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@nightops.com",
    )
    tier, reasons, score, matches, gaps = engine.evaluate(role, profile, now_override=NOW)
    assert tier == Tier.SKIPPED
    assert any("night shift" in r.lower() for r in reasons)
