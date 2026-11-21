from __future__ import annotations
import re
from urllib.parse import quote


def generate_wa_apply_link(phone: str, role_title: str, company: str, candidate_name: str) -> str:
    """Generates a wa.me prefilled message link for WhatsApp-based job applications."""
    clean_digits = re.sub(r"[^\d]", "", phone)
    if clean_digits.startswith("03"):
        # Pakistan local format 03XX -> 923XX
        clean_digits = "92" + clean_digits[1:]

    msg = (
        f"Hi, I am applying for the {role_title} position at {company}. "
        f"I am {candidate_name}, a 7th-semester Software Engineering student from Bahria University Karachi. "
        f"Please find my CV attached."
    )
    return f"https://wa.me/{clean_digits}?text={quote(msg)}"
