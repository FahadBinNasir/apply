from __future__ import annotations
import asyncio
import base64
import hashlib
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import httpx

from contracts.protocols import LLMProvider

logger = logging.getLogger(__name__)

# Privacy tokens that must NEVER appear in LLM prompts
SENSITIVE_PATTERNS = [
    "fahadabbasi17025@gmail.com",
    "327 8262810",
    "3278262810",
]


class PrivacyViolationError(Exception):
    pass


class LLMUnavailableError(Exception):
    """Raised when all configured LLM providers fail or quota is exhausted."""
    pass


class ProductionLLMProvider:
    """Free-tier resilient LLM Provider with Gemini primary and Groq fallback."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None,
        groq_model: Optional[str] = None,
        session_factory: Optional[Any] = None,
    ):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.gemini_model = gemini_model or os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash")
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.session_factory = session_factory

        self._cache: Dict[str, Dict[str, Any]] = {}
        self._daily_requests: int = 0
        self._last_request_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    def _check_privacy(self, prompt: str) -> None:
        for pattern in SENSITIVE_PATTERNS:
            if pattern in prompt:
                raise PrivacyViolationError(f"Privacy guard tripped: Sensitive profile token found in prompt!")

    def _compute_hash(self, prompt: str, image_bytes: Optional[bytes]) -> str:
        h = hashlib.sha256(prompt.encode("utf-8"))
        if image_bytes:
            h.update(image_bytes)
        return h.hexdigest()

    async def generate_json(
        self,
        schema: Dict[str, Any],
        prompt: str,
        image_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._check_privacy(prompt)

        cache_key = self._compute_hash(prompt, image_bytes)
        if cache_key in self._cache:
            return self._cache[cache_key]

        async with self._lock:
            self._daily_requests += 1
            self._last_request_time = datetime.now(timezone.utc)

        last_error = None

        # 1. Try Gemini primary with header auth
        if self.gemini_api_key:
            try:
                res = await self._call_gemini(prompt, image_bytes, mime_type)
                self._cache[cache_key] = res
                self._record_usage("gemini", self.gemini_model, cache_key)
                return res
            except Exception as e:
                logger.warning("Gemini provider failed after retries: %s. Falling back to Groq.", type(e).__name__)
                last_error = e

        # 2. Try Groq fallback (text only)
        if self.groq_api_key and not image_bytes:
            try:
                res = await self._call_groq(prompt)
                self._cache[cache_key] = res
                self._record_usage("groq", self.groq_model, cache_key)
                return res
            except Exception as e:
                logger.warning("Groq fallback provider failed after retries: %s.", type(e).__name__)
                last_error = e

        # No fake fallback! If providers fail or no keys exist, raise LLMUnavailableError
        raise LLMUnavailableError(
            f"All LLM providers unavailable or keys not configured. Last error: {last_error or 'Missing API keys'}"
        )

    def _record_usage(self, provider: str, model: str, post_hash: str) -> None:
        if not self.session_factory:
            return
        try:
            from app.db.models import LLMUsageModel
            import uuid
            with self.session_factory() as session:
                session.add(
                    LLMUsageModel(
                        id=f"use_{uuid.uuid4().hex[:12]}",
                        provider=provider,
                        model=model,
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0.0,
                        post_hash=post_hash,
                        created_at=datetime.now(timezone.utc),
                    )
                )
                session.commit()
        except Exception:
            pass

    async def _call_gemini(
        self,
        prompt: str,
        image_bytes: Optional[bytes],
        mime_type: Optional[str],
    ) -> Dict[str, Any]:
        # Clean URL without key parameter - authenticate strictly via x-goog-api-key header
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        headers = {
            "x-goog-api-key": self.gemini_api_key,
            "Content-Type": "application/json",
        }

        parts: list[dict] = [{"text": prompt}]
        if image_bytes:
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": mime_type or "image/jpeg",
                    "data": b64_data,
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code in (429, 500, 502, 503, 504):
                        if attempt == 3:
                            raise RuntimeError(f"Gemini HTTP {resp.status_code} quota or server error")
                        delay = (2 ** attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(delay)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_resp)
            except Exception as e:
                if attempt == 3:
                    raise
                await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 0.5))

        raise RuntimeError("Gemini retry limit reached")

    async def _call_groq(self, prompt: str) -> Dict[str, Any]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "You are a recruitment extraction assistant. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code in (429, 500, 502, 503, 504):
                        if attempt == 3:
                            raise RuntimeError(f"Groq HTTP {resp.status_code} quota or server error")
                        delay = (2 ** attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(delay)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
            except Exception as e:
                if attempt == 3:
                    raise
                await asyncio.sleep((2 ** attempt) + random.uniform(0.1, 0.5))

        raise RuntimeError("Groq retry limit reached")

    def get_quota_status(self) -> Dict[str, Any]:
        return {
            "gemini_configured": bool(self.gemini_api_key),
            "groq_configured": bool(self.groq_api_key),
            "daily_requests_made": self._daily_requests,
            "last_request_time": self._last_request_time.isoformat() if self._last_request_time else None,
            "cache_size": len(self._cache),
        }
