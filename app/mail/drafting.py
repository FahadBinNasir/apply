from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from contracts.models import EmailDraft, ExtractedRole, Profile


def generate_email_draft(
    role: ExtractedRole,
    profile: Profile,
    exact_subject: Optional[str] = None,
) -> EmailDraft:
    # 1. Subject line determination: verbatim if demanded
    subject = exact_subject or role.exact_subject or f"Application for {role.title} – Fahad Bin Nasir"

    # 2. Key matches to highlight
    match_1 = role.skills[0] if role.skills else "software engineering"
    match_2 = role.skills[1] if len(role.skills) > 1 else "relational database design"

    # 3. Internship consideration sentence if job
    intern_sentence = ""
    if role.fresh_grad_ok:
        intern_sentence = (
            "While this position is full-time, as an enrolled student in my 7th semester, "
            "I would also warmly welcome consideration for an internship, trainee, or project-based capacity. "
        )

    # 4. Construct body (targeted 90-130 words)
    body = (
        f"Dear Hiring Team at {role.company},\n\n"
        f"I am writing to express my strong interest in the {role.title} position. "
        f"Currently in my 7th semester of Bachelor of Software Engineering at Bahria University Karachi, "
        f"I offer hands-on technical experience with {match_1} and {match_2} developed through enterprise academic systems.\n\n"
        f"{intern_sentence}"
        f"I have attached my tailored CV highlighting relevant coursework and practical engineering projects. "
        f"I look forward to discussing how my skills and disciplined work ethic can support {role.company}'s objectives.\n\n"
        f"Sincerely,\n"
        f"{profile.name}\n"
        f"{profile.phone}\n"
        f"{profile.email}\n"
        f"{profile.links.get('linkedin', '')}"
    )

    return EmailDraft(
        id=f"draft_{role.company.lower().replace(' ', '_')[:24]}",
        job_id=f"job_{role.company.lower().replace(' ', '_')[:24]}",
        recipient=role.apply_email or "hiring@company.com",
        subject=subject,
        body=body,
        generated_at=datetime.now(timezone.utc),
        is_customized=True,
    )
