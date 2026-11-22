import asyncio
import os
import pytest
from sqlalchemy.orm import sessionmaker

from app.main import load_profile
from app.db.session import create_db_engine
from app.db.models import Base
from app.db.repos import SQLAlchemyJobRepo, SQLAlchemyInboxRepo
from app.llm import provider as llm_provider_module
from app.llm.provider import ProductionLLMProvider
LLMUnavailableError = getattr(llm_provider_module, "LLMUnavailableError", type("LLMUnavailableError", (Exception,), {}))
from app.pipeline.extract import ProductionExtractor
from app.pipeline.linkfetch import ProductionLinkFetcher
from app.pipeline.prefilter import ProductionPreFilter
from app.pipeline.rules.dedupe import ProductionDeduper
from app.pipeline.rules.engine import ProductionRulesEngine
from app.pipeline.rules.scoring import ProductionScorer
from app.cv.builder import ProductionCVBuilder
from app.mail.sender import ProductionMailer
from app.worker.pipeline import PipelineEngine
from contracts.models import IncomingMessage


def test_no_keys_produces_no_fake_jobs():
    # Remove keys
    old_gemini = os.environ.pop("GEMINI_API_KEY", None)
    old_groq = os.environ.pop("GROQ_API_KEY", None)

    try:
        eng = create_db_engine(db_url="sqlite:///:memory:")
        Base.metadata.create_all(eng)
        sf = sessionmaker(bind=eng)

        llm = ProductionLLMProvider()
        p = PipelineEngine(
            ProductionPreFilter(),
            ProductionExtractor(llm),
            ProductionLinkFetcher(),
            ProductionRulesEngine(),
            ProductionScorer(),
            ProductionDeduper(),
            ProductionCVBuilder(),
            ProductionMailer(),
            SQLAlchemyJobRepo(sf),
            SQLAlchemyInboxRepo(sf),
            load_profile(),
        )

        async def _run():
            # 1. Birthday message must never produce a fake Tech Company job card
            birthday_msg = IncomingMessage(
                source_id="NOISE_birthday",
                chat_id="x@g.us",
                chat_name="TestGroup",
                raw_text="Happy birthday to our batchmate Ali! Wishing you the best, party at 8pm everyone should join us tonight",
            )
            try:
                cards = await p.process_message(birthday_msg)
                # If cards are returned, none of them should be a fake heuristic job
                for c in cards:
                    assert c.role.company != "Tech Company", "Must not produce fake Tech Company job card"
                    assert "Ali" not in c.role.title
                assert len(cards) == 0, f"Expected 0 cards for birthday noise, got {len(cards)}"
            except LLMUnavailableError:
                # Raising LLMUnavailableError without creating fake cards is also acceptable
                pass

        asyncio.run(_run())
    finally:
        if old_gemini:
            os.environ["GEMINI_API_KEY"] = old_gemini
        if old_groq:
            os.environ["GROQ_API_KEY"] = old_groq
