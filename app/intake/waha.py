from __future__ import annotations
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from contracts.models import IncomingMessage
from contracts.protocols import IntakeSource

MEDIA_DIR = Path("app_data/media")


def parse_waha_message(payload: Dict[str, Any]) -> IncomingMessage:
    """Normalizes raw WAHA message event payload into IncomingMessage."""
    data = payload.get("payload") or payload

    source_id = str(data.get("id") or "")
    chat_id = str(data.get("from") or "")
    raw_text = str(data.get("body") or "")
    sender = str(data.get("_data", {}).get("notifyName") or data.get("sender", {}).get("pushname") or "")

    # Group and channel detection
    is_group = chat_id.endswith("@g.us")
    is_channel = chat_id.endswith("@newsletter")
    is_self_forward = chat_id.endswith("@c.us") and ("myself" in chat_id.lower() or "me" in chat_id.lower())

    # Media handling
    media_path = None
    media_mime = None
    if data.get("hasMedia") and data.get("media"):
        m = data["media"]
        media_mime = m.get("mimetype")
        if m.get("url"):
            media_path = m.get("url")

    # Content hash for deduplication
    content_str = f"{chat_id}:{raw_text}:{media_mime or ''}"
    message_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    return IncomingMessage(
        source_id=source_id,
        chat_id=chat_id,
        chat_name=chat_id.split("@")[0],
        sender=sender,
        timestamp=datetime.now(timezone.utc),
        raw_text=raw_text,
        media_path=media_path,
        media_mime=media_mime,
        is_group=is_group,
        is_channel=is_channel,
        is_self_forward=is_self_forward,
        message_hash=message_hash,
    )


class WAHAIntakeAdapter:
    """Interacts with WAHA Core container in listen-only mode."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("WAHA_BASE_URL", "http://whatsapp:3000")
        self.api_key = api_key or os.getenv("WAHA_API_KEY", "")
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    async def poll_or_receive(self) -> List[IncomingMessage]:
        # Listen-only mode receives messages via webhooks
        return []

    def get_status(self) -> Dict[str, Any]:
        try:
            headers = {"X-Api-Key": self.api_key} if self.api_key else {}
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/sessions/default", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "STOPPED")
                    return {
                        "connected": status == "WORKING",
                        "engine": "WAHA Core (WEBJS)",
                        "status": status,
                        "phone": data.get("me", {}).get("id"),
                    }
        except Exception as e:
            return {
                "connected": False,
                "engine": "WAHA Core (WEBJS)",
                "error": str(e),
                "status": "UNREACHABLE",
            }
        return {"connected": False, "status": "DISCONNECTED"}

    def get_qr(self) -> Optional[str]:
        try:
            headers = {"X-Api-Key": self.api_key} if self.api_key else {}
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/default/auth/qr", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("qr")
        except Exception:
            pass
        return None
