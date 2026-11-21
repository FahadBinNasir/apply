from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from contracts.models import JobCard, Status
from contracts.protocols import JobRepo

logger = logging.getLogger(__name__)


def setup_scheduler(job_repo: JobRepo, pipeline_engine=None) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def sweep_channels_job():
        logger.info("[SCHEDULER] Running 2-hour channel & Pintern sweep...")
        # Channels sweep check

    async def daily_expiry_and_cleanup_job():
        logger.info("[SCHEDULER] Running daily deadline expiry check & temp file cleanup...")
        now = datetime.now(timezone.utc)
        jobs = await job_repo.list_cards(limit=500)
        for j in jobs:
            if j.role.deadline and j.status not in [Status.SENT, Status.EXPIRED, Status.REJECTED]:
                try:
                    from dateutil import parser
                    dl = parser.parse(j.role.deadline)
                    if dl.tzinfo is not None:
                        dl = dl.replace(tzinfo=None)
                    if dl < now.replace(tzinfo=None):
                        await job_repo.update_status(j.id, Status.EXPIRED.value)
                        logger.info("Marked job %s as EXPIRED", j.id)
                except Exception:
                    pass

        # Cleanup tmp files older than 3 days
        tmp_dir = Path(".agents/tmp")
        if tmp_dir.exists():
            for f in tmp_dir.glob("*"):
                try:
                    if f.is_file() and (now.timestamp() - f.stat().st_mtime) > 259200:
                        f.unlink()
                except Exception:
                    pass

    scheduler.add_job(sweep_channels_job, "interval", hours=2, id="channels_sweep")
    scheduler.add_job(daily_expiry_and_cleanup_job, "cron", hour=0, minute=0, id="daily_cleanup")

    return scheduler
