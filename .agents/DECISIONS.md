# Architecture & Swarm Decisions Log

## DEC-001: Free-Tier Stack & Protocol-Driven Modular Isolation
- Date: 2026-11-21
- Context: Single-user self-hosted WhatsApp Job Agent on Oracle Cloud VPS (Ubuntu, 2 cores, 12GB RAM, Portainer Stack). Free tier constraints.
- Decision: Use FastAPI + SQLAlchemy 2 (SQLite WAL) + Jinja2 + HTMX + vanilla CSS. No React/Next/Postgres. All components interact via strict Protocol interfaces defined in `/contracts`.
- Status: Accepted

## DEC-002: Intake Strategy - WAHA Core with whatsapp-web.js fallback
- Date: 2026-11-21
- Context: WhatsApp listening without bans or paid services.
- Decision: Support WAHA Core (`devlikeapro/waha`, free tier, WEBJS engine) as preferred intake, plus lightweight `whatsapp-web.js` fallback container with LocalAuth. Always support self-chat ("Message yourself") and group/channel forwarding. Listen-only, zero outgoing messages.
- Status: Accepted

## DEC-003: LLM Resilience and Fallback
- Date: 2026-11-21
- Context: Free tier quota limits for Gemini and Groq.
- Decision: Primary provider is Google AI Studio Gemini free tier (multimodal for poster images), secondary fallback is Groq free tier. Aggressive pre-filter without LLM drops non-job noise before any API call. Persistent SQLite queue holds items during 429 backoff or quota exhaustion.
- Status: Accepted

## DEC-004: Anti-Fabrication CV Tailoring
- Date: 2026-11-21
- Context: Automated CV tailoring must never invent facts, experiences, or claims.
- Decision: LLM generates only a tailoring selection plan (ordering, relevant project IDs from `profile.seed.yaml`, skill emphasis). Code strictly validates every item against `profile.seed.yaml`. Anti-fabrication verifier enforces 100% ground-truth compliance.
- Status: Accepted
