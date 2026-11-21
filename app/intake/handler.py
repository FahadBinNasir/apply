from __future__ import annotations
import os
from typing import Any, Dict, Optional, Tuple
from app.intake.security import verify_webhook_signature
from app.intake.waha import parse_waha_message
from contracts.models import IncomingMessage
from contracts.protocols import InboxRepo, Queue


class WebhookIntakeHandler:
    """Capture-first intake handler guaranteeing atomic message capture before processing."""

    def __init__(self, inbox_repo: InboxRepo, queue: Queue, webhook_secret: Optional[str] = None):
        self.inbox_repo = inbox_repo
        self.queue = queue
        self.webhook_secret = webhook_secret or os.getenv("WEBHOOK_SECRET", "")
        self.watched_chats = [
            c.strip()
            for c in os.getenv("WATCHED_CHATS", "").split(",")
            if c.strip()
        ]

    async def process_incoming(
        self,
        payload: Dict[str, Any],
        raw_body: bytes,
        signature: Optional[str],
        timestamp: Optional[str],
    ) -> Tuple[bool, str, Optional[str]]:
        # 1. Verify HMAC Signature and timestamp
        is_valid, sig_err = verify_webhook_signature(
            raw_body, self.webhook_secret, signature, timestamp
        )
        if not is_valid:
            return False, f"Auth Error: {sig_err}", None

        # 2. Normalize message
        msg: IncomingMessage = parse_waha_message(payload)
        if not msg.source_id and not msg.raw_text:
            return True, "Ignored: Empty or non-message event", None

        # 3. Allow-list check
        if self.watched_chats and msg.chat_id not in self.watched_chats:
            return True, f"Ignored: Chat {msg.chat_id} not in allow-list", None

        # 4. Deduplication by message hash
        if await self.inbox_repo.is_duplicate_message(msg.message_hash):
            return True, "Ignored: Duplicate message hash", None

        # 5. Capture-first: persist to DB raw inbox BEFORE any AI / rules call
        inbox_item = await self.inbox_repo.save_raw_message(msg)

        # 6. Enqueue for async worker pipeline (groups get higher priority 5, channels priority 1)
        priority = 5 if msg.is_group or msg.is_self_forward else 1
        queue_payload = {
            "inbox_id": inbox_item.id,
            "message": msg.model_dump(mode="json"),
        }
        await self.queue.enqueue(queue_payload, priority=priority)

        return True, "Successfully captured and queued", inbox_item.id
