from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import ValidationError

from contracts.models import (
    ApplyMethod,
    ExtractedRole,
    ExtractionResult,
    IncomingMessage,
    PostType,
    WalkinDetails,
    WorkMode,
)
from contracts.protocols import Extractor, LLMProvider

PROMPT_FILE = Path(__file__).parent.parent / "llm" / "prompts" / "v1_extract.txt"


def _dict_to_role(d: Dict[str, Any], from_image_flag: bool = False) -> ExtractedRole:
    walkin = None
    if d.get("walkin"):
        w = d["walkin"]
        walkin = WalkinDetails(date=w.get("date"), time=w.get("time"), address=w.get("address"))

    # Map apply_method
    method_str = (d.get("apply_method") or "unknown").lower()
    method = ApplyMethod.UNKNOWN
    for m in ApplyMethod:
        if m.value == method_str:
            method = m
            break

    # Map work_mode
    mode_str = (d.get("work_mode") or "unknown").lower()
    mode = WorkMode.UNKNOWN
    for wm in WorkMode:
        if wm.value == mode_str:
            mode = wm
            break

    return ExtractedRole(
        title=d.get("title") or "Unknown Role",
        company=d.get("company") or "Unknown Company",
        field=d.get("field") or "",
        location_text=d.get("location_text") or "",
        work_mode=mode,
        city=d.get("city") or "",
        experience_min_years=d.get("experience_min_years", 0.0),
        experience_max_years=d.get("experience_max_years"),
        education=d.get("education"),
        skills=d.get("skills") or [],
        responsibilities=d.get("responsibilities") or [],
        deadline=d.get("deadline"),
        shift_text=d.get("shift_text"),
        night_shift=bool(d.get("night_shift", False)),
        gender_requirement=d.get("gender_requirement") or "any",
        apply_method=method,
        apply_email=d.get("apply_email"),
        apply_whatsapp=d.get("apply_whatsapp"),
        apply_link=d.get("apply_link"),
        exact_subject=d.get("exact_subject"),
        from_image=from_image_flag or bool(d.get("from_image", False)),
        walkin=walkin,
        fresh_grad_ok=bool(d.get("fresh_grad_ok", False)),
        notes=d.get("notes"),
    )


class ProductionExtractor:
    """Extracts structured roles using LLM Provider and validates schemas."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self._prompt_template = ""
        if PROMPT_FILE.exists():
            self._prompt_template = PROMPT_FILE.read_text(encoding="utf-8")

    async def extract(
        self,
        message: IncomingMessage,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> ExtractionResult:
        prompt = (
            f"{self._prompt_template}\n\n"
            f"MESSAGE CONTENT TO EXTRACT:\n"
            f"Source Chat: {message.chat_name}\n"
            f"Raw Text:\n{message.raw_text}\n"
        )

        # Call LLM with retry once on invalid schema
        for attempt in range(2):
            raw_json = await self.llm.generate_json(
                schema={},
                prompt=prompt,
                image_bytes=image_bytes,
                mime_type=mime_type,
            )

            try:
                is_job = bool(raw_json.get("is_job", False))
                post_type_str = (raw_json.get("post_type") or "job").lower()
                post_type = PostType.JOB
                for pt in PostType:
                    if pt.value == post_type_str:
                        post_type = pt
                        break

                roles_data = raw_json.get("roles", [])
                roles = [_dict_to_role(r, from_image_flag=bool(image_bytes)) for r in roles_data]

                return ExtractionResult(
                    is_job=is_job,
                    post_type=post_type,
                    roles=roles,
                    confidence=float(raw_json.get("confidence", 0.9)),
                )
            except Exception as e:
                if attempt == 1:
                    # Final attempt fallback
                    return ExtractionResult(
                        is_job=False,
                        post_type=PostType.OTHER,
                        roles=[],
                        confidence=0.0,
                    )
                prompt += f"\n\nERROR ON PREVIOUS ATTEMPT: {e}. Output strictly valid JSON."

        return ExtractionResult(is_job=False, roles=[])
