# Status: INTAKE Agent

## Progress
- `WAHAIntakeAdapter` implemented in `app/intake/waha.py`:
  - Listen-only adapter connecting to WAHA Core (`devlikeapro/waha`, free tier, WEBJS).
  - Normalizes group (`@g.us`), channel (`@newsletter`), and self-chat (`@c.us`) messages into `IncomingMessage`.
  - Computes SHA256 content hashes for deduplication.
  - Queries session status and exposes QR code.
- `verify_webhook_signature` implemented in `app/intake/security.py`:
  - HMAC-SHA256 signature verification and timestamp drift anti-replay guard (<=300s).
- `WebhookIntakeHandler` implemented in `app/intake/handler.py`:
  - Capture-first architecture: saves message to raw inbox DB table BEFORE any AI or rules call.
  - Idempotent deduplication by message hash.
  - Chat allow-list filtering.
  - Enqueues into persistent SQLite queue with priority.
- Fallback listener implemented in `whatsapp/`:
  - Multi-arch Dockerfile (amd64 / arm64) using Node 20 and system Chromium.
  - `whatsapp/index.js` listener with LocalAuth in `/wa_session`, signing webhook dispatches.
- Unit tests written and green: `tests/intake/test_intake.py` (3 passed).
- Requirements listed in `requirements/intake.txt`.
- Env vars declared in `contracts/env/intake.yaml`.

## Interfaces Implemented
- `IntakeSource` (from `contracts.protocols`)

## Open Issues / Notes
- WAHA Core free tier is preferred for simplicity and built-in REST API; fallback `whatsapp-web.js` container is ready if needed.
