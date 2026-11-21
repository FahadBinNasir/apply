import asyncio
import os
import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.auth.security import LockoutManager, hash_password, verify_password, verify_session_token, create_session_token
from app.cv.verifier import AntiFabricationVerifier
from app.intake.security import sign_payload, verify_webhook_signature
from app.llm.provider import PrivacyViolationError, ProductionLLMProvider
from app.main import app, load_profile
from app.pipeline.linkfetch import _validate_ssrf
from app.pipeline.rules.dedupe import ProductionDeduper
from contracts.models import ExtractedRole, JobCard, TailorPlan


def test_sec_audit_auth_and_lockout():
    # 1. Bcrypt password security
    pw = "SecretSecurePass123"
    h = hash_password(pw)
    assert h.startswith("$2b$") or h.startswith("$2a$")
    assert verify_password(pw, h)
    assert not verify_password("Wrong", h)

    # 2. Lockout protection (5 failed attempts -> lockout)
    lm = LockoutManager(max_attempts=5, lockout_seconds=900)
    ip = "10.0.0.15"
    for _ in range(4):
        lm.record_failure(ip)
        assert not lm.is_locked_out(ip)[0]
    lm.record_failure(ip)
    is_locked, remaining = lm.is_locked_out(ip)
    assert is_locked
    assert remaining > 0


def test_sec_audit_webhook_security():
    import time
    secret = "production_webhook_secret_999"
    payload = b'{"event":"message","id":"123"}'
    ts = int(time.time())

    # Signature validation
    sig = sign_payload(payload, secret, ts)
    valid, err = verify_webhook_signature(payload, secret, sig, str(ts))
    assert valid

    # Tampered payload fails
    tampered = b'{"event":"message","id":"123","injected":true}'
    valid_t, err_t = verify_webhook_signature(tampered, secret, sig, str(ts))
    assert not valid_t
    assert "Invalid webhook HMAC signature" in err_t


def test_sec_audit_ssrf_and_privacy():
    # SSRF defenses
    assert not _validate_ssrf("http://127.0.0.1:8080/admin")[0]
    assert not _validate_ssrf("http://localhost:3000")[0]
    assert not _validate_ssrf("http://192.168.0.1/router")[0]
    assert not _validate_ssrf("http://10.0.0.1/internal")[0]

    # Privacy guard
    provider = ProductionLLMProvider()
    with pytest.raises(PrivacyViolationError):
        asyncio.run(provider.generate_json({}, "Contact applicant at fahadabbasi17025@gmail.com"))
    with pytest.raises(PrivacyViolationError):
        asyncio.run(provider.generate_json({}, "Call mobile +92 327 8262810 for interview"))


def test_sec_audit_http_headers():
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        headers = res.headers
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "content-security-policy" in headers


def test_a11y_audit_tokens_and_targets():
    css_path = Path("app/web/static/style.css")
    assert css_path.exists()
    css = css_path.read_text(encoding="utf-8")

    # Minimum touch target 44px
    assert "--touch-target: 44px" in css

    # Both Dark and Light themes defined
    assert '[data-theme="light"]' in css
    assert ":root" in css

    # Tier badge styling uses distinct glyphs/borders, not color alone
    assert ".badge-strong" in css
    assert ".badge-stretch" in css
    assert ".badge-manual" in css
    assert ".badge-walkin" in css
    assert ".badge-skipped" in css


def test_eval_audit_anti_fabrication():
    profile = load_profile()
    verifier = AntiFabricationVerifier()

    # Legitimate plan passes
    plan_good = TailorPlan(
        relevant_project_ids=["knowledge-brain", "churnvision"],
        summary_2_3_lines="7th semester student at Bahria University applying for backend role.",
    )
    ok, violations = verifier.verify_plan(plan_good, profile)
    assert ok
    assert len(violations) == 0

    # Fabricated experience rejected
    plan_bad = TailorPlan(
        relevant_project_ids=["invented_fintech_app"],
        summary_2_3_lines="7th semester student with 3 years WebForms experience at Google.",
    )
    ok, violations = verifier.verify_plan(plan_bad, profile)
    assert not ok
    assert len(violations) >= 2


def test_eval_audit_deduplication():
    deduper = ProductionDeduper()
    existing = [
        JobCard(
            id="job_existing",
            role=ExtractedRole(
                title="DevOps Engineer",
                company="Paysys Labs",
                field="DevOps",
                apply_email="hiring@paysyslabs.com",
            ),
        )
    ]
    # Company with suffix
    role_var1 = ExtractedRole(
        title="DevOps Engineer",
        company="Paysys Labs (Pvt) Ltd",
        field="DevOps",
        apply_email="hiring@paysyslabs.com",
    )
    assert deduper.find_duplicate(role_var1, existing) == "job_existing"

    # Normalized title variation
    role_var2 = ExtractedRole(
        title="DevOps Engineer - Karachi Onsite",
        company="Paysys Labs",
        field="DevOps",
        apply_email="hiring@paysyslabs.com",
    )
    assert deduper.find_duplicate(role_var2, existing) == "job_existing"
