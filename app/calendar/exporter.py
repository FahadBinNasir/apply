from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from contracts.models import JobCard
from contracts.protocols import CalendarExporter


class ProductionCalendarExporter:
    """Generates RFC 5545 .ics calendar files for walk-in interview roles."""

    def export_walkin_ics(self, job: JobCard) -> Optional[str]:
        if not job.role.walkin:
            return None

        w = job.role.walkin
        now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        uid = f"walkin-{job.id}-{uuid.uuid4().hex[:8]}@apply.fahadbinnasir.tech"

        summary = f"Walk-in Interview: {job.role.title} at {job.role.company}"
        location = w.address or job.role.location_text or "Karachi"
        description = (
            f"Walk-in Interview for {job.role.title}\\n"
            f"Company: {job.role.company}\\n"
            f"Date: {w.date or 'TBD'}\\n"
            f"Time: {w.time or 'TBD'}\\n"
            f"Address: {location}\\n"
            f"Notes: Bring updated CV and portfolio."
        )

        return (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Fahad Bin Nasir//WhatsApp Job Agent//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:PUBLISH\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{now_str}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"LOCATION:{location}\r\n"
            f"DESCRIPTION:{description}\r\n"
            "STATUS:CONFIRMED\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
