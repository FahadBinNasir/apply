from __future__ import annotations
import re
from typing import List, Optional
from rapidfuzz import fuzz

from contracts.models import ExtractedRole, JobCard
from contracts.protocols import Deduper


def _clean_str(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


class ProductionDeduper:
    """Fuzzy deduplication across groups and channels using rapidfuzz."""

    def __init__(self, company_threshold: float = 85.0, title_threshold: float = 80.0):
        self.company_threshold = company_threshold
        self.title_threshold = title_threshold

    def find_duplicate(
        self,
        role: ExtractedRole,
        existing_jobs: List[JobCard],
    ) -> Optional[str]:
        norm_company = _clean_str(role.company)
        norm_title = _clean_str(role.title)

        for job in existing_jobs:
            # 1. Exact match on apply email if present
            if role.apply_email and job.role.apply_email:
                if role.apply_email.lower().strip() == job.role.apply_email.lower().strip():
                    # If emails match, check if title is reasonably similar
                    t_score = fuzz.token_set_ratio(norm_title, _clean_str(job.role.title))
                    if t_score >= 65.0:
                        return job.id

            # 2. Fuzzy match on company + title
            job_company = _clean_str(job.role.company)
            c_score = fuzz.token_set_ratio(norm_company, job_company)
            if c_score >= self.company_threshold:
                t_score = fuzz.token_set_ratio(norm_title, _clean_str(job.role.title))
                if t_score >= self.title_threshold:
                    return job.id

        return None
