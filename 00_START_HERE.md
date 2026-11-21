# Build Kit: WhatsApp Job Agent (100% free stack)

Files
- MASTER_PROMPT.md  -> paste into Antigravity as the main instruction (it tells the agent to read the other files)
- profile.seed.yaml -> your data from Fahad_CV_v3.pdf. Fill the TODO lines. Put it in the repo root.
- fixtures.md       -> real posts + the tier each MUST get. The agent turns these into tests.

Order
1. Create an empty GitHub repo, open it in Antigravity, drop these 3 files + Fahad_CV_v3.pdf in the root.
2. Paste MASTER_PROMPT.md. Let it build, run tests, and design the UI with /impeccable:impeccable.
3. Push to GitHub.
4. Portainer (portainer.fahadbinnasir.tech) -> Stacks -> Add stack -> Repository -> your repo -> set env vars -> Deploy.
5. DNS: A record apply.fahadbinnasir.tech -> Oracle IP. Open ports 80/443 in the Oracle security list AND the VPS firewall.
6. Open the dashboard -> WhatsApp page -> scan QR with a SECONDARY number -> test with "Message yourself".

Secrets you must create (all free)
- GEMINI_API_KEY (Google AI Studio) and optionally GROQ_API_KEY (console.groq.com)
- Google Cloud OAuth client (Gmail API, scope gmail.send) - reuse your existing project
- DASHBOARD_PASSWORD, SESSION_SECRET, WEBHOOK_SECRET, WAHA_API_KEY (any long random strings)
