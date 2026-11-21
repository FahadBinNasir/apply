# Route Specification (OpenAPI REST & HTMX Partials)

All dashboard endpoints (except `/login` and `/health`) require single-user session cookie authentication.
All mutation endpoints (POST/PUT/DELETE) require valid CSRF token in header or form body.

## 1. Authentication & System
| Method | Path | Auth | Purpose | Response |
|---|---|---|---|---|
| GET | `/health` | Public | Container health check | `{"status": "ok", "db": true, "waha": true}` |
| GET | `/login` | Public | Login page | HTML |
| POST | `/login` | Public | Authenticate password | Redirect to `/` or 401 |
| POST | `/logout` | User | Terminate session | Redirect to `/login` |

## 2. Dashboard & HTMX Views
| Method | Path | Auth | Purpose | Response |
|---|---|---|---|---|
| GET | `/` | User | Main Inbox/Pending dashboard (tabs: Strong, Stretch, Manual, Walk-in) | HTML / partial |
| GET | `/jobs/{job_id}` | User | Job detail page (extracted data, CV preview, email draft) | HTML / partial |
| GET | `/jobs/{job_id}/cv/preview/{page}` | User | Serve rendered PNG preview of CV | `image/png` |
| GET | `/jobs/{job_id}/cv/download` | User | Download tailored CV PDF | `application/pdf` |
| GET | `/jobs/{job_id}/ics` | User | Download walk-in calendar file | `text/calendar` |
| GET | `/sent` | User | Sent log screen with sent history | HTML / partial |
| GET | `/sent/export.csv` | User | Export sent jobs to CSV | `text/csv` |
| GET | `/skipped` | User | Skipped jobs list grouped by reason | HTML / partial |
| GET | `/opportunities` | User | Tech-relevant scholarships, hackathons, courses | HTML / partial |
| GET | `/whatsapp` | User | WhatsApp connection status, QR code, chat allow-list | HTML / partial |
| GET | `/settings` | User | Profile editor, matching rules, send limits, Gmail status | HTML / partial |

## 3. Actions & Operations (HTMX / REST)
| Method | Path | Auth | Purpose | Response |
|---|---|---|---|---|
| POST | `/api/jobs/{job_id}/approve-send` | User | Approve & dispatch Gmail application | HTMX card update / JSON |
| POST | `/api/jobs/{job_id}/save-draft` | User | Save edited draft recipient/subject/body | HTMX card update / JSON |
| POST | `/api/jobs/{job_id}/regenerate-cv` | User | Re-run tailor plan & CV render | HTMX card update / JSON |
| POST | `/api/jobs/{job_id}/reject` | User | Mark job rejected | HTMX card remove / JSON |
| POST | `/api/jobs/{job_id}/snooze` | User | Snooze job for 24h | HTMX card remove / JSON |
| POST | `/api/jobs/{job_id}/mark-manual` | User | Mark applied manually | HTMX card remove / JSON |
| POST | `/api/jobs/{job_id}/rescue` | User | Rescue skipped job into STRETCH | HTMX card update / JSON |
| POST | `/api/settings/save` | User | Save system settings & rules | HTMX toast / JSON |
| POST | `/api/settings/test-email` | User | Send test email to Fahad's own address | JSON |
| GET | `/settings/gmail/connect` | User | Start Google OAuth flow | 302 to Google |
| GET | `/oauth/google/callback` | User | Google OAuth redirect handler | 302 to `/settings` |
| POST | `/api/dev/simulate` | User | Simulate incoming post payload (dev only) | JSON `{job_id, tier}` |

## 4. Internal Ingestion (Protected)
| Method | Path | Auth | Purpose | Response |
|---|---|---|---|---|
| POST | `/api/intake/webhook` | Webhook Secret | Intake webhook from WAHA / fallback listener | `{"status": "queued"}` |
