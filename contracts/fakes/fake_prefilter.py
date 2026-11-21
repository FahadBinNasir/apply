from __future__ import annotations
from typing import Optional, Tuple
from contracts.models import IncomingMessage
from contracts.protocols import PreFilter


class FakePreFilter:
    def evaluate(self, message: IncomingMessage) -> Tuple[bool, Optional[str]]:
        text = message.raw_text.strip().lower()
        if not text and not message.media_path:
            return True, "empty_message"

        noise_keywords = [
            "convocation",
            "fundraising",
            "matrimonial",
            "google form",
            "survey",
            "any alumni",
            "alumnus working at",
            "looking for a job",
        ]
        for kw in noise_keywords:
            if kw in text:
                return True, f"matched_noise_keyword_{kw.replace(' ', '_')}"

        return False, None
