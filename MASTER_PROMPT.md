# MASTER PROMPT: WhatsApp Job Agent (self-hosted, 100% free), built by a parallel agent swarm

You are the **LEAD agent** (architect and integrator) of a multi-agent build in Google Antigravity. Your job is to freeze contracts first, then spawn specialist subagents that work **in parallel without interfering with each other**, then integrate, verify, and ship. Work autonomously. Do not stop to ask questions: where something is unknown, choose a sensible default, record a `TODO` in the docs, and continue.

Read first (part of the spec): `profile.seed.yaml` (the only source of truth for CV facts), `fixtures.md` (real posts and the tier each must get), `Fahad_CV_v3.pdf` (original CV look and content).

---

## PART A. WHAT WE ARE BUILDING

Fahad is in many WhatsApp groups and channels that post jobs and internships. Build a self-hosted system that:
1. Captures every post (text, poster image, or link) from groups and channels.
2. Understands it, decides if it fits him, and sorts it into tiers.
3. For good matches, builds a tailored CV (PDF) and a draft application email.
4. Shows everything in a mobile-first dashboard for review and approval.
5. On approval only, sends the email from his Gmail with the CV attached and logs it.

Nothing is ever sent without explicit approval. The WhatsApp number only LISTENS (no sends, no replies, no joins).

### Hard constraints
- **Everything free.** No paid APIs or tiers. Allowed: open-source software, Gemini API free tier, Groq free tier, Gmail API, Docker, SQLite.
- One Oracle Cloud VPS: Ubuntu, 2 cores, 12 GB RAM, 200 GB disk, Docker + Portainer. CPU architecture unknown, so everything must work on **amd64 and arm64**.
- Deployed as a **Portainer Stack from a GitHub repo** (compose in repo root). Hostname: `apply.fahadbinnasir.tech`. Existing Portainer: `portainer.fahadbinnasir.tech`.
- Single user. No n8n/Zapier/SaaS glue. No secrets in the repo; everything via env vars with a full `.env.example`.
- Development happens on **Windows** (Antigravity, Docker Desktop) but deploys to Linux: add `.gitattributes` with `* text=auto eol=lf`, no bash-only dev scripts without a PowerShell twin, use forward-slash paths in code.
- Stack: Python 3.12, FastAPI, SQLAlchemy 2 + SQLite (WAL), APScheduler, Jinja2 + HTMX + vanilla CSS. **Do not use** React/Next/shadcn/GSAP/Lenis/PostgreSQL/Supabase/Vercel skills or libraries. They are in the environment but wrong for this project.

### Architecture (Docker Compose)
- `whatsapp`: intake container, internal network only.
- `app`: one Python container running webhook intake, queue worker, scheduler, Gmail sender, CV renderer, and the dashboard. SQLite in a named volume.
- `proxy`: optional compose profile `with-proxy` (Caddy, free HTTPS). The default compose must NOT bind 80/443 (an existing proxy serves Portainer): expose `app` on `127.0.0.1:${APP_PORT:-8080}` plus an external-network option. Document attaching to Nginx Proxy Manager, Traefik, or Caddy.
- Memory limits: whatsapp about 2.5 GB, app about 2 GB. Healthchecks, `restart: unless-stopped`, volumes `wa_session` and `app_data`.

---

## PART B. SWARM OPERATING MODEL (read carefully)

### B1. Phases and gates
Use `native_swarm` (shared message board) to spawn agents and `swarm_monitor` to watch them; use `run-workflow` (`pipeline` and `parallel`) to orchestrate phases. Max concurrent agents = 6 by default (set `SWARM_MAX_PARALLEL`); if the platform rate-limits, queue the rest by priority order below.

| Phase | Who | Output | Gate to continue |
|---|---|---|---|
| 0 Contracts | LEAD alone | `/contracts` frozen, fakes, mocks, ownership map, board, branches | G0: `pytest contracts` passes; every Protocol has a fake; mock JSON covers every screen state; `contracts/VERSION=1` |
| 1 Build wave | 9 specialist agents in parallel | each agent's module, tests green against fakes | G1: each agent posts `DONE` with its checklist ticked |
| 2 Integration | LEAD | merged `main`, DI wiring, end-to-end fixtures pass | G2: all `fixtures.md` cases pass end to end offline |
| 3 Verification | QA, SEC, A11Y, EVAL agents in parallel | findings on the board; owners fix | G3: no open P0/P1 findings |
| 4 Release | LEAD | docs, deploy guide, final summary | Definition of Done (Part F) |

Priority order for slot allocation in Phase 1: DATA, RULES, EXTRACT, CVMAIL, UI, INTAKE, CORE, DEVOPS, QA.

### B2. Contract-first (this is what makes parallelism safe)
In Phase 0, LEAD writes `/contracts` (the **only** place agents share code) and nobody else may edit it:
- Pydantic models: `IncomingMessage, InboxItem, ExtractedRole, ExtractionResult, JobCard, Tier, Status, ApplyMethod, TailorPlan, CVArtifact, EmailDraft, SendResult, Profile, Settings`.
- `Protocol` interfaces: `IntakeSource, LLMProvider, Extractor, PreFilter, LinkFetcher, RulesEngine, Scorer, Deduper, CVBuilder, Mailer, CalendarExporter, JobRepo, InboxRepo, Queue`.
- **In-memory fake implementation of every Protocol** (`contracts/fakes/`) so every agent can develop and test alone from minute one.
- DB schema (ERD plus table list), event names, error codes, REST/HTMX route table (OpenAPI), env-var registry, port map.
- **View-model schemas for every UI screen with rich mock JSON** (`contracts/mocks/*.json`) covering normal, empty, error states (WhatsApp disconnected, quota exhausted, Gmail token expired, nothing pending). UI builds against these mocks without waiting for the backend.
- `contracts/fixtures.expected.json`: machine-readable mapping of every `fixtures.md` case to its expected tier and reason.
- Contract changes: only via a `CONTRACT-CHANGE` request on the board. LEAD approves or rejects within one cycle, bumps `contracts/VERSION`, and posts the diff. Agents then rebase.

### B3. File ownership (no overlaps, no exceptions)
| Path | Owner |
|---|---|
| `/contracts/**` , `/README.md`, `/TROUBLESHOOTING.md` | LEAD |
| `/app/db/**`, `/migrations/**` | DATA |
| `/whatsapp/**`, `/app/intake/**` | INTAKE |
| `/app/llm/**`, `/app/pipeline/prefilter*`, `extract*`, `linkfetch*` | EXTRACT |
| `/app/pipeline/rules/**`, `scoring*`, `dedupe*`, `tiers*` | RULES |
| `/app/cv/**`, `/app/mail/**`, `/app/calendar/**` | CVMAIL |
| `/app/main.py`, `/app/api/**`, `/app/auth/**`, `/app/worker/**`, `/app/scheduler/**`, `/app/viewmodels/**` | CORE |
| `/app/web/templates/**`, `/app/web/static/**`, `/app/web/mock/**`, `PRODUCT.md`, `DESIGN.md` | UI |
| `/docker/**`, `docker-compose*.yml`, `DEPLOY.md`, `/.github/**`, `/scripts/**`, root `requirements.txt` | DEVOPS |
| `/tests/<agent>/**` | that agent |
| `/tests/e2e/**` | QA |

Rules that prevent interference:
- Never edit a file you do not own. Need a change there? Post `REQUEST @OWNER` on the board.
- Each agent works in its **own git worktree/branch** `agent/<name>`; commits small and often with conventional messages. Only LEAD merges, in this order: DATA, RULES, EXTRACT, CVMAIL, INTAKE, CORE, UI, DEVOPS, QA.
- Dependencies: each agent lists its packages in `requirements/<name>.txt`; DEVOPS merges them into the root lock. No global upgrades, no repo-wide formatting sweeps.
- Env vars: each agent declares its own in `contracts/env/<name>.yaml` (LEAD merges into `.env.example`).
- Ports (dev): app 8080, UI mock 8081, whatsapp 3000, no one else picks ports. Temp files only under `.agents/tmp/<name>/`. Tests use `:memory:` or temp SQLite files, never a shared DB.
- Never put secrets on the board or in commits.

### B4. Sharing information
- **Board**: `.agents/board/BOARD.md` (use the native_swarm message board when available, mirror to this file). Append-only entries: `[time][FROM -> TO|ALL][INFO|QUESTION|REQUEST|CONTRACT-CHANGE|BLOCKED|DONE] message`.
- Read the board at the start of every work chunk and before declaring DONE. Answer QUESTIONs addressed to you in your next chunk.
- Status: each agent keeps `.agents/status/<NAME>.md` (progress, interfaces implemented, open issues).
- Decisions worth keeping go to `.agents/DECISIONS.md` (use the `claude-mem` skill).
- **Never idle-wait.** If blocked on another agent, build against the fakes and mocks and continue.
- Conserve context (`context-mode` skill): each agent reads Part A, Part B, its own Part C block, and only the Part D sections tagged with its name.

### B5. Skills: who uses what
Use a skill only when the task calls for it; do not load them all. If a skill is missing, proceed with the same principles manually. **Design precedence: `impeccable` decides direction; `anti-ui-slop` is the quality gate; the others are advisory.**

| Agent | Skills |
|---|---|
| LEAD | `superpowers`, `get-shit-done`, `api-and-interface-design`, `database-schema-designer`, `context-mode`, `claude-mem`, `native_swarm`, `swarm_monitor`, `run-workflow`, `pr-review`, `repo-manager`, `github-hub` |
| DATA | `sqlalchemy-orm`, `database-schema-designer`, `database-migration`, `sql-optimization-patterns`, `test-driven-development` |
| INTAKE | `fastapi-backend`, `webhook-and-oauth-security`, `debugging-and-error-recovery`, `test-driven-development` |
| EXTRACT | `test-driven-development`, `generate-synthetic-data`, `write-code-eval`, `error-discovery`, `security-and-hardening` (SSRF), `presidio-privacy-governance` (only as a lightweight PII guard) |
| RULES | `test-driven-development`, `write-code-eval`, `generate-synthetic-data`, `sql-optimization-patterns` (only if queries are needed) |
| CVMAIL | `webhook-and-oauth-security` (OAuth), `security-and-hardening` (token encryption), `pdf-accessibility` (ATS-friendly text PDF), `test-driven-development` |
| CORE | `fastapi-backend`, `api-and-interface-design`, `security-and-hardening`, `webhook-and-oauth-security`, `test-driven-development` |
| UI | `impeccable` (mandatory), `dashboard-design`, `ui-ux-pro-max`, `design-taste-frontend`, `anti-ui-slop`, `web-design-guidelines`, `modern-web-guidance`, `contrast-master`, `keyboard-navigator` |
| DEVOPS | `ci-cd-and-automation`, `security-and-hardening`, `github-hub`, `repo-manager`, `release-manager` |
| QA | `playwright-core`, `playwright-verifier`, `playwright-auth-state`, `playwright-network-mocking`, `playwright-debugging`, `browser-testing-with-devtools`, `debugging-and-error-recovery` |
| SEC (phase 3) | `security-and-hardening`, `webhook-and-oauth-security`, `presidio-privacy-governance` |
| A11Y (phase 3) | `web-accessibility-wizard`, `contrast-master`, `keyboard-navigator`, `aria-specialist`, `wcag-guide` |
| EVAL (phase 3) | `evals-start`, `eval-audit`, `write-code-eval`, `error-discovery`, `generate-synthetic-data` |

---

## PART C. AGENT BRIEFS (Phase 1, run in parallel)

Each brief: what to build, what it exposes, done checklist. All code is typed, documented, and has tests that pass against fakes.

### C1. DATA
Owns the database. Build SQLAlchemy 2 models and migrations (Alembic) for: `inbox`, `jobs` (one per extracted role, merged across sources), `job_sources`, `drafts`, `cv_artifacts`, `sends`, `settings`, `profile`, `queue`, `llm_usage`, `noise_log`, `audit_log`. SQLite with WAL, indexes for deadline/tier/status queries, FTS5 for search. Implement `JobRepo`, `InboxRepo`, `Queue` (persistent, retryable, priority, resumable after quota or crash). Encrypted-at-rest field helper (Fernet) for OAuth tokens.
Done: repos pass contract tests; migration up/down works; queue survives restart.

### C2. INTAKE (WhatsApp, free, listen-only)
Implement `IntakeSource` adapters:
1. **Preferred: WAHA Core** (`devlikeapro/waha`, free tier, WEBJS engine). Configure webhook to `app`, events `message`, API key, dashboard disabled. **Verify in current docs and by testing** whether the free tier can receive (a) group messages, (b) channel/newsletter messages, (c) image downloads.
2. **Fallback if limited:** a small `whatsapp-web.js` listener container (LocalAuth in `wa_session`, system Chromium via `PUPPETEER_EXECUTABLE_PATH`, `--no-sandbox`, works on arm64 and amd64) that POSTs normalized messages to `app` with `x-webhook-secret` (HMAC plus timestamp anti-replay).
3. **Always support the "Message yourself" chat** as a guaranteed input path (forward a channel post to yourself).
Rules: capture-first (store raw message and media BEFORE any AI call), idempotent by message id and content hash, allow-list of watched chats, QR and connection status exposed through a service interface. Ban hygiene: no sending of any kind.
Done: simulated and real-format payloads for groups, channels, self-chat, image and text all land in `inbox` exactly once.

### C3. EXTRACT (understanding)
- **PreFilter** (no LLM): drop empty, greetings, surveys, ads, matrimonial, events, "any alumni at X?" posts; conservative, everything dropped logged as NOISE with reason.
- **LLMProvider**: abstraction with `generate_json(schema, prompt, image=None)`. Providers `gemini` (default, Google AI Studio free tier, multimodal for posters) and `groq` (free fallback). **Look up currently available free-tier model names and limits at build time** and put them in env (`GEMINI_MODEL_FAST`, `GEMINI_MODEL_SMART`). Global rate limiter, exponential backoff on 429, response cache by content hash, daily budget counter, graceful "waiting for quota" (work stays queued, never lost). Prompts live in versioned files `/app/llm/prompts`.
- **Extractor** outputs validated JSON (retry once on invalid):
```
{ is_job, post_type: job|internship|trainee|freelance|volunteer|walkin|scholarship|fellowship|hackathon|course|other,
  roles: [ { title, company, field, location_text, work_mode(onsite|hybrid|remote|unknown), city,
             experience_min_years, experience_max_years, education, skills[], responsibilities[],
             deadline(ISO|null), shift_text, night_shift, gender_requirement(male|female|any),
             apply_method(email|whatsapp|link|form|linkedin|walkin|unknown),
             apply_email, apply_whatsapp, apply_link, exact_subject, from_image(bool),
             walkin{date,time,address}, fresh_grad_ok, notes } ], confidence }
```
  One post can hold MANY roles (a university listing 30 positions): split into one item per role. `exact_subject` is extracted verbatim when a post demands a subject line (keep punctuation such as en dashes); "mention the position title" means use the role title. Never guess emails or phones. Emails read from images set `from_image=true`.
- **LinkFetcher**: many Pintern posts are only a headline plus link. Fetch with `httpx` + `trafilatura`, timeouts, size cap, retries, cache, strip tracking params, **SSRF guard** (block private IPs and localhost, re-check after redirects). Playwright only if a page truly needs JS. `lnkd.in`/LinkedIn cannot be read: emit a MANUAL result.
- Prompt-injection defense: posts are untrusted data; LLM output may only fill data fields, never trigger actions.
- Privacy: the profile's phone/email/CNIC must never appear in any LLM prompt (add a guard plus a test).
- Evals: use `generate-synthetic-data` to create varied post styles (Roman Urdu, emoji-heavy, noisy posters, multi-role, link-only) and `write-code-eval` to measure extraction accuracy on `fixtures.md`; run `error-discovery` on failures.
Done: fixture posts extract correctly with recorded LLM responses (offline) and with a `@live` test marked optional.

### C4. RULES (decisions, pure code, no LLM)
Pure functions with exhaustive unit tests, driven by `fixtures.expected.json` plus synthetic cases. Implement per Part D3: field filter, location filter, level handling, deadlines (with `NOW_OVERRIDE`), night shift, gender, education gates, dedupe (`rapidfuzz`, company plus normalized title, merging sources), repeat-application guard, tier assignment (STRONG/STRETCH/MANUAL/WALKIN/OPPORTUNITY/SKIPPED/NOISE) with a human-readable reason list, and the `Scorer` combiner (LLM score plus rules flags to final tier).
Done: all fixture cases produce the expected tier and reason; property tests pass.

### C5. CVMAIL (outputs)
- **CVBuilder**: RenderCV (YAML to PDF via Typst, Python 3.12+) with a clean ATS-friendly one-page theme; fallback ReportLab/WeasyPrint. The LLM returns only a **selection and rephrase plan** (up to 3 projects, ordering, skill emphasis, 2 to 3 line summary); code builds the CV from `profile.seed.yaml`. **Anti-fabrication verifier is mandatory**: every project, skill, tool, course, employer, number, and date in the output must exist in the profile; on failure retry once with the violations listed, else use a safe template. Per-domain ordering by project `tags` (AI/data leads with ChurnVision then Exam Cheating Detector then FYP; backend/full-stack/DevOps leads with the FYP; mobile with the Flutter suite; IoT with the IoT project; .NET stresses C#, SQL, REST honestly and never claims WebForms experience). Summary adapts to internship vs job and truthfully states 7th semester. Output `Fahad_Bin_Nasir_CV_<Company>_<Role>.pdf` plus PNG page previews (PyMuPDF), because mobile browsers handle inline PDFs badly.
- **Mailer**: Gmail API, scope `gmail.send` only, OAuth flow at `/settings/gmail` with redirect `https://apply.fahadbinnasir.tech/oauth/google/callback`, refresh token stored encrypted. Document that the consent screen must be "In production" (personal use) or refresh tokens expire in 7 days. Fallback `MAIL_BACKEND=smtp` with a Gmail App Password. Draft email 90 to 130 words, polite, mentions 2 real matches, CV attached, name/phone/links, 7th semester; for full-time posts that might accept interns add one line asking to be considered for an internship/trainee role. **Subject = `exact_subject` verbatim when present**, else "Application for <Role>, Fahad Bin Nasir". `SEND_ENABLED=false` by default (dry-run). Daily cap (default 25), minimum gap (default 60 s), dedupe recheck right before sending, store Gmail message id, handle failed/token-expired states.
- **CalendarExporter**: `.ics` for walk-ins. **WhatsApp-apply helper**: `wa.me/<number>?text=` link (WhatsApp cannot pre-attach files, so the UI also offers CV download).
Done: verifier rejects invented facts in tests; PDF renders on a clean container; dry-run email builds correctly for F1 and F2.

### C6. CORE (runtime and API)
FastAPI app: `main.py`, routers, **single-user auth** (argon2/bcrypt hash from env, secure HttpOnly SameSite cookie, CSRF on all POSTs, login rate-limit and lockout), webhook endpoint (internal secret only), queue **worker** running the pipeline (prefilter, extract, link fetch, rules, score, tailor, draft) with concurrency 1 to 2, **APScheduler** (instant for groups, 2-hour sweep for channels/Pintern, daily expiry and cleanup, run-now and re-run), **view-model builders** in `/app/viewmodels` that produce exactly the contract schemas (a contract test compares them to the mock JSON), dev simulator `POST /api/dev/simulate` (login required, disabled in production unless `ENABLE_SIMULATOR=true`), health endpoint, security headers (CSP, frame, referrer), dependency-injection wiring selecting real or fake implementations by env.
Done: with all fakes the app runs end to end locally; pipeline processes fixtures through the worker; routes match the OpenAPI table.

### C7. UI (design, built with Impeccable)
Mobile-first (360 to 430 px primary, desktop secondary), light and dark, self-hosted fonts/assets (no CDNs), HTMX partials, no build step. Build against `contracts/mocks` with a local mock server (`/app/web/mock`, port 8081), so no backend is needed.
**Invoke `/impeccable:impeccable` and follow this sequence:** (1) `init` writes `PRODUCT.md` from the brief below (surface mode: **Operate**); (2) `shape dashboard` plans UX before code; (3) build under the skill's craft floor and bans (no generic AI-dashboard look, no purple gradients, no emoji-as-icons, no placeholder styling); (4) run `critique`, `audit`, `adapt`, `harden`, `typeset`, `layout`, then `polish`; (5) `document` writes `DESIGN.md`; (6) verify by screenshots at 390 px and 1280 px and fix what you see. Consult `dashboard-design`, `ui-ux-pro-max`, `design-taste-frontend` for ideas, gate with `anti-ui-slop`, check contrast and keyboard flow with `contrast-master` and `keyboard-navigator`.
**Brief for PRODUCT.md:** user is Fahad, a student triaging posts on his phone in short, often late, moments with deadlines looming. Feeling: calm, precise, trustworthy, quick; a personal operations desk, not a startup landing page. Card priority: deadline, tier, company and role, apply method, why it matched. Primary action Approve and Send must be hard to mis-tap and show exact recipient and subject first. Tier colors must be accessible (never color-only) in both themes.
**Screens:** (1) Inbox/Pending with tabs Strong, Stretch, Manual, Walk-in, sorted by deadline, filters new today and deadline soon; (2) Job detail: original post (zoomable image), extracted fields with OCR-derived emails highlighted for verification, match reasons and gaps, CV page previews plus download, editable recipient/subject/body, buttons Approve and Send, Save draft, Re-generate, Reject, Snooze, Mark applied manually, merged duplicate sources; (3) Sent log with CSV export; (4) Skipped list grouped by reason with a Rescue button; (5) Opportunities (scholarships, hackathons, free courses; tech-relevant, links only); (6) WhatsApp (status, QR, allow-list, last message per chat, simulator button); (7) Settings (profile editor, matching rules, send cap, SEND_ENABLED, Gmail connect, LLM provider status, quota meter, schedules); (8) Health. Full empty/error states for every screen.
Done: all screens render from every mock state; audit and critique findings fixed; screenshots saved in `/docs/screens`.

### C8. DEVOPS
Dockerfiles (multi-arch safe), `docker-compose.yml` that works as a **Portainer Repository stack** (env supplied via Portainer's editor, no `.env` needed at runtime, every variable commented), `docker-compose.dev.yml` with a fake WhatsApp source, optional `with-proxy` profile, healthchecks, limits, backup and restore scripts (SQLite plus session volume) in both bash and PowerShell, `.gitignore`, `.gitattributes`, GitHub Actions (lint, tests, `docker compose config`, multi-arch build check), root `requirements.txt` merged from `requirements/*.txt`. `DEPLOY.md` with exact steps: GitHub push; Portainer `https://portainer.fahadbinnasir.tech` Stacks, Add stack, Repository (PAT if private), env vars, Deploy; DNS A record for `apply.fahadbinnasir.tech`; Oracle Cloud security-list ingress for 80/443 **and** the Ubuntu iptables/ufw rules (Oracle Ubuntu images block them by default); attaching to the existing proxy; updates; backup/restore.
Done: `docker compose config` validates; images build for amd64 and arm64.

### C9. QA (starts in Phase 1 against mocks, finishes in Phase 3)
Write Playwright E2E specs from the contracts and the mock server (login, pending triage, job detail, edit email, approve dry-run, skipped rescue, WhatsApp disconnected state, Gmail expired banner), network mocking, auth state reuse, mobile (390 px) and desktop projects. Run against the real app in Phase 3 using the simulator and fixtures F1 to F3. File reproducible bugs on the board to the owning agent.

---

## PART D. FUNCTIONAL SPEC (tags show which agents care)

### D1. Pipeline stages [EXTRACT, RULES, CORE]
Capture, pre-filter, extract (vision for posters), link fetch for headline posts, rules, score, tier, tailor, draft, queue for approval. Each stage stores its output so it can be re-run; each card shows why it got its tier.

### D2. Tiers and statuses [all]
Tiers: `STRONG`, `STRETCH`, `MANUAL` (form, link, LinkedIn, unreadable), `WALKIN`, `OPPORTUNITY`, `SKIPPED` (always visible, collapsed, with reason and Rescue), `NOISE` (debug only). Statuses: `new, drafted, approved, sent, failed, rejected, snoozed, expired, applied_manually`.

### D3. Matching rules [RULES, EXTRACT, UI]
- **Field = hard filter** (profile `target_fields` vs `avoid_fields`). IT infrastructure/storage/networking = STRETCH.
- **Location = hard filter:** accept Karachi onsite, Karachi hybrid, Remote (must accept Pakistan-based applicants). Lahore/Islamabad/Rawalpindi/elsewhere onsite or hybrid = SKIPPED(location). Unknown location = STRETCH with a note.
- **Level = soft:** fresher/junior/trainee/MTO/0-1 years/intern never reject. Experience above `comfortable_max_years` = STRETCH; above `skip_above_years` = SKIPPED. "Final year / last semesters / currently enrolled" add weight. Mark `internship_possible` for jobs that may accept interns. Be generous: the goal is to never miss a chance.
- **Deadline:** expired = SKIPPED(expired); sort by nearest; flag within 3 days.
- **Night shift/gender per profile;** unknown gender is flagged, never auto-rejected.
- **Education gates** (MS required, ACCA/CA, MBBS) = SKIPPED(education).
- **Dedupe** across groups and channels; merge sources into one card.
- **No repeat spam:** no second application to the same company/email within N days (default 14).
- Final tier is computed in code: STRONG (score 70 or more, no hard flags), STRETCH (45 to 69 or soft flags), else SKIPPED(low fit).

### D4. LLM free-tier discipline [EXTRACT, CORE]
Pre-filter and rules cut calls; persistent queue; backoff; cache; daily counter shown in UI; if all providers are exhausted posts wait as `queued` and the UI says "waiting for quota". Low temperature for extraction.

### D5. Security [CORE, INTAKE, CVMAIL, SEC]
Single-user login with lockout; webhook accepts only the internal secret and is never exposed by the proxy; SSRF guard; media size caps; safe filenames; HTML-escape all post content (untrusted); secrets never logged, emails/phones redacted in debug logs; OAuth tokens encrypted; CSP and secure cookies in production.

### D6. Scheduling [CORE]
Groups: process on arrival. Channels/Pintern: sweep every 2 hours. Daily: expire old jobs, optional digest, cleanup. Run-now and per-job re-run buttons.

---

## PART E. TESTING AND CONNECT-AND-TRY

- Every agent: pytest against fakes. RULES and EXTRACT: every `fixtures.md` case with `NOW_OVERRIDE=2026-11-21` (note the PMTF, Alkhidmat, Nimir deadlines are already expired on that date). LLM is mocked with recorded JSON so tests are offline and free; optional `@live` tests.
- Contract tests (LEAD): fakes satisfy Protocols; view-model builders match mock JSON.
- Phase 3: QA runs Playwright end to end; SEC reviews auth, webhook, SSRF, token storage, injection handling; A11Y audits WCAG AA, contrast, keyboard, screen-reader labels; EVAL measures extraction/rules accuracy on fixtures and synthetic variants and reports failure modes.
- Simulator and a "Send test email to myself" button let Fahad verify everything BEFORE linking WhatsApp.
- Final manual test script for Fahad: deploy, log in, simulate F1 to F3, review CV and email, send a test to himself, link WhatsApp with a **secondary number**, post in a test group and in "Message yourself", watch it appear.

## PART F. NON-GOALS AND DEFINITION OF DONE

Non-goals: auto-sending without approval, mass auto-apply, LinkedIn automation, WhatsApp replies, paid services, multi-user.

Done when:
- [ ] Every phase gate (G0 to G3) passed and logged on the board.
- [ ] `docker compose up` brings the stack up healthy and deploys as a Portainer repo stack; builds for amd64 and arm64.
- [ ] All fixtures, unit, contract, and E2E tests pass; lint passes.
- [ ] Simulated F1 produces a STRONG card with the exact subject `DevOps Engineer – Application`, a one-page CV that passes the verifier, and a drafted email, viewable on the dashboard at 390 px.
- [ ] Dry-run works; enabling `SEND_ENABLED` sends one real email to Fahad's own address via the Gmail API.
- [ ] Skipped list shows Lahore-onsite jobs with a reason and a working Rescue button.
- [ ] `PRODUCT.md`, `DESIGN.md`, `README.md`, `DEPLOY.md`, `.env.example`, `TROUBLESHOOTING.md` (WhatsApp disconnects, quota 429s, Gmail token expiry, Oracle firewall) exist; no secrets or data in git.

When finished, print a concise summary: what each agent built, which free-tier models and limits were chosen, whether WAHA Core or the fallback listener is used and why, any contract changes made during the build, open TODOs, and the exact list of secrets Fahad must create.