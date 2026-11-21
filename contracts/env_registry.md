# Environment Variable Registry & Port Mapping

## Port Mapping
| Service | Internal Port | Exposed Port (Host) | Default Host Binding | Profile / Purpose |
|---|---|---|---|---|
| `app` | 8080 | 8080 | `127.0.0.1:${APP_PORT:-8080}` | Main app container |
| `whatsapp` (WAHA) | 3000 | 3000 | Internal network only | Intake service |
| `proxy` (Caddy) | 80, 443 | 80, 443 | `0.0.0.0:80`, `0.0.0.0:443` | `with-proxy` profile only |

## Environment Variables
| Variable | Required | Default | Owner | Purpose |
|---|---|---|---|---|
| `APP_PORT` | No | `8080` | DEVOPS | Port for web application |
| `APP_ENV` | No | `production` | CORE | `development` or `production` |
| `DASHBOARD_PASSWORD_HASH` | Yes | - | CORE | Argon2/Bcrypt hash of single-user password |
| `SESSION_SECRET` | Yes | - | CORE | Secret key for signing session cookies |
| `WEBHOOK_SECRET` | Yes | - | INTAKE | Shared secret between whatsapp and app containers |
| `FERNET_KEY` | Yes | - | CVMAIL | 32-byte url-safe base64 key for encrypting OAuth tokens |
| `GEMINI_API_KEY` | Yes | - | EXTRACT | Google AI Studio free-tier API key |
| `GEMINI_MODEL_FAST` | No | `gemini-2.5-flash` | EXTRACT | Fast multimodal model for posters and extraction |
| `GEMINI_MODEL_SMART` | No | `gemini-2.5-flash` | EXTRACT | High-fidelity model for complex cases |
| `GROQ_API_KEY` | No | - | EXTRACT | Groq free-tier API key for fallback |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | EXTRACT | Groq fallback model name |
| `GOOGLE_CLIENT_ID` | Yes | - | CVMAIL | Google Cloud OAuth Client ID for Gmail API |
| `GOOGLE_CLIENT_SECRET` | Yes | - | CVMAIL | Google Cloud OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | No | `https://apply.fahadbinnasir.tech/oauth/google/callback` | CVMAIL | OAuth callback URL |
| `MAIL_BACKEND` | No | `gmail_api` | CVMAIL | `gmail_api` or `smtp` |
| `SMTP_HOST` | No | `smtp.gmail.com` | CVMAIL | SMTP host if fallback used |
| `SMTP_PORT` | No | `587` | CVMAIL | SMTP port |
| `SMTP_USER` | No | - | CVMAIL | Gmail address for SMTP |
| `SMTP_PASS` | No | - | CVMAIL | 16-character Gmail App Password |
| `SEND_ENABLED` | No | `false` | CVMAIL | Dry-run protection flag (must be true to send) |
| `DAILY_SEND_CAP` | No | `25` | CVMAIL | Maximum emails sent per 24 hours |
| `MIN_GAP_SECONDS` | No | `60` | CVMAIL | Minimum delay between consecutive sends |
| `WAHA_API_KEY` | Yes | - | INTAKE | API key securing WAHA internal endpoints |
| `WAHA_BASE_URL` | No | `http://whatsapp:3000` | INTAKE | Internal URL of WAHA service |
| `ENABLE_SIMULATOR` | No | `false` | CORE | Enables `POST /api/dev/simulate` in prod |
| `NOW_OVERRIDE` | No | - | RULES | Clock override ISO timestamp for deterministic tests |
