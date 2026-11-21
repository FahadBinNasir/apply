from __future__ import annotations
import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.db.crypto import TokenEncryption
from app.mail.drafting import generate_email_draft
from contracts.models import CVArtifact, EmailDraft, ExtractedRole, JobCard, Profile, SendResult
from contracts.protocols import Mailer


class ProductionMailer:
    """Safely dispatches job application emails via Gmail API or SMTP with dry-run protection."""

    def __init__(self, crypto: Optional[TokenEncryption] = None):
        self.crypto = crypto or TokenEncryption()
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

        # 1. Daily cap check
        if self._sent_today >= self.daily_cap:
            return SendResult(
                success=False,
                error=f"Daily send cap of {self.daily_cap} applications reached. Sending paused until next day.",
            )

        # 2. Min gap rate limit check
        if self._last_sent_time:
            elapsed = (now - self._last_sent_time).total_seconds()
            if elapsed < self.min_gap_seconds:
                return SendResult(
                    success=False,
                    error=f"Rate limit: Must wait {self.min_gap_seconds - int(elapsed)}s between sends.",
                )

        # 3. Dry-run mode check
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

        # 4. Live sending (Gmail API or SMTP)
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
