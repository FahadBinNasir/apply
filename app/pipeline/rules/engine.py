from __future__ import annotations
import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from dateutil import parser as date_parser

from contracts.models import ApplyMethod, ExtractedRole, Profile, Tier, WorkMode
from contracts.protocols import RulesEngine


class ProductionRulesEngine:
    """Pure deterministic decision engine implementing matching rules per Part D3."""

    def evaluate(
        self,
        role: ExtractedRole,
        profile: Profile,
        now_override: Optional[datetime] = None,
    ) -> Tuple[Tier, List[str], float, List[str], List[str]]:
        reasons: List[str] = []
        matches: List[str] = []
        gaps: List[str] = []
        score: float = 50.0

        # Clock resolution
        now = now_override
        if not now:
            env_override = os.getenv("NOW_OVERRIDE")
            if env_override:
                try:
                    now = datetime.fromisoformat(env_override)
                except Exception:
                    pass
        if not now:
            now = datetime.now(timezone.utc)

        # Ensure tz-naive or tz-aware comparison consistency
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)

        # -------------------------------------------------------------
        # 1. SENIORITY & SENIOR EXPERIENCE CHECK (Hard filter)
        # -------------------------------------------------------------
        title_lower = role.title.lower()
        if re.search(r"\b(senior|sr\.?|principal|architect|lead|head\s+of|director|vp)\b", title_lower):
            return Tier.SKIPPED, [f"Senior role / experience requirement in title: '{role.title}'"], 0.0, [], ["Senior role exceeding experience bounds"]
        if re.search(r"\bmanager\b", title_lower) and not re.search(r"\b(management\s+trainee|mto)\b", title_lower):
            return Tier.SKIPPED, [f"Manager role exceeding experience bounds: '{role.title}'"], 0.0, [], ["Manager role"]

        # -------------------------------------------------------------
        # 2. PAY CHECK (Hard filter)
        # -------------------------------------------------------------
        text_all = f"{role.title} {role.field} {role.notes or ''}".lower()
        if re.search(r"\b(unpaid|volunteer|commission[\s-]only|stipend[\s-]only|unpaid[\s-]internship)\b", text_all):
            return Tier.SKIPPED, ["Unpaid or volunteer position"], 0.0, [], ["Unpaid / volunteer"]

        # -------------------------------------------------------------
        # 3. DEADLINE CHECK
        # -------------------------------------------------------------
        if role.deadline:
            try:
                # Handle dates like "2026-11-20", "20 Nov 2026", "2026-11-16"
                dl = date_parser.parse(role.deadline)
                if dl.tzinfo is not None:
                    dl = dl.replace(tzinfo=None)
                if dl < now:
                    return Tier.SKIPPED, [f"Application deadline ({role.deadline}) has expired"], 0.0, [], ["Expired deadline"]
                elif (dl - now).days <= 3:
                    reasons.append(f"Deadline approaching: {role.deadline}")
                    score += 5.0
            except Exception:
                pass

        # -------------------------------------------------------------
        # 4. AVOID FIELDS CHECK (Hard filter)
        # -------------------------------------------------------------
        field_text = f"{role.field} {role.title} {role.notes or ''}".lower()

        # Explicit non-tech engineering and non-tech professions
        if re.search(r"\b(civil|mechanical|chemical|petroleum|electrical)\s+enginee(r|ring)\b", field_text) and not any(k in field_text for k in ["embedded", "firmware", "iot"]):
            return Tier.SKIPPED, ["Field is non-software engineering (civil/mechanical/electrical)"], 0.0, [], ["Non-software engineering"]
        if re.search(r"\b(customer\s+support|customer\s+service|call\s+center|telecalling|telesales|bpo)\b", field_text):
            return Tier.SKIPPED, ["Customer support / call center role"], 0.0, [], ["Customer support"]
        if re.search(r"\b(graphic\s+designer?|graphic\s+design|ui[\s/]ux\s+designer?|designer|figma\s+designer)\b", field_text) and not any(k in field_text for k in ["developer", "frontend", "software"]):
            return Tier.SKIPPED, ["Design / Graphic design role (not software development)"], 0.0, [], ["Design role"]
        if re.search(r"\b(accountant|accounts\s+officer|finance\s+executive|audit\s+associate)\b", field_text):
            return Tier.SKIPPED, ["Finance / Accounting role"], 0.0, [], ["Accounting / Finance"]

        for avoid in profile.matching.avoid_fields:
            avoid_tokens = [tok.strip().lower() for tok in avoid.split(",") if tok.strip()]
            for tok in avoid_tokens:
                pattern = r"\b" + re.escape(tok) + r"(er|ing|s)?\b"
                if re.search(pattern, field_text):
                    return Tier.SKIPPED, [f"Field or role matches avoid list: '{tok}'"], 0.0, [], [f"Avoid category: {avoid}"]

        # -------------------------------------------------------------
        # 5. EDUCATION GATES (Hard filter)
        # -------------------------------------------------------------
        edu_text = f"{role.education or ''} {role.title} {role.notes or ''}".lower()
        if re.search(r"\b(ms|m\.?s|mphil|phd|master'?s?)\s+(required|in\s+cs|in\s+se)\b", edu_text):
            return Tier.SKIPPED, ["Requires MS or higher degree (current student in 7th semester)"], 0.0, [], ["Requires MS degree"]
        if re.search(r"\b(acca|ca\s+inter|icma|mbbs)\b", edu_text):
            return Tier.SKIPPED, ["Requires specialized non-engineering certification (ACCA/CA/MBBS)"], 0.0, [], ["Non-engineering qualification"]

        # -------------------------------------------------------------
        # 4. LOCATION (Hard filter)
        # -------------------------------------------------------------
        loc_str = f"{role.location_text} {role.city}".lower()
        is_remote = role.work_mode == WorkMode.REMOTE or "remote" in loc_str
        is_karachi = "karachi" in loc_str or "shahra-e-faisal" in loc_str

        # Reject explicitly non-Karachi onsite/hybrid
        if not is_remote and ("lahore" in loc_str or "islamabad" in loc_str or "rawalpindi" in loc_str or "faisalabad" in loc_str):
            loc_label = "Lahore" if "lahore" in loc_str else "Islamabad/Rawalpindi"
            return Tier.SKIPPED, [f"{loc_label} onsite/hybrid outside target location (Karachi only)"], 0.0, [], [f"Non-Karachi onsite: {loc_label}"]

        if is_karachi:
            matches.append("Location: Karachi on-site / hybrid")
            score += 15.0
        elif is_remote:
            matches.append("Location: Remote")
            score += 10.0
        else:
            # Unknown location -> STRETCH flag
            gaps.append("Location unknown or unspecified")

        # -------------------------------------------------------------
        # 5. NIGHT SHIFT (Hard filter if profile rejects)
        # -------------------------------------------------------------
        if role.night_shift and not profile.personal.accepts_night_shift:
            return Tier.SKIPPED, ["Requires night shift (profile does not accept night shift)"], 0.0, [], ["Night shift"]

        # -------------------------------------------------------------
        # 6. GENDER REQUIREMENTS
        # -------------------------------------------------------------
        gender_req = role.gender_requirement.lower()
        profile_gender = (profile.personal.gender or "unknown").lower()
        has_gender_warning = False

        if "female" in gender_req:
            if profile_gender == "male":
                return Tier.SKIPPED, ["Position is female-only"], 0.0, [], ["Gender requirement: female only"]
            elif profile_gender != "female":
                has_gender_warning = True
                reasons.append("Flag: Position specifies female-only or female-preferred")
                gaps.append("Gender requirement: female candidates preferred/required")

        # -------------------------------------------------------------
        # 7. EXPERIENCE LEVEL (Soft filter / Stretch / Skip)
        # -------------------------------------------------------------
        is_fresh_friendly = role.fresh_grad_ok or any(
            kw in f"{role.title} {role.notes or ''}".lower()
            for kw in ["fresh", "trainee", "mto", "intern", "junior", "0-1", "0–1", "associate"]
        )

        min_exp = role.experience_min_years or 0.0
        max_exp = role.experience_max_years or min_exp

        if min_exp >= profile.matching.experience.skip_above_years:
            return Tier.SKIPPED, [f"Experience required ({min_exp} yrs) exceeds maximum limit ({profile.matching.experience.skip_above_years} yrs)"], 0.0, [], [f"High experience requirement: {min_exp} yrs"]

        is_stretch_exp = False
        if min_exp > profile.matching.experience.comfortable_max_years:
            is_stretch_exp = True
            reasons.append(f"Experience required ({min_exp}-{max_exp} yrs) is in stretch range")
            gaps.append(f"Experience gap: {min_exp} yrs requested")
            score -= 10.0
        elif is_fresh_friendly:
            matches.append("Fresh graduate / student friendly level")
            score += 15.0

        # -------------------------------------------------------------
        # 8. FIELD MATCHING (Target fields vs Stretch)
        # -------------------------------------------------------------
        is_target_field = False
        is_stretch_field = False
        is_missing_field = False
        role_field_lower = (role.field or "").strip().lower()
        title_lower = role.title.lower()

        CURATED_TECH_KEYWORDS = [
            "software engineer", "software developer", "backend", "full-stack", "full stack",
            "frontend", "web developer", "devops", "cloud engineer", "cloud", "qa engineer",
            "sqa", "test automation", "quality assurance", "ai engineer", "machine learning",
            "data scientist", "data science", "data analyst", "deep learning", "flutter",
            "mobile developer", "ios developer", "android developer", ".net", "dotnet",
            "c# developer", "embedded", "firmware", "iot", "systems engineer", "cyber security"
        ]

        # Check if field is missing or empty
        if not role_field_lower or role_field_lower == "unknown":
            is_missing_field = True
            reasons.append("Field unconfirmed or missing; classified as STRETCH")
            score -= 10.0
        elif any(s in role_field_lower for s in ["infrastructure", "storage", "compute", "networking", "data center"]):
            is_stretch_field = True
            reasons.append("Field is IT infrastructure / storage & compute (stretch category)")
            score += 5.0
        else:
            # Curated tech match: check against specific multi-word tokens or tech keywords
            has_curated_match = any(
                re.search(r"\b" + re.escape(kw) + r"\b", f"{role_field_lower} {title_lower}")
                for kw in CURATED_TECH_KEYWORDS
            )
            if has_curated_match:
                is_target_field = True
                matches.append(f"Target field match: {role.field}")
                score += 20.0
            else:
                for tf in profile.matching.target_fields:
                    tf_clean = tf.lower().strip()
                    if tf_clean in role_field_lower or tf_clean in title_lower:
                        is_target_field = True
                        matches.append(f"Target field match: {tf}")
                        score += 20.0
                        break

            if not is_target_field:
                is_missing_field = True
                reasons.append(f"Field '{role.field}' not in target list; requires manual review")
                score -= 10.0

        # Check skill overlap
        profile_skills_flat = [
            s.lower()
            for category in [
                profile.skills.languages,
                profile.skills.ai_ml,
                profile.skills.web_backend,
                profile.skills.mobile_tools,
                profile.skills.concepts,
            ]
            for s in category
        ]

        matched_skills = []
        for s in role.skills:
            if any(ps in s.lower() or s.lower() in ps for ps in profile_skills_flat):
                matched_skills.append(s)

        if matched_skills:
            matches.append(f"Skills matched: {', '.join(matched_skills[:4])}")
            score += min(20.0, len(matched_skills) * 4.0)

        # Clamp score between 0 and 100
        score = min(100.0, max(0.0, score))

        # -------------------------------------------------------------
        # 9. SPECIAL TIER ASSIGNMENT
        # -------------------------------------------------------------
        # Walk-in check
        if role.apply_method == ApplyMethod.WALKIN or role.walkin:
            reasons.append("Walk-in interview opportunity")
            return Tier.WALKIN, reasons, score, matches, gaps

        # Manual apply check (link / LinkedIn / form / no email)
        if role.apply_method in [ApplyMethod.LINK, ApplyMethod.LINKEDIN, ApplyMethod.FORM] or not role.apply_email:
            if role.apply_method == ApplyMethod.LINKEDIN:
                reasons.append("LinkedIn apply link requires manual browser action")
            elif role.apply_method == ApplyMethod.WHATSAPP:
                reasons.append("WhatsApp direct application")
            else:
                reasons.append("External portal or link-only application")
            return Tier.MANUAL, reasons, score, matches, gaps

        # Stretch conditions: missing/unconfirmed field, stretch field, stretch exp, gender warning, unknown location
        if is_missing_field or is_stretch_field or is_stretch_exp or has_gender_warning or (not is_karachi and not is_remote):
            if is_missing_field and not any("Field" in r for r in reasons):
                reasons.append("Categorized as STRETCH due to unconfirmed field")
            if is_stretch_field:
                reasons.append("Categorized as STRETCH due to infrastructure/support field")
            if is_stretch_exp:
                reasons.append("Categorized as STRETCH due to experience requirement")
            if not is_karachi and not is_remote:
                reasons.append("Categorized as STRETCH due to unknown location")
            return Tier.STRETCH, reasons, score, matches, gaps

        if score >= 70.0:
            reasons.append("Strong technical, location, and experience fit")
            return Tier.STRONG, reasons, score, matches, gaps
        elif score >= 45.0:
            reasons.append("Moderate alignment, classified as STRETCH")
            return Tier.STRETCH, reasons, score, matches, gaps
        else:
            return Tier.SKIPPED, ["Low overall score/relevance"], score, matches, ["Low relevance score"]
