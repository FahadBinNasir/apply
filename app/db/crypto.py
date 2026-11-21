import base64
import os
from typing import Optional
from cryptography.fernet import Fernet


class TokenEncryption:
    """Helper for encrypting and decrypting sensitive tokens at rest using Fernet."""

    def __init__(self, key: Optional[str] = None):
        env_key = key or os.getenv("FERNET_KEY")
        if not env_key:
            # Generate deterministic fallback for dev/test if not provided
            env_key = base64.urlsafe_b64encode(b"01234567890123456789012345678901").decode("utf-8")
        self._fernet = Fernet(env_key.encode("utf-8") if isinstance(env_key, str) else env_key)

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        return self._fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        if not cipher_text:
            return ""
        return self._fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
