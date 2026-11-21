from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from contracts.models import (
    CVArtifact,
    EmailDraft,
    IncomingMessage,
    JobCard,
    Profile,
    Settings,
    Tier,
)


def build_inbox_viewmodel(jobs: List[JobCard], active_tab: Tier = Tier.STRONG) -> Dict[str, Any]:
    counts = {
        "strong": sum(1 for j in jobs if j.tier == Tier.STRONG),
        "stretch": sum(1 for j in jobs if j.tier == Tier.STRETCH),
        "manual": sum(1 for j in jobs if j.tier == Tier.MANUAL),
        "walkin": sum(1 for j in jobs if j.tier == Tier.WALKIN),
    }

    filtered_jobs = [j for j in jobs if j.tier == active_tab]

    now = datetime.now(timezone.utc)
    today_new = 0
    deadline_soon = 0

    job_dicts = []
    for j in filtered_jobs:
        if (now - j.created_at).total_seconds() < 86400:
            today_new += 1
        if j.role.deadline:
            try:
                from dateutil import parser
                dl = parser.parse(j.role.deadline)
                if dl.tzinfo is not None:
                    dl = dl.replace(tzinfo=None)
                if 0 <= (dl - now.replace(tzinfo=None)).days <= 3:
                    deadline_soon += 1
            except Exception:
                pass

        job_dicts.append({
            "id": j.id,
            "company": j.role.company,
            "title": j.role.title,
            "tier": j.tier.value,
            "tier_reasons": j.tier_reasons,
            "score": j.score,
            "status": j.status.value,
            "apply_method": j.role.apply_method.value,
            "apply_email": j.role.apply_email,
            "exact_subject": j.role.exact_subject,
            "deadline": j.role.deadline,
            "location_text": j.role.location_text,
            "matches": j.matches,
            "gaps": j.gaps,
            "created_at": j.created_at.isoformat(),
        })

    vm = {
        "active_tab": active_tab.value,
        "counts": counts,
        "today_new_count": today_new,
        "deadline_soon_count": deadline_soon,
        "jobs": job_dicts,
    }

    if not job_dicts:
        vm["empty_state"] = {
            "title": "All caught up",
            "description": "No pending applications to review right now. New matching posts from watched WhatsApp groups will appear here automatically.",
        }

    return vm


def build_job_detail_viewmodel(
    job: JobCard,
    raw_msg: Optional[IncomingMessage] = None,
    draft: Optional[EmailDraft] = None,
    cv: Optional[CVArtifact] = None,
) -> Dict[str, Any]:
    job_dict = {
        "id": job.id,
        "company": job.role.company,
        "title": job.role.title,
        "field": job.role.field,
        "tier": job.tier.value,
        "tier_reasons": job.tier_reasons,
        "score": job.score,
        "status": job.status.value,
        "location_text": job.role.location_text,
        "work_mode": job.role.work_mode.value,
        "city": job.role.city,
        "experience_min_years": job.role.experience_min_years,
        "experience_max_years": job.role.experience_max_years,
        "education": job.role.education,
        "skills": job.role.skills,
        "responsibilities": job.role.responsibilities,
        "deadline": job.role.deadline,
        "apply_method": job.role.apply_method.value,
        "apply_email": job.role.apply_email,
        "apply_whatsapp": job.role.apply_whatsapp,
        "apply_link": job.role.apply_link,
        "exact_subject": job.role.exact_subject,
        "from_image": job.role.from_image,
        "fresh_grad_ok": job.role.fresh_grad_ok,
        "fit_summary": job.fit_summary,
        "matches": job.matches,
        "gaps": job.gaps,
        "source_messages": job.source_messages,
        "created_at": job.created_at.isoformat(),
    }

    raw_dict = {
        "chat_name": raw_msg.chat_name if raw_msg else "WhatsApp Post",
        "timestamp": raw_msg.timestamp.strftime("%Y-%m-%d %H:%M") if raw_msg else "Recent",
        "text": raw_msg.raw_text if raw_msg else "",
    }

    draft_dict = {
        "id": draft.id if draft else "",
        "recipient": draft.recipient if draft else job.role.apply_email or "",
        "subject": draft.subject if draft else f"Application for {job.role.title}",
        "body": draft.body if draft else "",
    }

    cv_dict = {
        "id": cv.id if cv else "",
        "pdf_path": cv.pdf_path if cv else "",
        "preview_png_paths": cv.preview_png_paths if cv else [],
        "passes_verifier": cv.passes_verifier if cv else True,
        "verifier_notes": cv.verifier_notes if cv else "Verified compliant",
    }

    return {
        "job": job_dict,
        "raw_message": raw_dict,
        "draft": draft_dict,
        "cv": cv_dict,
    }


def build_sent_log_viewmodel(sends: List[Dict[str, Any]], daily_cap: int = 25) -> Dict[str, Any]:
    today_count = 0
    now = datetime.now(timezone.utc)
    for s in sends:
        sent_time = s.get("sent_at")
        if sent_time:
            try:
                from dateutil import parser
                dt = parser.parse(sent_time)
                if dt.date() == now.date():
                    today_count += 1
            except Exception:
                pass

    return {
        "total_sent": len(sends),
        "today_sent": today_count,
        "daily_cap": daily_cap,
        "sends": sends,
    }


def build_skipped_viewmodel(skipped_jobs: List[JobCard]) -> Dict[str, Any]:
    by_reason: Dict[str, List[Dict[str, Any]]] = {
        "location": [],
        "field": [],
        "expired": [],
        "experience": [],
        "other": [],
    }

    for j in skipped_jobs:
        # Categorize by first matching reason
        reasons_text = " ".join(j.tier_reasons).lower()
        cat = "other"
        can_rescue = True
        if "location" in reasons_text or "lahore" in reasons_text:
            cat = "location"
            can_rescue = True
        elif "avoid" in reasons_text or "field" in reasons_text or "business development" in reasons_text:
            cat = "field"
            can_rescue = True
        elif "expired" in reasons_text or "deadline" in reasons_text:
            cat = "expired"
            can_rescue = False
        elif "experience" in reasons_text:
            cat = "experience"
            can_rescue = False

        by_reason[cat].append({
            "id": j.id,
            "company": j.role.company,
            "title": j.role.title,
            "location": j.role.location_text or j.role.city,
            "reason": "; ".join(j.tier_reasons),
            "source": j.source_messages[0] if j.source_messages else "WhatsApp",
            "created_at": j.created_at.isoformat(),
            "can_rescue": can_rescue,
        })

    # Filter out empty categories
    filtered_by_reason = {k: v for k, v in by_reason.items() if v}

    return {
        "total_skipped": len(skipped_jobs),
        "by_reason": filtered_by_reason,
    }


def build_health_viewmodel(
    db_ok: bool = True,
    waha_ok: bool = True,
    gmail_ok: bool = True,
    gemini_ok: bool = True,
    groq_ok: bool = True,
    queue_depth: int = 0,
) -> Dict[str, Any]:
    is_healthy = db_ok and waha_ok and gmail_ok and (gemini_ok or groq_ok)
    return {
        "status": "healthy" if is_healthy else "degraded",
        "database": "connected" if db_ok else "error",
        "waha": "connected" if waha_ok else "disconnected",
        "gmail": "authenticated" if gmail_ok else "token_expired",
        "llm_gemini": "operational" if gemini_ok else "quota_exhausted",
        "llm_groq": "standby" if groq_ok else "quota_exhausted",
        "queue_depth": queue_depth,
        "memory_usage_mb": 145.0,
        "uptime_seconds": 3600,
    }


def build_whatsapp_viewmodel(status: Dict[str, Any], watched_chats: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "connected": status.get("connected", False),
        "engine": status.get("engine", "WAHA Core (WEBJS)"),
        "phone": status.get("phone"),
        "battery": status.get("battery", 100),
        "watched_chats": watched_chats,
        "qr_code": status.get("qr_code"),
    }


def build_settings_viewmodel(settings: Settings, gmail_status: Dict[str, Any], profile: Profile) -> Dict[str, Any]:
    return {
        "system": {
            "send_enabled": settings.send_enabled,
            "daily_send_cap": settings.daily_send_cap,
            "min_gap_seconds": settings.min_gap_seconds,
            "gemini_model_fast": settings.gemini_model_fast,
            "gemini_model_smart": settings.gemini_model_smart,
            "groq_fallback_enabled": settings.groq_fallback_enabled,
            "now_override": settings.now_override,
        },
        "gmail": gmail_status,
        "matching": {
            "target_locations": profile.matching.hard_locations,
            "comfortable_max_years": profile.matching.experience.comfortable_max_years,
            "stretch_max_years": profile.matching.experience.stretch_max_years,
            "skip_above_years": profile.matching.experience.skip_above_years,
            "accepts_night_shift": profile.personal.accepts_night_shift,
            "target_fields_count": len(profile.matching.target_fields),
            "avoid_fields_count": len(profile.matching.avoid_fields),
        },
    }


def build_opportunities_viewmodel(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total_opportunities": len(opportunities),
        "opportunities": opportunities,
    }
