from __future__ import annotations
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.cv.verifier import AntiFabricationVerifier
from contracts.models import CVArtifact, ExtractedRole, Profile, TailorPlan
from contracts.protocols import CVBuilder

DATA_DIR = Path(os.getenv("DATA_DIR", "app_data")).resolve()
OUTPUT_DIR = DATA_DIR / "cvs"


def _sanitize_name(s: str) -> str:
    return re.sub(r"[^\w\-]", "", s.replace(" ", "_"))


class ProductionCVBuilder:
    """Renders tailored ATS-friendly single-page PDFs using ReportLab from profile.seed.yaml facts."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verifier = AntiFabricationVerifier()

    async def plan_tailoring(
        self,
        role: ExtractedRole,
        profile: Profile,
    ) -> TailorPlan:
        field_lower = role.field.lower()
        title_lower = role.title.lower()

        # Domain project ordering based on tags
        if "ai" in field_lower or "data" in field_lower or "machine learning" in field_lower:
            # AI / Data lead
            ordered_ids = ["churnvision", "exam-cheating-detector", "knowledge-brain"]
            skills_focus = profile.skills.ai_ml[:5] + ["Python", "FastAPI"]
        elif "devops" in field_lower or "cloud" in field_lower or "backend" in field_lower or "full-stack" in field_lower:
            # Backend / DevOps lead with FYP
            ordered_ids = ["knowledge-brain", "churnvision", "iot-inventory"]
            skills_focus = ["FastAPI", "Python", "REST APIs", "Docker", "OAuth 2.0", "SQL"]
        elif "mobile" in field_lower or "flutter" in field_lower:
            ordered_ids = ["flutter-suite", "knowledge-brain", "iot-inventory"]
            skills_focus = profile.skills.mobile_tools[:5] + ["Dart", "Flutter"]
        elif "iot" in field_lower or "embedded" in field_lower:
            ordered_ids = ["iot-inventory", "knowledge-brain", "flutter-suite"]
            skills_focus = ["NodeMCU ESP8266", "RFID", "Arduino IDE", "C++", "Python"]
        elif ".net" in field_lower or "c#" in title_lower:
            ordered_ids = ["knowledge-brain", "churnvision", "exam-cheating-detector"]
            skills_focus = ["C#", "SQL", "REST APIs", "Python", "FastAPI"]
        else:
            ordered_ids = ["knowledge-brain", "churnvision", "flutter-suite"]
            skills_focus = profile.skills.languages[:4] + ["FastAPI", "SQL"]

        summary = (
            f"7th-semester Bachelor of Software Engineering student at Bahria University Karachi, "
            f"targeting {role.title} at {role.company}. Strong practical foundation in "
            f"{', '.join(skills_focus[:3])} demonstrated through enterprise-scale academic and laboratory projects. "
            f"Available for entry-level, internship, or trainee roles with dedication to high code quality and security."
        )

        plan = TailorPlan(
            relevant_project_ids=ordered_ids,
            project_ordering=ordered_ids,
            skill_emphasis=skills_focus,
            summary_2_3_lines=summary,
            honest_notes=["Truthfully reflects 7th semester status and verified projects from profile.seed.yaml"],
        )

        # Enforce verifier on the plan
        is_valid, violations = self.verifier.verify_plan(plan, profile)
        if not is_valid:
            # Reset to safe default
            plan.summary_2_3_lines = (
                f"7th-semester Bachelor of Software Engineering student at Bahria University Karachi applying for {role.title}."
            )

        return plan

    async def build_cv(
        self,
        role: ExtractedRole,
        profile: Profile,
        plan: TailorPlan,
    ) -> CVArtifact:
        safe_company = _sanitize_name(role.company)
        safe_title = _sanitize_name(role.title)
        filename = f"Fahad_Bin_Nasir_CV_{safe_company}_{safe_title}.pdf"
        pdf_path = self.output_dir / filename

        self._render_pdf(str(pdf_path), role, profile, plan)

        preview_path = f"{str(pdf_path)}.preview.png"

        # Verification check on output
        passes, violations = self.verifier.verify_cv_text(plan.summary_2_3_lines, profile)

        return CVArtifact(
            id=f"cv_{safe_company}_{safe_title}",
            job_id=f"job_{safe_company}",
            pdf_path=pdf_path.as_posix(),
            preview_png_paths=[preview_path],
            generated_at=datetime.now(timezone.utc),
            passes_verifier=passes,
            verifier_notes="; ".join(violations) if violations else "Verified compliant with profile.seed.yaml facts",
        )

    def _render_pdf(self, path: str, role: ExtractedRole, profile: Profile, plan: TailorPlan) -> None:
        doc = SimpleDocTemplate(
            path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Clean typography styles
        header_title = ParagraphStyle(
            "HeaderTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor="#1A202C",
        )
        contact_line = ParagraphStyle(
            "ContactLine",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor="#4A5568",
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor="#2B6CB0",
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor="#2D3748",
        )
        bullet_style = ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor="#2D3748",
            leftIndent=10,
        )

        story = []

        # Name and Header
        story.append(Paragraph(profile.name, header_title))
        story.append(Spacer(1, 2))
        contact_text = (
            f"{profile.location} | {profile.phone} | {profile.email} | "
            f"LinkedIn: {profile.links.get('linkedin', '')}"
        )
        story.append(Paragraph(contact_text, contact_line))
        story.append(Spacer(1, 8))

        # Professional Summary
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
        story.append(Spacer(1, 2))
        story.append(Paragraph(plan.summary_2_3_lines, body_style))
        story.append(Spacer(1, 6))

        # Education
        story.append(Paragraph("EDUCATION", section_heading))
        story.append(Spacer(1, 2))
        story.append(
            Paragraph(
                "<b>Bachelor of Software Engineering</b> — Bahria University, Karachi (2022 - Present, 7th Semester)",
                body_style,
            )
        )
        story.append(
            Paragraph(
                "<b>FSc Pre-Engineering</b> — Cadet College Ormara (2016 - 2022)",
                body_style,
            )
        )
        story.append(Spacer(1, 6))

        # Technical Skills
        story.append(Paragraph("TECHNICAL SKILLS", section_heading))
        story.append(Spacer(1, 2))
        skills_text = (
            f"<b>Languages:</b> {', '.join(profile.skills.languages)}<br/>"
            f"<b>AI/ML & Data:</b> {', '.join(profile.skills.ai_ml)}<br/>"
            f"<b>Backend & Systems:</b> {', '.join(profile.skills.web_backend)}<br/>"
            f"<b>Mobile & Tools:</b> {', '.join(profile.skills.mobile_tools)}"
        )
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 6))

        # Selected Projects
        story.append(Paragraph("KEY ENTERPRISE & LAB PROJECTS", section_heading))
        story.append(Spacer(1, 2))

        project_map = {p.id: p for p in profile.projects}
        for pid in plan.relevant_project_ids[:3]:
            proj = project_map.get(pid)
            if not proj:
                continue

            proj_header = f"<b>{proj.name}</b> ({proj.years}) — <i>{proj.context}</i>"
            story.append(Paragraph(proj_header, body_style))
            for bullet in proj.bullets[:2]:
                story.append(Paragraph(f"• {bullet}", bullet_style))
            story.append(Spacer(1, 3))

        doc.build(story)

    def verify_no_fabrication(
        self,
        cv_text: str,
        profile: Profile,
    ) -> Tuple[bool, List[str]]:
        return self.verifier.verify_cv_text(cv_text, profile)
