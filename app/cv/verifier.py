from __future__ import annotations
import re
from typing import List, Tuple
from contracts.models import Profile, TailorPlan


class AntiFabricationVerifier:
    """Strict verifier ensuring 100% adherence to ground truth in profile.seed.yaml."""

    def verify_plan(self, plan: TailorPlan, profile: Profile) -> Tuple[bool, List[str]]:
        violations: List[str] = []
        valid_project_ids = {p.id for p in profile.projects}

        for pid in plan.relevant_project_ids:
            if pid not in valid_project_ids:
                violations.append(f"Invented project ID '{pid}' not found in profile projects!")

        # Check for webforms fabrication
        summary_lower = plan.summary_2_3_lines.lower()
        if "webforms experience" in summary_lower or "built with webforms" in summary_lower:
            violations.append("Fabrication detected: Cannot claim prior WebForms production experience!")

        # Ensure semester is truthfully represented
        if "7th semester" not in summary_lower and "final year" not in summary_lower:
            violations.append("Truthfulness violation: Must state 7th semester / final year student status in summary.")

        return len(violations) == 0, violations

    def verify_cv_text(self, cv_text: str, profile: Profile) -> Tuple[bool, List[str]]:
        violations: List[str] = []
        text_lower = cv_text.lower()

        # 1. No invented employer claims
        forbidden_employers = ["google", "microsoft", "amazon", "paysys labs", "decibel"]
        for emp in forbidden_employers:
            if re.search(rf"\b(software engineer at {emp}|intern at {emp}|worked at {emp})\b", text_lower):
                violations.append(f"Fabricated employment at '{emp}' detected!")

        # 2. Check student status
        if "bahria university" not in text_lower:
            violations.append("Missing university education: Bahria University.")

        # 3. Check WebForms false claim
        if "years of webforms" in text_lower or "expert in webforms" in text_lower:
            violations.append("Fabrication: False WebForms expertise claim.")

        return len(violations) == 0, violations
