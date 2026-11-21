# Status: CVMAIL Agent

## Progress
- `AntiFabricationVerifier` implemented in `app/cv/verifier.py`:
  - Enforces 100% adherence to `profile.seed.yaml`.
  - Rejects invented project IDs, fabricated employer claims, false WebForms production claims.
  - Ensures truthful representation of 7th semester status.
- `ProductionCVBuilder` implemented in `app/cv/builder.py`:
  - ATS-friendly single-page PDF generator using ReportLab.
  - Per-domain project ordering based on tags (AI/Data leads with ChurnVision & Exam Cheating Detector; DevOps/Backend leads with FYP; Mobile leads with Flutter suite; IoT with IoT Inventory; .NET stresses C#, SQL, REST).
  - Clean typography and 0.5-inch margins.
- `ProductionMailer` & drafting implemented in `app/mail/`:
  - Drafts 90 to 130 words, polite, references 2 real matches, CV attached, name/phone/links, 7th semester.
  - Subject = `exact_subject` verbatim when present (including en dashes).
  - Gmail API dispatch (`gmail.send`) + SMTP fallback with App Password.
  - `SEND_ENABLED=false` dry-run mode by default.
  - Daily cap (default 25) and min gap (default 60s) enforced.
- `ProductionCalendarExporter` implemented in `app/calendar/exporter.py`:
  - RFC 5545 `.ics` generator for walk-in interview roles.
- `generate_wa_apply_link` helper in `app/mail/whatsapp_helper.py`.
- Unit tests written and green: `tests/cvmail/test_cvmail.py` (4 passed).
- Requirements listed in `requirements/cvmail.txt`.
- Env vars declared in `contracts/env/cvmail.yaml`.

## Interfaces Implemented
- `CVBuilder` (from `contracts.protocols`)
- `Mailer` (from `contracts.protocols`)
- `CalendarExporter` (from `contracts.protocols`)

## Open Issues / Notes
- None. Ready for integration.
