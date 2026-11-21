from __future__ import annotations
import hmac
import hashlib
import time
from typing import Dict, Optional, Tuple
import bcrypt


class LockoutManager:
    """Tracks failed login attempts and applies temporary cooldowns."""

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 900):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts: Dict[str, list[float]] = {}

    def is_locked_out(self, client_id: str) -> Tuple[bool, int]:
        now = time.time()
        attempts = [t for t in self._attempts.get(client_id, []) if now - t < self.lockout_seconds]
        self._attempts[client_id] = attempts
        if len(attempts) >= self.max_attempts:
            cooldown_left = int(self.lockout_seconds - (now - attempts[0]))
            return True, max(1, cooldown_left)
        return False, 0

    def record_failure(self, client_id: str) -> None:
        now = time.time()
        if client_id not in self._attempts:
            self._attempts[client_id] = []
        self._attempts[client_id].append(now)

    def record_success(self, client_id: str) -> None:
        if client_id in self._attempts:
            del self._attempts[client_id]


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_session_token(secret: str, user_id: str = "fahad") -> str:
    ts = int(time.time())
    msg = f"{user_id}:{ts}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{user_id}:{ts}:{sig}"


def verify_session_token(token: str, secret: str, max_age_days: int = 30) -> bool:
    if not token or not secret:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    user_id, ts_str, sig = parts
    try:
        ts = int(ts_str)
        if time.time() - ts > (max_age_days * 86400):
            return False
    except ValueError:
        return False

    msg = f"{user_id}:{ts}".encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, sig)


def generate_csrf_token(session_token: str, secret: str) -> str:
    msg = f"csrf:{session_token}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:32]


def verify_csrf_token(csrf_token: str, session_token: str, secret: str) -> bool:
    expected = generate_csrf_token(session_token, secret)
    return hmac.compare_digest(expected, csrf_token)
