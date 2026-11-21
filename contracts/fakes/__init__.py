"""
In-memory fake implementations of all contract protocols.
Usable by all agents for unit tests and local mock execution without external services.
"""

from contracts.fakes.fake_intake import FakeIntakeSource
from contracts.fakes.fake_llm import FakeLLMProvider
from contracts.fakes.fake_prefilter import FakePreFilter
from contracts.fakes.fake_extract import FakeExtractor
from contracts.fakes.fake_linkfetch import FakeLinkFetcher
from contracts.fakes.fake_rules import FakeRulesEngine, FakeScorer, FakeDeduper
from contracts.fakes.fake_cvmail import FakeCVBuilder, FakeMailer, FakeCalendarExporter
from contracts.fakes.fake_repo import FakeJobRepo, FakeInboxRepo
from contracts.fakes.fake_queue import FakeQueue

__all__ = [
    "FakeIntakeSource",
    "FakeLLMProvider",
    "FakePreFilter",
    "FakeExtractor",
    "FakeLinkFetcher",
    "FakeRulesEngine",
    "FakeScorer",
    "FakeDeduper",
    "FakeCVBuilder",
    "FakeMailer",
    "FakeCalendarExporter",
    "FakeJobRepo",
    "FakeInboxRepo",
    "FakeQueue",
]
