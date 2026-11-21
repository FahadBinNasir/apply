import asyncio
import pytest

from app.llm.provider import PrivacyViolationError, ProductionLLMProvider
from app.pipeline.extract import ProductionExtractor
from app.pipeline.linkfetch import ProductionLinkFetcher, _strip_tracking_params, _validate_ssrf
from app.pipeline.prefilter import ProductionPreFilter
from contracts.fakes import FakeLLMProvider
from contracts.models import ApplyMethod, IncomingMessage, PostType


def test_prefilter_noise_cases():
    prefilter = ProductionPreFilter()

    # 1. Empty message
    msg_empty = IncomingMessage(source_id="1", chat_id="c1", raw_text="")
    is_noise, reason = prefilter.evaluate(msg_empty)
    assert is_noise
    assert reason == "empty_message"

    # 2. Greeting
    msg_greeting = IncomingMessage(source_id="2", chat_id="c1", raw_text="AOA everyone")
    is_noise, reason = prefilter.evaluate(msg_greeting)
    assert is_noise

    # 3. Convocation
    msg_convocation = IncomingMessage(source_id="3", chat_id="c1", raw_text="Bahria 22nd Convocation announcement and registration.")
    is_noise, reason = prefilter.evaluate(msg_convocation)
    assert is_noise
    assert "convocation" in reason or "event" in reason

    # 4. Fundraising
    msg_fund = IncomingMessage(source_id="4", chat_id="c1", raw_text="Legacy Medal alumni fundraising post.")
    is_noise, reason = prefilter.evaluate(msg_fund)
    assert is_noise

    # 5. Survey
    msg_survey = IncomingMessage(source_id="5", chat_id="c1", raw_text="Please fill out this Master's research survey via google form forms.gle/123")
    is_noise, reason = prefilter.evaluate(msg_survey)
    assert is_noise

    # 6. Matrimonial
    msg_matrimonial = IncomingMessage(source_id="6", chat_id="c1", raw_text="Exclusive matrimonial proposal platform for doctors and engineers.")
    is_noise, reason = prefilter.evaluate(msg_matrimonial)
    assert is_noise

    # 7. Alumni lookup
    msg_alumni = IncomingMessage(source_id="7", chat_id="c1", raw_text="Is there any alumnus working at JBS Global?")
    is_noise, reason = prefilter.evaluate(msg_alumni)
    assert is_noise

    # 8. Real job should NOT be noise
    msg_job = IncomingMessage(
        source_id="8",
        chat_id="c1",
        raw_text="We're Hiring – DevOps Engineer at Paysys Labs. Location: Karachi. Send CV to hiring@paysyslabs.com",
    )
    is_noise, reason = prefilter.evaluate(msg_job)
    assert not is_noise


def test_linkfetcher_ssrf_and_sanitization():
    # SSRF guard on loopback
    is_safe, err = _validate_ssrf("http://127.0.0.1:8080/secret")
    assert not is_safe
    assert "Localhost" in err or "private" in err

    is_safe, err = _validate_ssrf("http://localhost:3000")
    assert not is_safe

    # SSRF guard on private subnet
    is_safe, err = _validate_ssrf("http://192.168.1.100/admin")
    assert not is_safe
    assert "private" in err

    # Tracking param stripping
    clean = _strip_tracking_params("https://example.com/job?id=123&utm_source=whatsapp&utm_medium=channel&ref=xyz")
    assert clean == "https://example.com/job?id=123"

    # LinkedIn wall check
    async def _test_linkedin():
        fetcher = ProductionLinkFetcher()
        success, text, err = await fetcher.fetch_link("https://www.linkedin.com/jobs/view/999")
        assert not success
        assert "LinkedIn" in err

    asyncio.run(_test_linkedin())


def test_privacy_guard():
    provider = ProductionLLMProvider()

    # Prompt containing Fahad's personal email must be rejected
    with pytest.raises(PrivacyViolationError):
        asyncio.run(provider.generate_json({}, "Tell me about fahadabbasi17025@gmail.com"))

    # Prompt containing Fahad's phone number must be rejected
    with pytest.raises(PrivacyViolationError):
        asyncio.run(provider.generate_json({}, "Candidate contact +92 327 8262810"))


def test_extractor_with_mock():
    fake_llm = FakeLLMProvider()
    extractor = ProductionExtractor(fake_llm)

    msg = IncomingMessage(
        source_id="msg_01",
        chat_id="chat_01",
        chat_name="Jobs Group",
        raw_text="We're Hiring – DevOps Engineer at Paysys Labs.",
    )

    async def _test():
        res = await extractor.extract(msg)
        assert res.is_job
        assert res.post_type == PostType.JOB
        assert len(res.roles) >= 1
        role = res.roles[0]
        assert role.title == "Software Engineer"
        assert role.apply_method == ApplyMethod.EMAIL

    asyncio.run(_test())
