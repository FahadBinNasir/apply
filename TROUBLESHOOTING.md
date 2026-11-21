# Troubleshooting Guide: WhatsApp Job Agent

This guide covers resolution procedures for common operational issues encountered in self-hosted deployment.

---

## 1. Oracle Cloud Firewall Issues (Cannot Access Port 80/443)

### Symptom:
Connection times out when visiting `https://apply.fahadbinnasir.tech` or `http://<IP>:8080`, even though the stack is running in Portainer and the Oracle Cloud Security List has ports 80 and 443 open.

### Root Cause:
Oracle Cloud Ubuntu minimal images enforce pre-installed `iptables` and `ufw` rules inside the OS that drop all incoming TCP traffic except port 22.

### Solution:
SSH into your Oracle Cloud VPS and run:
```bash
# Insert ACCEPT rules ahead of the default REJECT rule (typically at position 6)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT

# Make rules persistent across reboots
sudo netfilter-persistent save
```

---

## 2. WhatsApp Disconnects & Session Invalidation

### Symptom:
The dashboard shows "Disconnected / QR Required", or WAHA logs indicate session logout (`CONFLICT` or `SESSION_CLOSED`).

### Common Causes & Fixes:
1. **Primary Number Risk:** Never use your primary WhatsApp number. Always link with a secondary SIM or virtual WhatsApp number dedicated to listening.
2. **Phone Battery Saver / Sleep:** Ensure the physical phone running WhatsApp does not put the app into battery-saver sleep. Turn off "Battery Optimization" for WhatsApp.
3. **Session Volume Missing:** Ensure the named volume `apply_wa_session` is mounted to `/app/.waha` in WAHA (or `/wa_session` in the fallback listener) so authentication tokens persist across container restarts.
4. **Re-linking:** Navigate to the **WhatsApp** tab on the dashboard, click "Refresh QR", and scan with Linked Devices on your phone.

---

## 3. LLM Free-Tier Rate Limits (HTTP 429 Quota Exhaustion)

### Symptom:
Health status degrades to `waiting_for_quota`, logs show `429 Too Many Requests` from Google AI Studio.

### Automated Recovery:
1. **Zero Message Loss:** The queue worker automatically nacks the item with exponential backoff (starting at 30 seconds). Unprocessed messages remain safely persisted in the SQLite queue table.
2. **Groq Automatic Fallback:** If `GROQ_API_KEY` is configured, the system automatically redirects extraction requests to Groq free tier (`llama-3.3-70b-versatile`).
3. **PreFilter Protection:** The pre-filter drops non-job noise (convocations, surveys, ads) before any API call is made, conserving quota for real job postings.
4. **Content-Hash Caching:** Duplicate postings from multiple groups are served directly from the SHA256 cache with zero LLM API cost.

---

## 4. Gmail API OAuth Token Expiry (7-Day Consent Expiration)

### Symptom:
After exactly 7 days of operation, email sending fails with `invalid_grant` or `Token has been expired or revoked`.

### Root Cause:
When a Google Cloud OAuth Consent Screen is in "Testing" status, refresh tokens automatically expire after 7 days.

### Solution:
1. Open [Google Cloud Console](https://console.cloud.google.com/) > **APIs & Services > OAuth consent screen**.
2. Click **Publish App** to switch publishing status from "Testing" to **In production**.
   - Note: Because you are only using this application personally for your own email account, you do NOT need to submit for Google verification. Simply click Publish.
3. Once in production, user refresh tokens remain valid indefinitely until revoked.
4. Go to `https://apply.fahadbinnasir.tech/settings`, click **Authorize / Reconnect Gmail Account**, and re-authenticate.

---

## 5. Mobile Inline PDF Preview Issues

### Symptom:
Mobile browsers (Safari on iOS, Chrome on Android) download the CV instead of showing an inline preview.

### Solution:
Mobile browsers have limited inline PDF iframe rendering capabilities. The WhatsApp Job Agent addresses this by rendering PNG page previews (`.preview.png`) alongside the PDF. In the job detail view, the page preview is rendered directly as an image, with an explicit "Download PDF" button for ATS transmission.
