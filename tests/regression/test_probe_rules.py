import os
import pytest
from app.main import load_profile
from app.pipeline.rules.engine import ProductionRulesEngine
from contracts.models import ExtractedRole, WorkMode, ApplyMethod, Tier

os.environ["NOW_OVERRIDE"] = "2026-11-21T00:00:00"


def make_role(**kwargs):
    base = dict(
        title="Software Engineer",
        company="Acme",
        field="software engineering",
        city="Karachi",
        location_text="Karachi",
        work_mode=WorkMode.ONSITE,
        apply_method=ApplyMethod.EMAIL,
        apply_email="hr@acme.pk",
        experience_min_years=0.0,
        skills=["Python"],
    )
    base.update(kwargs)
    return ExtractedRole(**base)


def test_probe_rules_seniority_and_bounds():
    profile = load_profile()
    engine = ProductionRulesEngine()

    # 1. Seniority should be SKIPPED
    senior_role = make_role(title="Senior Software Engineer")
    t, reasons, score, _, _ = engine.evaluate(senior_role, profile)
    assert t == Tier.SKIPPED, f"Expected SKIPPED for Senior Software Engineer, got {t.value}"
    assert any("senior" in r.lower() for r in reasons)

    # 2. Unpaid/Volunteer should be SKIPPED
    unpaid_role = make_role(title="Software Developer volunteer", notes="unpaid volunteer position")
    t, reasons, score, _, _ = engine.evaluate(unpaid_role, profile)
    assert t == Tier.SKIPPED, f"Expected SKIPPED for unpaid/volunteer, got {t.value}"

    # 3. 3 yrs experience should be SKIPPED (profile skip_above_years is 3.0)
    exp_role = make_role(experience_min_years=3.0)
    t, reasons, score, _, _ = engine.evaluate(exp_role, profile)
    assert t == Tier.SKIPPED, f"Expected SKIPPED for >=3 years, got {t.value}"

    # 4. Missing/empty field must NOT be STRONG (should be STRETCH with reason)
    no_field = make_role(field="")
    t, reasons, score, _, _ = engine.evaluate(no_field, profile)
    assert t != Tier.STRONG, f"Empty field should not be STRONG, got {t.value}"
    assert t == Tier.STRETCH

    # 5. Clamped scores: 0 <= score <= 100
    today_role = make_role(deadline="22 Nov 2026")
    _, _, score, _, _ = engine.evaluate(today_role, profile)
    assert 0 <= score <= 100, f"Score should be clamped to 100, got {score}"


def test_probe_rules_avoid_false_positives():
    profile = load_profile()
    engine = ProductionRulesEngine()

    # Civil Engineer -> SKIPPED
    civil = make_role(title="Civil Engineer", field="civil engineering", skills=[])
    t, _, _, _, _ = engine.evaluate(civil, profile)
    assert t == Tier.SKIPPED, f"Civil Engineer should be SKIPPED, got {t.value}"

    # Customer Support -> SKIPPED
    support = make_role(title="Customer Support Executive", field="customer support", skills=["email"])
    t, _, _, _, _ = engine.evaluate(support, profile)
    assert t == Tier.SKIPPED, f"Customer Support should be SKIPPED, got {t.value}"

    # Graphic Designer -> SKIPPED
    designer = make_role(title="Graphic Designer", field="design", skills=["Figma"])
    t, _, _, _, _ = engine.evaluate(designer, profile)
    assert t == Tier.SKIPPED, f"Graphic Designer should be SKIPPED, got {t.value}"
