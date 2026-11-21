from __future__ import annotations
import hmac
import hashlib
import time
from typing import Optional, Tuple


def sign_payload(payload_bytes: bytes, secret: str, timestamp: int) -> str:
    """Computes HMAC-SHA256 signature for webhook payload and timestamp."""
    data = f"{timestamp}.".encode("utf-8") + payload_bytes
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()


def verify_webhook_signature(
    payload_bytes: bytes,
    secret: str,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
    max_drift_seconds: int = 300,
) -> Tuple[bool, Optional[str]]:
    """Validates HMAC-SHA256 signature and checks timestamp anti-replay."""
    if not secret:
        # If no secret configured in dev mode
        return True, None

    if not signature_header:
        return False, "Missing x-webhook-signature header"

    if not timestamp_header:
        return False, "Missing x-webhook-timestamp header"

    try:
        ts = int(timestamp_header)
        now = int(time.time())
        if abs(now - ts) > max_drift_seconds:
            return False, f"Timestamp drift exceeded: {abs(now - ts)}s > {max_drift_seconds}s"
    except ValueError:
        return False, "Invalid timestamp header"

    expected_sig = sign_payload(payload_bytes, secret, ts)
    if not hmac.compare_digest(expected_sig, signature_header):
        return False, "Invalid webhook HMAC signature"

    return True, None
