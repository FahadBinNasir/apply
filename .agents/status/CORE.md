# Status: CORE Agent

## Progress
- Single-user authentication & security implemented in `app/auth/security.py`:
  - Password hashing with bcrypt.
  - Signed session tokens using HMAC-SHA256 with `SESSION_SECRET`.
  - CSRF tokens on state-changing requests.
  - Lockout protection: 5 failed attempts -> 15-minute lock.
- Viewmodel builders implemented in `app/viewmodels/builders.py`:
  - Produce schemas matching `contracts/mocks/*.json` for Inbox, Job Detail, Sent log, Skipped list, Opportunities, WhatsApp status, Settings, and Health.
- Processing Pipeline implemented in `app/worker/pipeline.py`:
  - Chains: PreFilter -> LinkFetcher -> Extractor -> RulesEngine -> Scorer -> Deduper -> CVBuilder -> Mailer -> JobRepo.
- Background QueueWorker implemented in `app/worker/queue_worker.py`:
  - Asynchronous dequeue, execution, ack, and nack with exponential backoff.
- APScheduler configured in `app/scheduler/tasks.py`:
  - 2-hour channel/Pintern sweep, daily midnight deadline expiry and cleanup.
- FastAPI REST & View routers implemented in `app/api/routers.py`:
  - `/health`, `/login`, `/logout`, `/`, `/jobs/{job_id}`, `/jobs/{job_id}/cv/download`, `/jobs/{job_id}/ics`, `/sent`, `/skipped`, `/opportunities`, `/whatsapp`, `/settings`.
  - Actions: `/api/jobs/{id}/approve-send`, `/api/jobs/{id}/reject`, `/api/jobs/{id}/snooze`, `/api/jobs/{id}/mark-manual`, `/api/jobs/{id}/rescue`.
  - Ingestion: `/api/intake/webhook`.
  - Developer simulator: `POST /api/dev/simulate`.
- FastAPI main application wired in `app/main.py`:
  - Dependency-injection wiring (production vs `USE_FAKES`).
  - Lifespan background task management (QueueWorker and APScheduler).
  - Security headers middleware (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
- Unit tests written and green: `tests/core/test_core.py` (4 passed).
- Requirements listed in `requirements/core.txt`.
- Env vars declared in `contracts/env/core.yaml`.

## Interfaces Implemented
- FastAPI Application, Routes & Dependency Injection wiring.

## Open Issues / Notes
- None. Ready for UI templates and integration.
