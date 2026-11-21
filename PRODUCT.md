# Product Specification: WhatsApp Job Agent Dashboard

## 1. Persona & Context
- **Target User:** Fahad Bin Nasir — Final-year (7th semester) Software Engineering student at Bahria University, Karachi.
- **Operating Context:** Triaging high volumes of job/internship posts on mobile (360px - 430px) in short, late-evening bursts, often with imminent application deadlines.
- **Surface Mode:** **Operate** (calm, precise, trustworthy, high-density, high-efficiency personal mission control).
- **Core Principle:** Nothing is ever sent automatically without explicit manual review and approval. Zero hallucination. Zero spam.

## 2. Emotional Tone & Visual Direction
- **Feel:** Quiet professional utility desk. No purple gradients, no startup hype, no marketing fluff, no neon accents.
- **Color Philosophy:** Functional, accessible contrast in both Light and Dark themes (meeting WCAG AA standards, contrast ratio >= 4.5:1).
  - Tiers have both distinct shape/badges and accessible colors (never color-only):
    - `STRONG`: Forest Emerald badge (`#059669` dark / `#065f46` light) with checkmark glyph.
    - `STRETCH`: Amber/Bronze badge (`#d97706` dark / `#92400e` light) with flag glyph.
    - `MANUAL`: Cobalt Blue badge (`#2563eb` dark / `#1e40af` light) with external link glyph.
    - `WALKIN`: Violet badge (`#7c3aed` dark / `#5b21b6` light) with calendar glyph.
    - `SKIPPED`: Slate/Muted badge (`#64748b` dark / `#475569` light).
- **Typography:** System fonts (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`), clear hierarchy, tabular figures for deadlines and dates.

## 3. Screen Structure & Priorities
1. **Inbox / Pending (Primary Screen):**
   - Header with active system state (connection status, quota, pending counter).
   - Segmented control tabs: `Strong`, `Stretch`, `Manual`, `Walk-in` with live badge counts.
   - Filter chips: `New Today`, `Deadline Soon (<3d)`.
   - Card information architecture:
     - Header row: Company, Role, Tier Badge, Deadline urgency badge.
     - Subheader: Work mode, Location (Karachi/Remote), Apply method (Email / WhatsApp / Link).
     - Match breakdown: Green tag for primary field match, key matched skills.
     - Action bar: Primary "Review & Approve" button.
2. **Job Detail Modal / Screen:**
   - Split pane on desktop, sequential card on mobile.
   - Top: Raw WhatsApp message (or zoomable image container if poster).
   - Middle: Extracted fields with OCR-derived emails highlighted in amber with a verification badge. Match reasons and gap disclosures.
   - CV Preview: Crisp visual preview of tailored 1-page CV with one-click download.
   - Email Draft Section:
     - Exact subject line verified.
     - Editable recipient email, subject, and body.
     - Primary Action: Prominent "Approve & Send Email" button with clear confirmation modal.
     - Secondary Actions: Save Draft, Re-generate CV, Reject, Snooze 24h, Mark Applied Manually.
3. **Sent Log:**
   - Table / list of all sent applications with Gmail Message ID, timestamp, and "Export CSV" button.
4. **Skipped List:**
   - Grouped accordion by reason (Location: Lahore onsite; Field: Sales/BD; Expired; Experience >3 yrs).
   - "Rescue to Stretch" button on each card for human override.
5. **Opportunities:**
   - Tech-relevant scholarships, hackathons, and certifications (CERN, QNX, NASA, etc.) with external action links.
6. **WhatsApp Connection:**
   - Live status indicator (Connected / Disconnected).
   - QR code display for scanning with secondary number.
   - Watched group list with last message timestamp.
   - Simulator trigger button for offline testing.
7. **Settings & Health:**
   - Profile editor preview.
   - Matching rules parameters (`comfortable_max_years`, `accepts_night_shift`).
   - Daily send cap (25) & dry-run toggle (`SEND_ENABLED`).
   - Quota usage meter for Gemini & Groq.
