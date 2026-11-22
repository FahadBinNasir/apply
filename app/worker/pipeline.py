from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from contracts.models import (
    ApplyMethod,
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    IncomingMessage,
    JobCard,
    Profile,
    Status,
    Tier,
)
from contracts.protocols import (
    CVBuilder,
    Deduper,
    Extractor,
    InboxRepo,
    JobRepo,
    LinkFetcher,
    Mailer,
    PreFilter,
    RulesEngine,
    Scorer,
)

URL_REGEX = re.compile(r"https?://[^\s]+")


class PipelineEngine:
    """End-to-end extraction, evaluation, tailoring, and card generation pipeline."""

    def __init__(
        self,
        prefilter: PreFilter,
        extractor: Extractor,
        link_fetcher: LinkFetcher,
        rules_engine: RulesEngine,
        scorer: Scorer,
        deduper: Deduper,
        cv_builder: CVBuilder,
        mailer: Mailer,
        job_repo: JobRepo,
        inbox_repo: InboxRepo,
        profile: Profile,
    ):
        self.prefilter = prefilter
        self.extractor = extractor
        self.link_fetcher = link_fetcher
        self.rules_engine = rules_engine
        self.scorer = scorer
        self.deduper = deduper
        self.cv_builder = cv_builder
        self.mailer = mailer
        self.job_repo = job_repo
        self.inbox_repo = inbox_repo
        self.profile = profile

    async def process_message(
        self,
        message: IncomingMessage,
        now_override: Optional[datetime] = None,
    ) -> List[JobCard]:
        # Stage 1: Pre-filter (No LLM)
        is_noise, noise_reason = self.prefilter.evaluate(message)
        if is_noise:
            await self.inbox_repo.log_noise(message, noise_reason or "prefilter_drop")
            return []

        # Stage 2: Link Fetching for headline posts
        raw_text = message.raw_text
        urls = URL_REGEX.findall(raw_text)
        if urls and len(raw_text) < 150:
            target_url = urls[0]
            success, content, err = await self.link_fetcher.fetch_link(target_url)
            if success:
                raw_text = f"{raw_text}\n\n[LINK CONTENT FETCHED]:\n{content}"
            elif "LinkedIn" in str(err):
                # Special MANUAL tier for LinkedIn link posts
                role = ExtractedRole(
                    title="External Opening (LinkedIn)",
                    company="External Employer",
                    field="software engineering",
                    apply_method=ApplyMethod.LINKEDIN,
                    apply_link=target_url,
                    notes=err,
                )
                card = JobCard(
                    id=f"job_{uuid.uuid4().hex[:12]}",
                    role=role,
                    tier=Tier.MANUAL,
                    tier_reasons=["LinkedIn link post requires browser action"],
                    score=50.0,
                    status=Status.NEW,
                    fit_summary="LinkedIn post link requiring manual review",
                    source_messages=[message.chat_name],
                )
                await self.job_repo.save(card)
                return [card]

        updated_msg = message.model_copy(update={"raw_text": raw_text})

        # Stage 3: Extraction (support poster images)
        image_bytes = None
        mime_type = message.media_mime
        if message.media_path and Path(message.media_path).exists():
            try:
                image_bytes = Path(message.media_path).read_bytes()
            except Exception as e:
                logger.warning("Failed to read media file %s: %s", message.media_path, e)

        extraction = await self.extractor.extract(updated_msg, image_bytes=image_bytes, mime_type=mime_type)
        if not extraction.is_job or not extraction.roles:
            await self.inbox_repo.log_noise(message, "no_roles_extracted")
            return []

        existing_jobs = await self.job_repo.list_cards(limit=200)
        created_cards: List[JobCard] = []

        # Process each extracted role (multi-role split)
        for role in extraction.roles:
            # Deduplication
            duplicate_id = self.deduper.find_duplicate(role, existing_jobs)
            if duplicate_id:
                dup_job = await self.job_repo.get_by_id(duplicate_id)
                if dup_job:
                    if message.chat_name and message.chat_name not in dup_job.source_messages:
                        dup_job.source_messages.append(message.chat_name)
                        await self.job_repo.save(dup_job)
                    continue

            # Stage 4: Rules evaluation & Scoring
            tier, reasons, score_mod, matches, gaps = self.rules_engine.evaluate(
                role, self.profile, now_override=now_override
            )
            final_tier, final_score, summary = self.scorer.score(
                role, tier, reasons, score_mod, self.profile
            )

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            card = JobCard(
                id=job_id,
                role=role,
                tier=final_tier,
                tier_reasons=reasons,
                score=final_score,
                status=Status.DRAFTED if final_tier in [Tier.STRONG, Tier.STRETCH] else Status.NEW,
                fit_summary=summary,
                matches=matches,
                gaps=gaps,
                source_messages=[message.chat_name],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Stage 5: Tailoring & Drafting (for actionable tiers)
            if final_tier in [Tier.STRONG, Tier.STRETCH]:
                plan = await self.cv_builder.plan_tailoring(role, self.profile)
                cv = await self.cv_builder.build_cv(role, self.profile, plan)
                draft = self.mailer.create_draft(role, self.profile, role.exact_subject)
                cv.job_id = card.id
                draft.job_id = card.id
                if hasattr(self.job_repo, "save_cv"):
                    await self.job_repo.save_cv(cv)
                if hasattr(self.job_repo, "save_draft"):
                    await self.job_repo.save_draft(draft)

            await self.job_repo.save(card)
            existing_jobs.append(card)
            created_cards.append(card)

        return created_cards
