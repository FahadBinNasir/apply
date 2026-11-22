# FIX PROMPT (Round 2a): make it work for real

You are the LEAD agent in the existing repo `apply` (commit f1cec14). A code review found defects that the 54
passing tests do not catch. Read `REVIEW.md` first. Use `probes/probe_pipeline_no_keys.py` and
`probes/probe_rules.py` as failing regression tests BEFORE fixing (TDD): copy them into `tests/regression/` as
pytest tests that currently fail, then make them pass.

Rules: free-only; no MCPs for WhatsApp/LinkedIn/Portainer; keep contracts frozen unless a CONTRACT-CHANGE is
needed (then bump VERSION and write contracts/CHANGELOG.md). Parallel agents with file ownership as before.
Honesty rule: the final report must label every item LIVE-VERIFIED / FAKE-ONLY / NOT-DONE with evidence.
Apply `HARDENING_PROMPT.md` and the merged `profile.seed.yaml` from `hardening-kit` after these P0 fixes
(or merge both prompts' tasks; P0 here comes first).

## P0 tasks (in this order)
1. **LLM failure handling (EXTRACT).** Delete `_heuristic_fallback`. Add `LLMUnavailableError`. Retry 429/5xx with
   exponential backoff + jitter (max 4 tries), then raise. The worker catches it, re-queues the item with
   `next_attempt_at` (persistent queue) and sets inbox status `waiting_for_quota`; no JobCard is created.
   Log provider errors (without keys or message bodies). Put the Gemini key in header `x-goog-api-key`, never in
   the URL. Use the official `google-genai` SDK or the REST API with header auth; verify the current free-tier model
   name via Google docs (Fahad previously used `gemini-3.5-flash-lite` successfully). Enforce JSON via response
   schema where supported. Persist daily usage in `llm_usage`. Test: no keys => no cards, item stays queued.
2. **Docker networking (DEVOPS).** The `whatsapp` service must reach the internet: attach it to `default` (egress)
   and `internal`, or drop `internal: true`. Only `app` and `whatsapp` share `internal` for the webhook.
   The webhook route must not be reachable from the public proxy: serve it on a second internal-only port/app
   (e.g. 8081) or block `/api/intake/*` at the proxy and document it. Remove default dev keys: startup fails if
   `WAHA_API_KEY`, `WEBHOOK_SECRET`, `SESSION_SECRET` are empty in production. Make the WAHA healthcheck use a tool
   present in the image (verify) or drop `service_healthy`. Choose the WAHA image by platform (multi-arch tag or
   documented `WAHA_IMAGE`); verify what the free Core tier supports (groups, channels, media) with a real
   container and document it.
3. **Webhook auth that matches the real sender (INTAKE).** Support WAHA's native HMAC webhook scheme (configure
   `WHATSAPP_HOOK_HMAC_KEY` and verify its header) AND the custom listener's scheme. Reject when no secret is
   configured in production. Add tests using real WAHA-shaped payloads (message, media, group, newsletter).
4. **Read posters (INTAKE + EXTRACT + CORE).** Download media (WAHA media endpoint or listener upload), store it on
   the `app_data` volume, pass `image_bytes`/`mime_type` to the extractor, extract from the image, set
   `from_image=true`, and highlight OCR-derived emails in the UI for confirmation. Test with the MCB, DigiPersona
   and PMTF style posters (generate synthetic poster PNGs if none are available).
5. **Auth hardening (CORE).** Remove the `admin`/`devpassword` fallback and the default session secret: in
   production the app refuses to start without `DASHBOARD_PASSWORD` (plain, hashed in memory) or
   `DASHBOARD_PASSWORD_HASH` (document `$$` escaping for Compose) and a real `SESSION_SECRET`. Enforce CSRF on every
   POST (token in forms/HTMX headers). Lockout keyed by IP from `X-Forwarded-For` when `TRUST_PROXY=true`, and keep
   it from locking out the owner permanently. Session cookie: `Secure`, `HttpOnly`, `SameSite=Lax`, rotating.
6. **Persistence of drafts/CVs/sends (DATA + CORE + CVMAIL).** Save `CVArtifact`, `EmailDraft` and send records via
   repos. CV files live under `/app_data/cvs` (env `DATA_DIR`), never a relative path. The card keeps a stable
   UUID id (do not rename it to a slug). Approve sends the SAVED, possibly user-edited draft and the SAVED CV
   path. Add routes to edit recipient/subject/body, regenerate, and preview CV pages (PNG via PyMuPDF).
7. **Never send without the CV (CVMAIL).** If the CV file is missing, fail the send with a clear error. Validate the
   recipient (regex, no newlines/commas, not a placeholder), reject header injection in subject/recipient.
   Dry-run results are recorded as `dry_run`, not `sent`. Persist daily cap and min gap in the DB (reset by date in
   Asia/Karachi). Add the 14-day same-company/email guard, rechecked right before sending.
8. **Gmail OAuth flow (CVMAIL + CORE).** Implement `/settings/gmail` (start), `/oauth/google/callback`, token
   refresh and encrypted storage in DB, scope `gmail.send` only, state parameter + PKCE, "Send test email to
   myself" button, and a banner when the token is expired. Test against a mocked Google endpoint. Document that
   the consent screen must be "In production".
9. **Profile loader (CORE + RULES).** Load the whole YAML into the `Profile` model: personal (gender, night shift),
   status (semester, expected graduation), links, coursework, matching thresholds, pay and seniority settings,
   all projects. `TODO` values are treated as unset and listed in a Settings warning banner; they never reach a CV.
10. **Rules engine fixes (RULES), with tests for every probe line:**
    - Seniority words (senior, sr., principal, architect, head of, director, lead in title) => SKIPPED(seniority);
      "Manager" in title skipped but "Management Trainee"/MTO allowed.
    - Pay: unpaid/volunteer/commission-only/"stipend only" => SKIPPED(pay); "paid"/"stipend based" fine.
    - Experience from profile: 0-1 normal, 1-2 STRETCH, >=3 SKIPPED.
    - Target-field match must use a curated, specific keyword map (backend, frontend, full-stack, devops, qa, ml,
      data scientist, flutter, mobile, .NET, embedded...), not generic tokens. "Civil Engineer", "Customer Support",
      "Graphic Designer" (match stems: design*), "Accountant" must be SKIPPED(field). Unknown/empty field => STRETCH
      with reason, never STRONG.
    - Scores clamp to 0-100; location unknown => STRETCH with a reason; city from structured fields only.
    - Optimistic extraction defaults removed: unknown stays unknown (`None`), and the rules treat unknown honestly.

## P1 tasks
- Real tests: a `tests/live/` suite (marked `@live`, skipped without keys) that runs Gemini extraction on F1, F2, F3
  and one poster; recorded-response tests for CI. Fixture tests must go through the extractor with recorded LLM
  JSON, not hand-built roles.
- Verifier: check every project id/name, skill, number, date and link in the final CV/email text against the
  profile; forbid an Experience section when `no_formal_employment=true`; forbid "WebForms" claims (WinForms is not
  WebForms). Add an LLM-assisted tailoring step ONLY if it passes this verifier; otherwise keep templates.
- Backoff/queue persistence tests; process restart test; midnight reset test.
- Remove hardcoded email/phone from `provider.py`; build the privacy deny-list from the profile at runtime.
- Packaging: add `trafilatura` (or keep BeautifulSoup but test it), evaluate RenderCV, add PyMuPDF; `.dockerignore`.
- UI evidence: Impeccable critique/audit/adapt/harden/polish run for real; screenshots at 390 px and 1280 px in
  `docs/screens/`; Playwright E2E specs run against the running app.

## Verification you must run and report
1. `pytest -q` on Windows AND in `python:3.12-slim` container.
2. Both probes pass as regression tests.
3. `docker compose up -d` with a dummy env; `docker compose ps` healthy; whatsapp container can reach the internet
   (`docker compose exec whatsapp wget -qO- https://example.com` or equivalent).
4. Simulated end-to-end: F1 text -> STRONG card -> saved draft + CV file on the volume -> edit subject -> dry-run
   approve -> Sent log entry with `dry_run` status.
5. Live: one real Gemini extraction (F1) and one real Gmail test email to myself, if keys are present; otherwise
   mark NOT-DONE.
