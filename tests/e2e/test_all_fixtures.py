import asyncio
import json
from datetime import datetime
from pathlib import Path
import pytest

from app.main import load_profile
from app.pipeline.extract import ProductionExtractor
from app.pipeline.linkfetch import ProductionLinkFetcher
from app.pipeline.prefilter import ProductionPreFilter
from app.pipeline.rules.dedupe import ProductionDeduper
from app.pipeline.rules.engine import ProductionRulesEngine
from app.pipeline.rules.scoring import ProductionScorer
from app.worker.pipeline import PipelineEngine
from contracts.fakes import (
    FakeCVBuilder,
    FakeExtractor,
    FakeInboxRepo,
    FakeJobRepo,
    FakeLinkFetcher,
    FakeMailer,
    FakePreFilter,
)
from contracts.models import ExtractedRole, IncomingMessage, Tier, WorkMode, ApplyMethod


@pytest.fixture
def expected_fixtures():
    path = Path("contracts/fixtures.expected.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_gate_g2_all_fixtures_offline(expected_fixtures):
    profile = load_profile()
    clock_dt = datetime.fromisoformat(expected_fixtures["test_clock"])

    engine = ProductionRulesEngine()
    scorer = ProductionScorer()

    # F1 - Paysys Labs DevOps => STRONG
    f1_role = ExtractedRole(
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
        apply_method=ApplyMethod.EMAIL,
        apply_email="hiring@paysyslabs.com",
        exact_subject="DevOps Engineer – Application",
        fresh_grad_ok=True,
    )
    t1, r1, s1, _, _ = engine.evaluate(f1_role, profile, now_override=clock_dt)
    final_t1, _, _ = scorer.score(f1_role, t1, r1, s1, profile)
    assert final_t1.value == expected_fixtures["fixtures"]["F1"]["expected_tier"]

    # F2 - Decibel MTO .NET => STRONG
    f2_role = ExtractedRole(
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
    t2, r2, s2, _, _ = engine.evaluate(f2_role, profile, now_override=clock_dt)
    final_t2, _, _ = scorer.score(f2_role, t2, r2, s2, profile)
    assert final_t2.value == expected_fixtures["fixtures"]["F2"]["expected_tier"]

    # F3 - EBG Storage & Compute => STRETCH
    f3_role = ExtractedRole(
        title="Storage & Compute Intern",
        company="EBG Partner",
        field="IT infrastructure (Enterprise Storage, Compute Technologies)",
        location_text="Karachi, Pakistan",
        work_mode=WorkMode.ONSITE,
        city="Karachi",
        experience_min_years=0.0,
        apply_method=ApplyMethod.EMAIL,
        apply_email="muhammad.bilal.ahmed30@gmail.com",
        fresh_grad_ok=True,
    )
    t3, r3, s3, _, _ = engine.evaluate(f3_role, profile, now_override=clock_dt)
    final_t3, _, _ = scorer.score(f3_role, t3, r3, s3, profile)
    assert final_t3.value == expected_fixtures["fixtures"]["F3"]["expected_tier"]

    # F4 - Pentaloop iOS (Lahore) => SKIPPED(location)
    f4_role = ExtractedRole(
        title="ASE - iOS Developer",
        company="Pentaloop",
        field="mobile (Flutter)",
        location_text="Johar Town, Lahore",
        work_mode=WorkMode.ONSITE,
        city="Lahore",
        apply_method=ApplyMethod.EMAIL,
        apply_email="hr@pentaloop.com",
    )
    t4, _, _, _, _ = engine.evaluate(f4_role, profile, now_override=clock_dt)
    assert t4.value == expected_fixtures["fixtures"]["F4"]["expected_tier"]

    # F5 - Techtimize MERN + AI intern (Lahore onsite) => SKIPPED(location)
    f5_role = ExtractedRole(
        title="MERN + AI Intern",
        company="Techtimize",
        field="full-stack web",
        location_text="Lahore onsite",
        work_mode=WorkMode.ONSITE,
        city="Lahore",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@techtimize.com",
    )
    t5, _, _, _, _ = engine.evaluate(f5_role, profile, now_override=clock_dt)
    assert t5.value == expected_fixtures["fixtures"]["F5"]["expected_tier"]

    # F6 - Superior University Lecturer CS & IT (MS required) => SKIPPED(education)
    f6_role = ExtractedRole(
        title="Lecturer for CS & IT",
        company="Superior University",
        field="software engineering",
        location_text="Karachi",
        education="MS in SE, CS, IT & DA Required",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@superior.edu.pk",
    )
    t6, _, _, _, _ = engine.evaluate(f6_role, profile, now_override=clock_dt)
    assert t6.value == expected_fixtures["fixtures"]["F6"]["expected_tier"]

    # F7 - Wenawa BD Trainee => SKIPPED(field)
    f7_role = ExtractedRole(
        title="Business Development Trainee",
        company="Wenawa",
        field="Business Development",
        location_text="Hybrid Karachi",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@wenawa.com",
    )
    t7, _, _, _, _ = engine.evaluate(f7_role, profile, now_override=clock_dt)
    assert t7.value == expected_fixtures["fixtures"]["F7"]["expected_tier"]

    # F8 - Inovativex BD Intern => SKIPPED(field)
    f8_role = ExtractedRole(
        title="BD Intern",
        company="Inovativex",
        field="sales, business development",
        location_text="Remote",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@inovativex.com",
    )
    t8, _, _, _, _ = engine.evaluate(f8_role, profile, now_override=clock_dt)
    assert t8.value == expected_fixtures["fixtures"]["F8"]["expected_tier"]

    # F9 - Roomi Associates (ACCA/CA) => SKIPPED(field)
    f9_role = ExtractedRole(
        title="Audit Trainee",
        company="Roomi Associates",
        field="accounting, finance",
        location_text="Karachi",
        education="ACCA / CA Inter",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@roomi.com",
    )
    t9, _, _, _, _ = engine.evaluate(f9_role, profile, now_override=clock_dt)
    assert t9.value == expected_fixtures["fixtures"]["F9"]["expected_tier"]

    # F10 - Code Avenue Senior PM => SKIPPED(experience)
    f10_role = ExtractedRole(
        title="Senior Project Manager",
        company="Code Avenue",
        field="software engineering",
        location_text="Karachi",
        experience_min_years=4.0,
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@codeavenue.com",
    )
    t10, _, _, _, _ = engine.evaluate(f10_role, profile, now_override=clock_dt)
    assert t10.value == expected_fixtures["fixtures"]["F10"]["expected_tier"]

    # F11 - Alkhidmat HR & Admin (deadline 20 Nov 2026) => SKIPPED(expired & field)
    f11_role = ExtractedRole(
        title="HR & Admin Officer",
        company="Alkhidmat",
        field="HR, admin",
        location_text="Karachi",
        deadline="2026-11-20",
        apply_method=ApplyMethod.EMAIL,
        apply_email="jobs@alkhidmat.org",
    )
    t11, _, _, _, _ = engine.evaluate(f11_role, profile, now_override=clock_dt)
    assert t11.value == expected_fixtures["fixtures"]["F11"]["expected_tier"]

    # F12 - Nimir Chemicals MTO Lahore (deadline 16 Nov 2026) => SKIPPED(location & expired)
    f12_role = ExtractedRole(
        title="MTO Chemical Engineer",
        company="Nimir Chemicals",
        field="engineering",
        location_text="Lahore",
        deadline="2026-11-16",
        apply_method=ApplyMethod.EMAIL,
        apply_email="careers@nimir.com.pk",
    )
    t12, _, _, _, _ = engine.evaluate(f12_role, profile, now_override=clock_dt)
    assert t12.value == expected_fixtures["fixtures"]["F12"]["expected_tier"]
