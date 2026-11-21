# WhatsApp Job Agent (Self-Hosted, 100% Free)

A self-hosted, privacy-first automated job discovery and application platform for **Fahad Bin Nasir**. It continuously monitors WhatsApp groups and channels, parses and extracts job opportunities using free-tier AI, evaluates candidate fit using deterministic matching rules, constructs tailored ATS-friendly CVs and emails, and presents them in a mobile-first dashboard for one-click approval and Gmail dispatch.

---

## Key Highlights

- **100% Free Stack:** Powered entirely by open-source software, Google AI Studio Gemini free tier (`gemini-2.5-flash`), Groq free tier (`llama-3.3-70b-versatile`), Gmail API, and Docker on an Oracle Cloud Always Free VPS.
- **Listen-Only Ban Hygiene:** The WhatsApp instance strictly listens to incoming webhooks and **never** sends messages, replies, or joins groups.
- **Approval-Gate Security:** Zero automatic applications. No email is ever dispatched without explicit human review and approval.
- **Anti-Fabrication Verifier:** Tailored CVs and email drafts are strictly validated against `profile.seed.yaml`. Invented projects, degrees, or employers are rejected.
- **Multi-Role Splitting:** Posts containing multiple job listings (such as a university post with 30 openings) are split and scored individually.
- **Mobile-First Operate UX:** Built with vanilla CSS and HTMX, optimized for mobile screens (360px - 430px) with accessible tier badges and 44px touch targets.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │ WhatsApp Groups & Channels              │
                      └────────────────────┬────────────────────┘
                                           │ Listen-only webhook
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Docker Network (Portainer Stack)                                            │
│                                                                             │
│  ┌───────────────────────┐               ┌────────────────────────────────┐ │
│  │ whatsapp (WAHA Core)  ├──────────────►│ app (FastAPI Backend)          │ │
│  │ LocalAuth session     │  HMAC signed  │  - Zero-LLM PreFilter          │ │
│  └───────────────────────┘    webhooks   │  - SSRF-Guarded Link Fetcher   │ │
│                                          │  - Gemini / Groq Extractor     │ │
│  ┌───────────────────────┐               │  - Deterministic Rules Engine  │ │
│  │ SQLite WAL Database   │◄──────────────┤  - ReportLab CV Builder        │ │
│  │ - Persistent Queue    │               │  - Mobile HTMX Dashboard       │ │
│  │ - FTS5 Full-Text      │               │  - Gmail API Sender            │ │
│  └───────────────────────┘               └───────────────┬────────────────┘ │
└──────────────────────────────────────────────────────────┼──────────────────┘
                                                           │
                                                           ▼
                                            ┌───────────────────────────────┐
                                            │ Fahad's Mobile Dashboard      │
                                            │ (Review, Approve & Dispatch)  │
                                            └───────────────────────────────┘
```

---

## Directory Structure

```
├── .agents/               # Swarm message board, decisions, and status logs
├── app/
│   ├── api/               # FastAPI route controllers (OpenAPI & HTMX)
│   ├── auth/              # Bcrypt auth, signed session cookies, lockout, CSRF
│   ├── calendar/          # RFC 5545 .ics generator for walk-ins
│   ├── cv/                # ReportLab 1-page ATS CV builder & anti-fabrication verifier
│   ├── db/                # SQLAlchemy 2 models, SQLite WAL session, Fernet crypto
│   ├── intake/            # WAHA Core adapter, webhook HMAC security, capture-first logic
│   ├── llm/               # Gemini & Groq resilient client, privacy guards, prompts
│   ├── mail/              # Gmail API client, SMTP fallback, email drafter, wa.me helper
│   ├── pipeline/          # PreFilter, Extractor, LinkFetcher, RulesEngine, Scorer, Deduper
│   ├── scheduler/         # APScheduler 2-hour sweeps and daily cleanup
│   ├── viewmodels/        # View-model builders matching mock JSON schemas
│   ├── web/               # Templates (Jinja2), static CSS, and local mock server
│   └── main.py            # Application entrypoint & dependency injection
├── contracts/             # Frozen contracts: Pydantic models, Protocols, fakes, mocks
├── docker/                # Multi-arch Dockerfile for app container (amd64/arm64)
├── scripts/               # Backup and restore scripts (bash and PowerShell)
├── tests/                 # Comprehensive test suite (46+ unit, contract, E2E tests)
├── .env.example           # Environment template with generation commands
├── DEPLOY.md              # Oracle Cloud VPS & Portainer deployment manual
├── fixtures.md            # Acceptance criteria and real fixture posts
├── profile.seed.yaml      # Candidate ground truth (the ONLY source of CV facts)
└── TROUBLESHOOTING.md     # Firewall, WhatsApp disconnects, and quota guides
```

---

## Quickstart & Local Testing

### 1. Run Tests Locally
```bash
python -m pytest -v
```

### 2. Run Local Development Server (with in-memory fakes)
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```
Visit `http://localhost:8080` and log in with password `devpassword` or `admin`.

### 3. Production Deployment
Refer to [DEPLOY.md](file:///C:/Users/fahad/Documents/apply/DEPLOY.md) for step-by-step instructions on deploying as a Portainer Repository Stack on an Oracle Cloud VPS.
