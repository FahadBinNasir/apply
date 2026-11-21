from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from contracts.models import (
    CVArtifact,
    EmailDraft,
    ExtractedRole,
    JobCard,
    Profile,
    SendResult,
    TailorPlan,
)
from contracts.protocols import CalendarExporter, CVBuilder, Mailer


class FakeCVBuilder:
    async def plan_tailoring(
        self,
        role: ExtractedRole,
        profile: Profile,
    ) -> TailorPlan:
        # Pick top 2-3 projects based on role
        project_ids = [p.id for p in profile.projects[:3]]
        return TailorPlan(
            relevant_project_ids=project_ids,
            project_ordering=project_ids,
            skill_emphasis=role.skills[:5] if role.skills else ["Python", "FastAPI"],
            summary_2_3_lines=(
                f"7th semester Software Engineering student at Bahria University applying for {role.title} "
                f"at {role.company}. Strong background in backend systems, APIs, and modern development."
            ),
            honest_notes=["Truthfully states 7th semester status and verified projects only."],
        )

    async def build_cv(
        self,
        role: ExtractedRole,
        profile: Profile,
        plan: TailorPlan,
    ) -> CVArtifact:
        safe_company = "".join(c for c in role.company if c.isalnum() or c in ("-", "_"))
        safe_role = "".join(c for c in role.title if c.isalnum() or c in ("-", "_"))
        pdf_path = f"/app_data/cvs/Fahad_Bin_Nasir_CV_{safe_company}_{safe_role}.pdf"
        return CVArtifact(
            id=f"cv_{safe_company}_{safe_role}",
            job_id=f"job_{safe_company}",
            pdf_path=pdf_path,
            preview_png_paths=[f"{pdf_path}.page1.png"],
            generated_at=datetime.now(timezone.utc),
            passes_verifier=True,
            verifier_notes="All facts verified against profile.seed.yaml",
        )

    def verify_no_fabrication(
        self,
        cv_text: str,
        profile: Profile,
    ) -> Tuple[bool, List[str]]:
        # Verification passes if all listed items are in profile
        return True, []


class FakeMailer:
    def create_draft(
        self,
        role: ExtractedRole,
        profile: Profile,
        exact_subject: Optional[str] = None,
    ) -> EmailDraft:
        subject = exact_subject or f"Application for {role.title} – Fahad Bin Nasir"
        body = (
            f"Dear Hiring Team at {role.company},\n\n"
            f"I am writing to express my strong interest in the {role.title} position. "
            f"As a 7th-semester Software Engineering student at Bahria University Karachi, "
            f"my background in {', '.join(role.skills[:2]) if role.skills else 'software development'} "
            f"and hands-on enterprise project experience align closely with your team's objectives.\n\n"
            f"I have attached my tailored CV for your review and welcome the opportunity to discuss my qualifications.\n\n"
            f"Sincerely,\n{profile.name}\n{profile.phone}\n{profile.email}"
        )
        return EmailDraft(
            id=f"draft_{role.company}",
            job_id=f"job_{role.company}",
            recipient=role.apply_email or "hiring@company.com",
            subject=subject,
            body=body,
            generated_at=datetime.now(timezone.utc),
            is_customized=True,
        )

    async def send_application(
        self,
        job: JobCard,
        draft: EmailDraft,
        cv: CVArtifact,
    ) -> SendResult:
        return SendResult(
            success=True,
            message_id=f"fake_msg_{int(datetime.now(timezone.utc).timestamp())}",
            sent_at=datetime.now(timezone.utc),
        )


class FakeCalendarExporter:
    def export_walkin_ics(self, job: JobCard) -> Optional[str]:
        if not job.role.walkin:
            return None
        return (
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "BEGIN:VEVENT\n"
            f"SUMMARY:Walk-in Interview: {job.role.title} at {job.role.company}\n"
            f"DESCRIPTION:Walk-in interview details: {job.role.walkin.address}\n"
            "END:VEVENT\n"
            "END:VCALENDAR"
        )
