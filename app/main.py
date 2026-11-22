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
    ProfileEducation,
    ProfileMatching,
    ProfileMatchingExperience,
    ProfilePersonal,
    ProfileProject,
    ProfileSkills,
    ProfileStatus,
    Settings,
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

    def clean_val(v):
        if isinstance(v, str) and v.startswith("TODO"):
            return None
        return v

    personal_data = data.get("personal", {})
    status_data = data.get("status", {})
    matching_data = data.get("matching", {})
    links_data = {
        k: v for k, v in data.get("links", {}).items()
        if not str(v).startswith("TODO")
    }

    gender_val = clean_val(personal_data.get("gender"))
    night_shift_raw = personal_data.get("accepts_night_shift")
    night_shift = bool(night_shift_raw) if not str(night_shift_raw).startswith("TODO") else False

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

    edu = [
        ProfileEducation(
            degree=e["degree"],
            school=e["school"],
            years=e.get("years", ""),
            note=clean_val(e.get("note")),
        )
        for e in data.get("education", [])
    ]

    exp = matching_data.get("experience", {})

    return Profile(
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        location=data["location"],
        links=links_data,
        personal=ProfilePersonal(
            gender=gender_val,
            accepts_night_shift=night_shift,
            languages=personal_data.get("languages", []),
        ),
        status=ProfileStatus(
            degree=status_data.get("degree", ""),
            university=status_data.get("university", ""),
            semester=int(status_data.get("semester", 7)),
            expected_graduation=clean_val(status_data.get("expected_graduation")),
            available_as=status_data.get("available_as", []),
        ),
        matching=ProfileMatching(
            hard_locations=matching_data.get("hard_locations", []),
            remote_must_accept_pakistan=matching_data.get("remote_must_accept_pakistan", True),
            target_fields=matching_data.get("target_fields", []),
            avoid_fields=matching_data.get("avoid_fields", []),
            experience=ProfileMatchingExperience(
                comfortable_max_years=float(exp.get("comfortable_max_years", 2.0)),
                stretch_max_years=float(exp.get("stretch_max_years", 3.0)),
                skip_above_years=float(exp.get("skip_above_years", 3.0)),
            ),
            notes=matching_data.get("notes"),
        ),
        skills=ProfileSkills(
            languages=data["skills"].get("languages", []),
            ai_ml=data["skills"].get("ai_ml", []),
            web_backend=data["skills"].get("web_backend", []),
            mobile_tools=data["skills"].get("mobile_tools", []),
            concepts=data["skills"].get("concepts", []),
        ),
        education=edu,
        projects=projects,
        courses=data.get("courses", []),
        experience=data.get("experience", []),
        achievements=data.get("achievements", []),
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
    is_prod = os.getenv("APP_ENV", "").lower() == "production"
    if is_prod and not use_fakes:
        pwd = os.getenv("DASHBOARD_PASSWORD") or os.getenv("DASHBOARD_PASSWORD_HASH")
        sec = os.getenv("SESSION_SECRET")
        wh_sec = os.getenv("WEBHOOK_SECRET")
        if not pwd:
            raise RuntimeError(
                "Production startup failed: DASHBOARD_PASSWORD or DASHBOARD_PASSWORD_HASH must be configured."
            )
        if not sec or sec == "dev_session_secret_change_in_production":
            raise RuntimeError(
                "Production startup failed: SESSION_SECRET must be set to a secure secret."
            )
        if not wh_sec:
            raise RuntimeError(
                "Production startup failed: WEBHOOK_SECRET must be configured."
            )

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
        mailer = ProductionMailer(job_repo=job_repo)
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
        mailer = ProductionMailer(job_repo=job_repo)

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
    settings = Settings(
        send_enabled=os.getenv("SEND_ENABLED", "false").lower() == "true",
        daily_send_cap=int(os.getenv("DAILY_SEND_CAP", "25")),
        min_gap_seconds=int(os.getenv("MIN_GAP_SECONDS", "60")),
        gemini_model_fast=os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash"),
        gemini_model_smart=os.getenv("GEMINI_MODEL_SMART", "gemini-2.5-flash"),
        groq_fallback_enabled=bool(os.getenv("GROQ_API_KEY")),
        now_override=os.getenv("NOW_OVERRIDE"),
    )
    app.state.settings = settings
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
