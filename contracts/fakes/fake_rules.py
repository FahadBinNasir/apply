from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Tuple
from contracts.models import ExtractedRole, JobCard, Profile, Tier
from contracts.protocols import Deduper, RulesEngine, Scorer


class FakeRulesEngine:
    def evaluate(
        self,
        role: ExtractedRole,
        profile: Profile,
        now_override: Optional[datetime] = None,
    ) -> Tuple[Tier, List[str], float, List[str], List[str]]:
        reasons: List[str] = []
        matches: List[str] = []
        gaps: List[str] = []

        now = now_override or datetime(2026, 11, 21, 0, 0, 0)

        # 1. Check deadline
        if role.deadline:
            try:
                deadline_dt = datetime.fromisoformat(role.deadline)
                if deadline_dt < now:
                    return Tier.SKIPPED, [f"Deadline {role.deadline} expired"], -50.0, [], ["Expired deadline"]
            except Exception:
                pass

        # 2. Check location
        loc = (role.location_text or role.city).lower()
        if "lahore" in loc or "islamabad" in loc or "rawalpindi" in loc:
            return Tier.SKIPPED, ["Location outside target areas (Lahore/Islamabad onsite)"], -50.0, [], ["Location mismatch"]

        # 3. Check avoid fields
        field_lower = role.field.lower()
        for avoid in profile.matching.avoid_fields:
            if avoid.lower() in field_lower:
                return Tier.SKIPPED, [f"Field '{role.field}' matches avoid list: {avoid}"], -50.0, [], [f"Avoid field {avoid}"]

        # 4. Check night shift
        if role.night_shift and not profile.personal.accepts_night_shift:
            return Tier.SKIPPED, ["Requires night shift"], -50.0, [], ["Night shift"]

        # 5. Check education
        if role.education and "ms" in role.education.lower() and "required" in role.education.lower():
            return Tier.SKIPPED, ["Requires MS degree"], -50.0, [], ["Education level required: MS"]

        # 6. Check stretch conditions
        if "infrastructure" in field_lower or "storage" in field_lower:
            return Tier.STRETCH, ["IT infrastructure/storage is a stretch field"], 10.0, ["IT infrastructure"], []

        # 7. Check experience
        if role.experience_min_years and role.experience_min_years > profile.matching.experience.stretch_max_years:
            return Tier.SKIPPED, [f"Experience {role.experience_min_years} exceeds bounds"], -50.0, [], ["High experience requirement"]
        elif role.experience_min_years and role.experience_min_years > profile.matching.experience.comfortable_max_years:
            return Tier.STRETCH, [f"Experience {role.experience_min_years} is stretch"], 5.0, [], ["Stretch experience"]

        matches.append(f"Target field match: {role.field}")
        matches.append("Location Karachi/Remote match")
        return Tier.STRONG, ["Strong match on target field and location"], 25.0, matches, gaps


class FakeScorer:
    def score(
        self,
        role: ExtractedRole,
        rules_tier: Tier,
        rules_reasons: List[str],
        base_score: float,
        profile: Profile,
    ) -> Tuple[Tier, float, str]:
        if rules_tier == Tier.SKIPPED:
            return Tier.SKIPPED, 0.0, "Skipped by hard rules filter: " + "; ".join(rules_reasons)
        if rules_tier == Tier.STRETCH:
            return Tier.STRETCH, 60.0, "Stretch opportunity: " + "; ".join(rules_reasons)

        final_score = min(100.0, max(0.0, base_score + 75.0))
        tier = Tier.STRONG if final_score >= 70.0 else Tier.STRETCH
        return tier, final_score, f"Fit score: {final_score:.1f}. High alignment with skills and location."


class FakeDeduper:
    def find_duplicate(
        self,
        role: ExtractedRole,
        existing_jobs: List[JobCard],
    ) -> Optional[str]:
        target_company = role.company.lower().strip()
        target_title = role.title.lower().strip()
        for job in existing_jobs:
            if (
                job.role.company.lower().strip() == target_company
                and job.role.title.lower().strip() == target_title
            ):
                return job.id
        return None
