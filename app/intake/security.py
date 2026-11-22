from __future__ import annotations
import hmac
import hashlib
import os
import time
from typing import Optional, Tuple


def sign_payload(payload_bytes: bytes, secret: str, timestamp: int) -> str:
    """Computes HMAC-SHA256 signature for custom webhook payload and timestamp."""
    data = f"{timestamp}.".encode("utf-8") + payload_bytes
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()


def sign_waha_payload(payload_bytes: bytes, secret: str) -> str:
    """Computes WAHA native HMAC-SHA256 signature (direct body digest)."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def verify_webhook_signature(
    payload_bytes: bytes,
    secret: str,
    signature_header: Optional[str] = None,
    timestamp_header: Optional[str] = None,
    waha_hmac_header: Optional[str] = None,
    max_drift_seconds: int = 300,
) -> Tuple[bool, Optional[str]]:
    """
    Validates HMAC-SHA256 signature supporting both WAHA native HMAC and custom listener signatures.
    """
    is_prod = os.getenv("APP_ENV", "").lower() == "production"

    if not secret:
        if is_prod:
            return False, "Rejecting webhook: WEBHOOK_SECRET is not configured in production"
        return True, None

    # 1. Check WAHA native HMAC (sent via x-waha-hmac or x-hub-signature-256)
    if waha_hmac_header:
        sig = waha_hmac_header.strip()
        if sig.startswith("sha256="):
            sig = sig[7:]
        expected_sig = sign_waha_payload(payload_bytes, secret)
        if hmac.compare_digest(expected_sig, sig):
            return True, None
        return False, "Invalid WAHA HMAC signature"

    # 2. Check Custom Listener signature (x-webhook-signature + x-webhook-timestamp)
    if signature_header:
        if not timestamp_header:
            return False, "Missing x-webhook-timestamp header for custom listener signature"

        try:
            ts = int(timestamp_header)
            now = int(time.time())
            if abs(now - ts) > max_drift_seconds:
                return False, f"Timestamp drift exceeded: {abs(now - ts)}s > {max_drift_seconds}s"
        except ValueError:
            return False, "Invalid timestamp header"

        expected_sig = sign_payload(payload_bytes, secret, ts)
        if hmac.compare_digest(expected_sig, signature_header):
            return True, None
        return False, "Invalid webhook HMAC signature"

    return False, "Missing webhook signature header (expected x-waha-hmac or x-webhook-signature)"
