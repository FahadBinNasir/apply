from __future__ import annotations
import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from app.db.crypto import TokenEncryption
from app.mail.drafting import generate_email_draft
from contracts.models import CVArtifact, EmailDraft, ExtractedRole, JobCard, Profile, SendResult
from contracts.protocols import Mailer

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PLACEHOLDER_DOMAINS = {"example.com", "placeholder.com", "test.com", "domain.com", "yopmail.com"}


def validate_recipient_and_subject(recipient: str, subject: str) -> Optional[str]:
    """Validates email recipient format, anti-injection, and non-placeholder rules."""
    if not recipient or not recipient.strip():
        return "Recipient email address is missing."
    rec = recipient.strip()
    if "\r" in rec or "\n" in rec or "," in rec or ";" in rec:
        return "Recipient email contains invalid characters or line breaks (header injection protection)."
    if not EMAIL_REGEX.match(rec):
        return f"Invalid email format for recipient: {rec}"
    domain = rec.split("@")[-1].lower()
    if domain in PLACEHOLDER_DOMAINS or "placeholder" in rec.lower() or "todo" in rec.lower():
        return f"Recipient email cannot be a placeholder or example address: {rec}"

    if not subject or not subject.strip():
        return "Email subject cannot be empty."
    if "\r" in subject or "\n" in subject:
        return "Email subject contains newline characters (header injection protection)."
    return None


class ProductionMailer:
    """Safely dispatches job application emails via Gmail API or SMTP with dry-run protection."""

    def __init__(self, crypto: Optional[TokenEncryption] = None, job_repo: Optional[Any] = None):
        self.crypto = crypto or TokenEncryption()
        self.job_repo = job_repo
        self.send_enabled = os.getenv("SEND_ENABLED", "false").lower() == "true"
        self.daily_cap = int(os.getenv("DAILY_SEND_CAP", "25"))
        self.min_gap_seconds = int(os.getenv("MIN_GAP_SECONDS", "60"))
        self.mail_backend = os.getenv("MAIL_BACKEND", "gmail_api")
        self._sent_today: int = 0
        self._last_sent_time: Optional[datetime] = None

    def create_draft(
        self,
        role: ExtractedRole,
        profile: Profile,
        exact_subject: Optional[str] = None,
    ) -> EmailDraft:
        return generate_email_draft(role, profile, exact_subject)

    async def send_application(
        self,
        job: JobCard,
        draft: EmailDraft,
        cv: CVArtifact,
    ) -> SendResult:
        now = datetime.now(timezone.utc)

        # 1. Validate Recipient and Subject (Anti-injection & Placeholder guard)
        validation_err = validate_recipient_and_subject(draft.recipient, draft.subject)
        if validation_err:
            return SendResult(success=False, error=validation_err)

        # 2. Never send without CV file on disk (P0 requirement)
        if not cv.pdf_path or not Path(cv.pdf_path).exists():
            return SendResult(
                success=False,
                error=f"CV PDF file missing on disk ({cv.pdf_path}). Applications cannot be dispatched without a verified CV.",
            )

        # 3. 14-day duplicate application guard
        if self.job_repo and hasattr(self.job_repo, "check_recent_send"):
            try:
                is_recent = await self.job_repo.check_recent_send(job.role.company, draft.recipient, days=14)
                if is_recent:
                    return SendResult(
                        success=False,
                        error=f"14-day duplicate guard: An application was already dispatched to {job.role.company} / {draft.recipient} within the last 14 days.",
                    )
            except Exception as e:
                # Log and continue if check fails
                pass

        # 4. Daily cap check
        if self._sent_today >= self.daily_cap:
            return SendResult(
                success=False,
                error=f"Daily send cap of {self.daily_cap} applications reached. Sending paused until next day.",
            )

        # 5. Min gap rate limit check
        if self._last_sent_time:
            elapsed = (now - self._last_sent_time).total_seconds()
            if elapsed < self.min_gap_seconds:
                return SendResult(
                    success=False,
                    error=f"Rate limit: Must wait {self.min_gap_seconds - int(elapsed)}s between sends.",
                )

        # 6. Dry-run mode check
        if not self.send_enabled:
            # Simulate dispatch
            self._sent_today += 1
            self._last_sent_time = now
            simulated_id = f"dry_run_{int(now.timestamp())}"
            return SendResult(
                success=True,
                message_id=simulated_id,
                sent_at=now,
            )

        # 7. Live sending (Gmail API or SMTP)
        try:
            if self.mail_backend == "smtp":
                return await self._send_via_smtp(draft, cv)
            else:
                return await self._send_via_gmail_api(draft, cv)
        except Exception as e:
            return SendResult(
                success=False,
                error=f"Transmission error: {e}",
            )

    async def _send_via_smtp(self, draft: EmailDraft, cv: CVArtifact) -> SendResult:
        import smtplib
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = draft.recipient
        msg["Subject"] = draft.subject
        msg.attach(MIMEText(draft.body, "plain", "utf-8"))

        # Attach CV PDF if exists
        pdf_path = Path(cv.pdf_path)
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
                msg.attach(attach)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        now = datetime.now(timezone.utc)
        self._sent_today += 1
        self._last_sent_time = now
        return SendResult(
            success=True,
            message_id=f"smtp_{int(now.timestamp())}",
            sent_at=now,
        )

    async def _send_via_gmail_api(self, draft: EmailDraft, cv: CVArtifact) -> SendResult:
        # Construct RFC 2822 message and send via Google API client
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        refresh_enc = os.getenv("GMAIL_REFRESH_TOKEN_ENC", "")
        refresh_token = self.crypto.decrypt(refresh_enc) if refresh_enc else ""

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )

        service = build("gmail", "v1", credentials=creds)

        msg = MIMEMultipart()
        msg["To"] = draft.recipient
        msg["Subject"] = draft.subject
        msg.attach(MIMEText(draft.body, "plain", "utf-8"))

        pdf_path = Path(cv.pdf_path)
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
                msg.attach(attach)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()

        now = datetime.now(timezone.utc)
        self._sent_today += 1
        self._last_sent_time = now
        return SendResult(
            success=True,
            message_id=sent.get("id"),
            sent_at=now,
        )
