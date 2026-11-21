from __future__ import annotations
import re
from typing import Optional, Tuple
from contracts.models import IncomingMessage
from contracts.protocols import PreFilter


class ProductionPreFilter:
    """Zero-LLM pre-filter to drop noise and save API quota."""

    def evaluate(self, message: IncomingMessage) -> Tuple[bool, Optional[str]]:
        text = message.raw_text.strip()
        has_media = bool(message.media_path)

        # 1. Empty messages
        if not text and not has_media:
            return True, "empty_message"

        lower = text.lower()

        # 2. Short greetings or acknowledgements
        if len(text) < 15 and not has_media:
            if any(g in lower for g in ["hi", "hello", "salam", "aoa", "thank you", "thanks", "ok", "okay"]):
                return True, "greeting_or_acknowledgment"

        # 3. Convocation / University events
        if any(k in lower for k in ["convocation", "gala", "sports week", "orientation ceremony", "reunion"]):
            return True, "university_event_announcement"

        # 4. Fundraising / Donations
        if any(k in lower for k in ["fundraising", "donation", "donate", "legacy medal", "charity drive"]):
            return True, "fundraising_or_charity"

        # 5. Surveys / Research forms
        if any(k in lower for k in ["google form", "forms.gle", "fill out this survey", "research questionnaire", "master's thesis survey", "ms thesis survey"]):
            return True, "academic_survey_or_form"

        # 6. Matrimonial / Personal ads
        if any(k in lower for k in ["matrimonial", "rishta", "proposal", "bride", "groom"]):
            return True, "matrimonial_advertisement"

        # 7. Alumni lookups / Someone else's job hunting post
        if re.search(r"\b(is there any alumnus|any alumni in|any alumni at|looking for a job|please refer me|anyone working at|i am looking for job)\b", lower):
            return True, "alumni_query_or_personal_job_hunt"

        return False, None
