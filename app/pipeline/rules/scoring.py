from __future__ import annotations
from typing import List, Tuple
from contracts.models import ExtractedRole, Profile, Tier
from contracts.protocols import Scorer


class ProductionScorer:
    """Combines rule evaluation flags and base scores into final Tier, numeric score, and summary."""

    def score(
        self,
        role: ExtractedRole,
        rules_tier: Tier,
        rules_reasons: List[str],
        base_score: float,
        profile: Profile,
    ) -> Tuple[Tier, float, str]:
        # Hard skips remain SKIPPED
        if rules_tier == Tier.SKIPPED:
            summary = "Skipped by rules filter: " + "; ".join(rules_reasons)
            return Tier.SKIPPED, 0.0, summary

        # Special non-email tiers remain unchanged
        if rules_tier in [Tier.MANUAL, Tier.WALKIN, Tier.OPPORTUNITY]:
            summary = f"{rules_tier.value} tier: " + "; ".join(rules_reasons)
            return rules_tier, base_score, summary

        # Clamp score between 0 and 100
        final_score = min(100.0, max(0.0, base_score))

        if rules_tier == Tier.STRETCH:
            summary = f"Stretch fit ({final_score:.0f}/100): " + "; ".join(rules_reasons)
            return Tier.STRETCH, final_score, summary

        # If rules engine determined STRONG
        if final_score >= 70.0:
            summary = f"Strong fit ({final_score:.0f}/100): " + "; ".join(rules_reasons)
            return Tier.STRONG, final_score, summary
        else:
            summary = f"Moderate fit ({final_score:.0f}/100): " + "; ".join(rules_reasons)
            return Tier.STRETCH, final_score, summary
