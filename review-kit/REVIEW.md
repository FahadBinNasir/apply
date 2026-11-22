# Code review of apply-main (repo commit f1cec14)

Method: unzipped the repo, ran the 54 tests (all pass), read the production modules, and ran two probes
(`probes/`). Severity: P0 = will break or harm in real use, P1 = serious, P2 = should fix.

## Verdict
The skeleton, contracts, DB models, dashboard templates and Docker files are real work. But the tests pass
mostly because they feed hand-built data into the rules engine, or use fakes. The parts that touch the real
world (WhatsApp, posters, Gemini, CV storage, Gmail) are broken or missing. Do NOT deploy and link WhatsApp yet.

## P0 (breaks or harms)
1. **Fake jobs when the AI is unavailable.** `app/llm/provider.py::_heuristic_fallback` returns a made-up
   "Software Engineer at Tech Company, jobs@techcompany.com" when keys are missing OR when Gemini/Groq fail
   (quota 429, network). Errors are swallowed (`except: pass`). Proven: probe_pipeline_no_keys.py turns a birthday
   message into a STRONG card (score 100), generates a CV, and then dedupes every real post against it.
   Fix: raise `LLMUnavailable`; the worker re-queues with backoff; nothing is created from a failure.
2. **Whatsapp container has no internet.** In `docker-compose.yml` the `whatsapp` service is only on the network
   `internal`, which is declared `internal: true`. WAHA cannot reach WhatsApp servers, so it can never link.
3. **WAHA webhooks will be rejected.** The app requires custom headers `x-webhook-signature` +
   `x-webhook-timestamp` (HMAC of `timestamp.body`). WAHA sends neither (it has its own HMAC header scheme).
   If `WEBHOOK_SECRET` is empty, verification is skipped entirely (open endpoint). Only the custom Node listener
   (`whatsapp/index.js`) signs correctly, but compose defaults to WAHA.
4. **Posters are never read.** `PipelineEngine.process_message` calls `extractor.extract(msg)` without image
   bytes; `waha.py` stores the media URL but nothing downloads it. Poster-only posts (MCB, DigiPersona, PMTF)
   are invisible.
5. **Login backdoor + forgeable sessions.** If `DASHBOARD_PASSWORD_HASH` is empty, the passwords `admin` and
   `devpassword` log in. `SESSION_SECRET` defaults to a public string. In production with a missing env var this
   exposes the dashboard (which can send email as you). Fail startup instead.
6. **No Gmail OAuth flow exists.** No `/settings/gmail` or `/oauth/google/callback` routes. The sender expects a
   pre-encrypted refresh token in env `GMAIL_REFRESH_TOKEN_ENC` that you have no way to produce. Real sending
   cannot work as built.
7. **Applications can go out without the CV.** `sender.py` attaches the PDF only `if pdf_path.exists()`, else it
   silently sends the email anyway (body says "CV attached"). The approve route also guesses the path
   (`app_data/cvs/Fahad_Bin_Nasir_CV_<company>_<title>.pdf` with raw spaces) instead of using the file the builder
   made. The builder writes to a relative `app_data/cvs` inside the container, not the `/app_data` volume, so CVs
   are lost on redeploy.
8. **Drafts, CVs and sends are never saved.** `process_message` builds `cv` and `draft`, then drops them (tables
   exist but nothing writes them). Approve re-generates a fresh draft, so edits in the UI cannot be sent, and the
   Sent log has no data source. Also `card.id` is overwritten after creation with a company/title slug, which
   collides for two roles at one company.
9. **Gemini API key in the URL query string.** httpx logs request URLs at INFO, so the key leaks into logs. Use
   the `x-goog-api-key` header.

## P1 (serious)
10. **Rules engine is too loose.** Probe_rules.py shows STRONG for: "Senior Software Engineer", a volunteer/unpaid
    dev role, "Civil Engineer", "Customer Support Executive", "Graphic Designer" (avoid-list `\bdesign\b` does not
    match "designer"). Target-field matching uses generic tokens ("engineering", "software", "data") found in the
    title. Missing: seniority rule, pay rule, experience rule thresholds from the profile (3 years currently
    STRETCH, wanted SKIPPED), scores exceed 100, empty `field` defaults to "software engineering".
11. **Profile loader ignores the profile.** `app/main.py::load_profile` hardcodes `semester=7` and experience
    thresholds (2/3/3), drops `gender`, `accepts_night_shift`, `expected_graduation`, links, courses, projects'
    extra fields. Night-shift and gender rules therefore never see your answers.
12. **Optimistic extraction defaults.** `is_job` defaults True, `fresh_grad_ok` True, `night_shift` False,
    `field` "software engineering". Missing info should become unknown, not a pass.
13. **No retry/backoff/rate-limit, quota counters in memory only.** The report claimed exponential backoff with
    jitter; the code has none. `_sent_today` in the mailer never resets at midnight and resets on restart; no
    14-day repeat-application guard exists.
14. **Anti-fabrication verifier is mostly cosmetic.** It checks project ids and a few hardcoded phrases only. The
    CV and email are template-built (no LLM tailoring), so "AI-tailored" is not implemented; summary and bullets
    are not verified against the profile.
15. **CSRF is never enforced** (`verify_csrf_token` imported, never used; templates have no tokens). Login lockout
    is per client IP in memory; behind a reverse proxy all users share the proxy IP (the owner can be locked out).
16. **Production safety:** compose defaults `WAHA_API_KEY` to `dev_waha_api_key_12345`; WAHA healthcheck uses
    `curl` that the image may not contain (then `app` never starts because of `service_healthy`); default image
    `waha:arm` breaks on x86; webhook route is served by the same public app (should be internal-only).
17. **Tests overstate coverage.** The "all fixtures" test builds `ExtractedRole` objects by hand, so it tests only
    the rules, not extraction. Nothing tests real Gemini, poster reading, link fetch, OAuth, or a full send.

## P2
- Uses BeautifulSoup in `linkfetch.py` instead of trafilatura; ReportLab instead of RenderCV; no PNG preview
  (PyMuPDF), no Playwright tests, no screenshots or Impeccable audit evidence in the repo.
- `CORSMiddleware` imported unused; hardcoded personal email/phone strings inside `provider.py` (privacy guard)
  should come from the profile.
- `profile.seed.yaml` in the repo is still the first version (TODO graduation, missing projects/coursework).

## What is genuinely good
Contract-first structure; capture-first inbox design; SQLite models incl. WAL and encryption helper; SSRF-aware
link fetcher; clean route structure behind `require_auth`; non-root Dockerfile; localhost-only port binding;
dry-run default (`SEND_ENABLED=false`); backup/restore scripts; separation of rules engine as pure code.

## How to reproduce my findings
`python probes/probe_pipeline_no_keys.py` (run from repo root with no API keys) and `python probes/probe_rules.py`.
Turn both into permanent regression tests.
