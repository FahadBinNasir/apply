from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routers import router
from app.cv.builder import ProductionCVBuilder
from app.db.crypto import TokenEncryption
from app.db.repos import SQLAlchemyInboxRepo, SQLAlchemyJobRepo, SQLAlchemyQueue
from app.db.session import create_db_engine, init_db
from app.intake.handler import WebhookIntakeHandler
from app.intake.waha import WAHAIntakeAdapter
from app.llm.provider import ProductionLLMProvider
from app.mail.sender import ProductionMailer
from app.pipeline.extract import ProductionExtractor
from app.pipeline.linkfetch import ProductionLinkFetcher
from app.pipeline.prefilter import ProductionPreFilter
from app.pipeline.rules.dedupe import ProductionDeduper
from app.pipeline.rules.engine import ProductionRulesEngine
from app.pipeline.rules.scoring import ProductionScorer
from app.scheduler.tasks import setup_scheduler
from app.worker.pipeline import PipelineEngine
from app.worker.queue_worker import QueueWorker
from contracts.fakes import (
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
from contracts.models import (
    Profile,
    ProfileMatching,
    ProfileMatchingExperience,
    ProfilePersonal,
    ProfileProject,
    ProfileSkills,
    ProfileStatus,
)


def load_profile() -> Profile:
    profile_path = Path("profile.seed.yaml")
    if not profile_path.exists():
        # Minimal fallback
        return Profile(
            name="Fahad Bin Nasir",
            email="fahadabbasi17025@gmail.com",
            phone="+92 327 8262810",
            location="Karachi, Pakistan",
        )

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


class SystemClock:
    def now(self) -> datetime:
        override = os.getenv("NOW_OVERRIDE")
        if override:
            try:
                return datetime.fromisoformat(override)
            except Exception:
                pass
        return datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dependency Injection Initialization
    use_fakes = os.getenv("USE_FAKES", "false").lower() == "true"
    profile = load_profile()
    clock = SystemClock()

    if use_fakes:
        job_repo = FakeJobRepo()
        inbox_repo = FakeInboxRepo()
        queue = FakeQueue()
        intake_source = FakeIntakeSource()
        prefilter = ProductionPreFilter()
        llm = FakeLLMProvider()
        extractor = FakeExtractor()
        link_fetcher = FakeLinkFetcher()
        rules_engine = ProductionRulesEngine()
        scorer = ProductionScorer()
        deduper = ProductionDeduper()
        cv_builder = ProductionCVBuilder()
        mailer = ProductionMailer()
    else:
        from sqlalchemy.orm import sessionmaker
        engine = init_db()
        session_factory = sessionmaker(bind=engine)

        job_repo = SQLAlchemyJobRepo(session_factory)
        inbox_repo = SQLAlchemyInboxRepo(session_factory)
        queue = SQLAlchemyQueue(session_factory)
        intake_source = WAHAIntakeAdapter()
        prefilter = ProductionPreFilter()
        llm = ProductionLLMProvider()
        extractor = ProductionExtractor(llm)
        link_fetcher = ProductionLinkFetcher()
        rules_engine = ProductionRulesEngine()
        scorer = ProductionScorer()
        deduper = ProductionDeduper()
        cv_builder = ProductionCVBuilder()
        mailer = ProductionMailer()

    webhook_handler = WebhookIntakeHandler(inbox_repo, queue)

    pipeline = PipelineEngine(
        prefilter=prefilter,
        extractor=extractor,
        link_fetcher=link_fetcher,
        rules_engine=rules_engine,
        scorer=scorer,
        deduper=deduper,
        cv_builder=cv_builder,
        mailer=mailer,
        job_repo=job_repo,
        inbox_repo=inbox_repo,
        profile=profile,
    )

    worker = QueueWorker(queue, pipeline)
    worker_task = asyncio.create_task(worker.start())

    scheduler = setup_scheduler(job_repo, pipeline)
    scheduler.start()

    # Store on app.state
    app.state.job_repo = job_repo
    app.state.inbox_repo = inbox_repo
    app.state.queue = queue
    app.state.intake_source = intake_source
    app.state.webhook_handler = webhook_handler
    app.state.pipeline = pipeline
    app.state.profile = profile
    app.state.clock = clock
    app.state.mailer = mailer
    app.state.cv_builder = cv_builder

    yield

    # Teardown
    worker.stop()
    worker_task.cancel()
    scheduler.shutdown(wait=False)


app = FastAPI(title="WhatsApp Job Agent", version="1.0.0", lifespan=lifespan)

# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self';"
    )
    return response

# Static files & routers
static_dir = Path("app/web/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(router)
