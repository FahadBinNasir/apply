# Deployment Guide: WhatsApp Job Agent

This guide covers deploying the WhatsApp Job Agent to your Oracle Cloud VPS (Ubuntu, Portainer) at **`apply.fahadbinnasir.tech`**.

---

## 1. Prerequisites & Secrets Preparation

Before deploying, generate your secrets (all 100% free):

### A. Dashboard Password Hash
Choose a secure password and generate its bcrypt hash:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YourSecurePasswordHere', bcrypt.gensalt()).decode())"
```

### B. Session & Webhook Secrets
Generate two 32-byte hex secrets:
```bash
python -c "import secrets; print('SESSION_SECRET=' + secrets.token_hex(32)); print('WEBHOOK_SECRET=' + secrets.token_hex(32))"
```

### C. Fernet Encryption Key
Generate a 32-byte url-safe base64 key for encrypting OAuth tokens:
```bash
python -c "from cryptography.fernet import Fernet; print('FERNET_KEY=' + Fernet.generate_key().decode())"
```

### D. Google Gemini API Key
Get your free API key at [Google AI Studio](https://aistudio.google.com/). Set `GEMINI_API_KEY`.

### E. Google Cloud OAuth Client (Gmail API)
1. Go to [Google Cloud Console](https://console.cloud.google.com/) > Select or create project.
2. Enable **Gmail API** in APIs & Services.
3. OAuth Consent Screen: Set user type to External. Enter app name and support email. Add scope `https://www.googleapis.com/auth/gmail.send`. Set publishing status to **In production** (for personal use, prevents the 7-day token expiration).
4. Credentials > Create Credentials > OAuth client ID > Web application.
   - Authorized redirect URIs: `https://apply.fahadbinnasir.tech/oauth/google/callback`
5. Note down `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

---

## 2. Oracle Cloud VPS & Firewall Setup

### Step A: Oracle Cloud Console Security List
1. In Oracle Cloud Console, navigate to **Networking > Virtual Cloud Networks**.
2. Select your VCN > Click **Security Lists** > Select Default Security List.
3. Click **Add Ingress Rules**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: `TCP`
   - Destination Port Range: `80,443`
   - Description: `HTTP and HTTPS Ingress`

### Step B: Oracle Ubuntu Host Firewall (CRITICAL)
Oracle Cloud Ubuntu images block incoming ports 80/443 by default in the OS iptables rules even after opening them in the cloud console. SSH into your VPS and run:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## 3. DNS Configuration

In your DNS provider (Cloudflare / Namecheap / Route 53):
- Type: `A`
- Name: `apply` (for `apply.fahadbinnasir.tech`)
- Content: `<Your_Oracle_VPS_Public_IP>`
- TTL: Auto

---

## 4. Portainer Stack Deployment

1. Log into your Portainer dashboard at **`https://portainer.fahadbinnasir.tech`**.
2. Go to **Stacks > Add stack**.
3. Select **Repository**:
   - Name: `apply`
   - Repository URL: `https://github.com/your-username/apply`
   - Repository reference: `refs/heads/main`
   - Compose path: `docker-compose.yml`
   - If repository is private: Toggle **Authentication** and enter your GitHub Personal Access Token (PAT).
4. Under **Environment variables**, click **Add environment variable** and supply:
   - `DASHBOARD_PASSWORD_HASH`: *(from Step 1A)*
   - `SESSION_SECRET`: *(from Step 1B)*
   - `WEBHOOK_SECRET`: *(from Step 1B)*
   - `FERNET_KEY`: *(from Step 1C)*
   - `GEMINI_API_KEY`: *(from Step 1D)*
   - `GOOGLE_CLIENT_ID`: *(from Step 1E)*
   - `GOOGLE_CLIENT_SECRET`: *(from Step 1E)*
   - `SEND_ENABLED`: `false` (keep false initially for dry-run testing)
   - `WAHA_API_KEY`: *(random secure string)*
5. Click **Deploy the stack**.

---

## 5. Reverse Proxy Configuration

The `app` container binds locally on `127.0.0.1:8080` so it does not conflict with existing services.

### If using Nginx Proxy Manager:
- Domain Names: `apply.fahadbinnasir.tech`
- Scheme: `http`
- Forward Hostname / IP: `127.0.0.1` (or `apply_app` if on shared docker network)
- Forward Port: `8080`
- SSL: Request new Let's Encrypt certificate, Force SSL.

### If using Caddy (Standalone):
Deploy stack with profile `with-proxy` in Portainer:
```bash
docker compose --profile with-proxy up -d
```

---

## 6. Pairing WhatsApp & First Test

1. Visit **`https://apply.fahadbinnasir.tech`**.
2. Log in using your dashboard password.
3. Go to the **WhatsApp** page:
   - Scan the QR code using a **secondary WhatsApp number** (Settings > Linked Devices > Link a Device).
   - Once linked, status will display **Connected & Listening**.
4. Test Ingestion:
   - Use "Message yourself" on WhatsApp or post in a test group:
     `We are hiring a DevOps Engineer at Paysys Labs Karachi. Send CV to hiring@paysyslabs.com with subject "DevOps Engineer – Application"`
   - Watch the card appear on your dashboard in the **Strong** tab within seconds!
5. When satisfied, visit **Settings**, connect Gmail, toggle `SEND_ENABLED=true`, and click "Send test email to myself".

---

## 7. Backup and Restore

### Create a Backup:
```bash
./scripts/backup.sh
# or on Windows PowerShell:
.\scripts\backup.ps1
```

### Restore from Backup:
```bash
./scripts/restore.sh backups/backup_YYYYMMDD_HHMMSS
# or on Windows PowerShell:
.\scripts\restore.ps1 -BackupPath backups\backup_YYYYMMDD_HHMMSS
```
