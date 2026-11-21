# Events and Error Codes Specification

## Pipeline Events
- `message.received`: Raw message received from WhatsApp intake.
- `message.filtered_noise`: Message dropped by pre-filter without LLM call.
- `message.extracted`: Message parsed into roles by Extractor.
- `role.evaluated`: Role scored and categorized into Tier by RulesEngine & Scorer.
- `role.deduplicated`: Role matched against existing job and merged.
- `card.created`: New JobCard created and placed in Inbox.
- `cv.generated`: Tailored CV PDF and PNG previews rendered.
- `draft.created`: Email draft constructed with exact subject.
- `job.approved`: User approved application email and CV.
- `job.sent`: Email successfully dispatched through Gmail API.
- `job.failed`: Dispatch or generation encountered an error.
- `job.rescued`: Job rescued from SKIPPED into STRETCH.

## Error Codes
| Code | Category | Meaning | Recovery Action |
|---|---|---|---|
| `AUTH_INVALID_CREDENTIALS` | Auth | Wrong password on login | Show error, record failed attempt in lockout counter |
| `AUTH_LOCKED_OUT` | Auth | Too many failed logins (5 attempts) | 15 minute cooldown |
| `INTAKE_INVALID_SECRET` | Intake | Webhook request missing or invalid `x-webhook-secret` | 403 Forbidden |
| `INTAKE_REPLAY_DETECTED` | Intake | Timestamp drift > 300s or duplicated HMAC nonce | 400 Bad Request |
| `LLM_QUOTA_EXHAUSTED` | LLM | 429 quota error on all providers (Gemini & Groq) | Retain in queue, display "waiting for quota" banner |
| `LLM_INVALID_JSON` | LLM | LLM response failed schema validation after retry | Fallback to heuristic parser, log raw response |
| `SSRF_BLOCKED_HOST` | Fetch | URL points to localhost or private subnet | Reject fetch, log security alert |
| `LINK_LOGIN_WALL` | Fetch | LinkedIn / walled garden page | Set tier to MANUAL with note |
| `CV_FABRICATION_DETECTED` | CV | Tailored CV contains skills or facts not in profile | Retry tailoring with strict prompt; fallback to baseline CV |
| `GMAIL_TOKEN_EXPIRED` | Mail | Google refresh token revoked or expired (7-day personal consent) | Display warning banner on UI, prompt reconnect |
| `DAILY_CAP_REACHED` | Mail | Daily send limit exceeded (default 25) | Block dispatch until next calendar day |
