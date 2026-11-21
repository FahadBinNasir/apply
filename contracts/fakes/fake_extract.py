from __future__ import annotations
from typing import Optional
from contracts.models import (
    ApplyMethod,
    ExtractedRole,
    ExtractionResult,
    IncomingMessage,
    PostType,
    WorkMode,
)
from contracts.protocols import Extractor


class FakeExtractor:
    async def extract(
        self,
        message: IncomingMessage,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> ExtractionResult:
        text = message.raw_text.strip()
        lower = text.lower()

        # F1 fixture check
        if "paysys" in lower or "devops engineer" in lower:
            role = ExtractedRole(
                title="DevOps Engineer",
                company="Paysys Labs",
                field="DevOps / cloud",
                location_text="Karachi (On-site)",
                work_mode=WorkMode.ONSITE,
                city="Karachi",
                experience_min_years=0.0,
                experience_max_years=1.0,
                education="Bachelor's degree in Computer Science, Software Engineering, IT",
                skills=["CI/CD", "Linux", "SQL", "Git", "Scripting", "API testing"],
                responsibilities=["CI/CD pipelines", "Linux administration"],
                deadline=None,
                shift_text=None,
                night_shift=False,
                gender_requirement="any",
                apply_method=ApplyMethod.EMAIL,
                apply_email="hiring@paysyslabs.com",
                exact_subject="DevOps Engineer – Application",
                from_image=False,
                walkin=None,
                fresh_grad_ok=True,
                notes=None,
            )
            return ExtractionResult(is_job=True, post_type=PostType.JOB, roles=[role], confidence=0.98)

        # F2 fixture check
        if "decibel" in lower or "dot net" in lower:
            role = ExtractedRole(
                title="MTO - Dot Net Developer",
                company="Decibel HRMS",
                field=".NET / C# junior",
                location_text="Shahra-e-Faisal, Karachi",
                work_mode=WorkMode.ONSITE,
                city="Karachi",
                experience_min_years=0.0,
                experience_max_years=1.0,
                education="Bachelor's degree in computer science or relevant field",
                skills=["C#", "ASP .NET with webforms", "REST APIs", "SQL"],
                responsibilities=["Develop and maintain web applications", "Build REST APIs"],
                deadline=None,
                shift_text=None,
                night_shift=False,
                gender_requirement="any",
                apply_method=ApplyMethod.EMAIL,
                apply_email="careers@decibel360.com",
                exact_subject="MTO - Dot Net Developer",
                from_image=False,
                walkin=None,
                fresh_grad_ok=True,
                notes="Mentions webforms",
            )
            return ExtractionResult(is_job=True, post_type=PostType.JOB, roles=[role], confidence=0.98)

        # F3 fixture check
        if "ebg" in lower or "storage & compute" in lower:
            role = ExtractedRole(
                title="Storage & Compute Intern",
                company="EBG Partner",
                field="IT infrastructure (stretch)",
                location_text="Karachi, Pakistan",
                work_mode=WorkMode.ONSITE,
                city="Karachi",
                experience_min_years=0.0,
                experience_max_years=0.0,
                education="Fresh graduates",
                skills=["Enterprise Storage", "Compute Technologies", "Data Center"],
                responsibilities=[],
                deadline=None,
                shift_text=None,
                night_shift=False,
                gender_requirement="any",
                apply_method=ApplyMethod.EMAIL,
                apply_email="muhammad.bilal.ahmed30@gmail.com",
                exact_subject=None,
                from_image=False,
                walkin=None,
                fresh_grad_ok=True,
                notes=None,
            )
            return ExtractionResult(is_job=True, post_type=PostType.INTERNSHIP, roles=[role], confidence=0.95)

        # F4 fixture check (Pentaloop Lahore)
        if "pentaloop" in lower or "johar town, lahore" in lower:
            role = ExtractedRole(
                title="ASE - iOS Developer",
                company="Pentaloop",
                field="mobile (Flutter/iOS)",
                location_text="Johar Town, Lahore",
                work_mode=WorkMode.ONSITE,
                city="Lahore",
                experience_min_years=0.0,
                apply_method=ApplyMethod.EMAIL,
                apply_email="hr@pentaloop.com",
                fresh_grad_ok=True,
            )
            return ExtractionResult(is_job=True, post_type=PostType.JOB, roles=[role], confidence=0.95)

        # Generic default extraction
        role = ExtractedRole(
            title="Software Trainee",
            company="Generic Co",
            field="software engineering",
            location_text="Karachi",
            work_mode=WorkMode.ONSITE,
            city="Karachi",
            experience_min_years=0.0,
            experience_max_years=1.0,
            apply_method=ApplyMethod.EMAIL,
            apply_email="jobs@generic.com",
            fresh_grad_ok=True,
        )
        return ExtractionResult(is_job=True, post_type=PostType.JOB, roles=[role], confidence=0.9)
