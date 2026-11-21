# Design System: WhatsApp Job Agent (Operate Desk)

## 1. Principles
- **Density with Clarity:** Compact, information-rich cards without visual clutter.
- **Accessible-First:** Every tier has a distinctive icon/shape and label, never relying on color alone. Contrast ratio >= 4.5:1 on text, >= 3:1 on controls (WCAG AA).
- **Zero-Build Vanilla CSS:** Pure CSS variables, modern flexbox and grid layouts, lightweight HTMX transitions. No React, no Tailwind CDN, no external font CDNs.

## 2. Design Tokens & Color Palettes

### Dark Theme (Default)
```css
:root[data-theme="dark"] {
  --bg-canvas: #090d16;
  --bg-surface: #111827;
  --bg-elevated: #1e293b;
  --bg-subtle: #273549;

  --border-subtle: #1f2937;
  --border-muted: #374151;
  --border-focus: #3b82f6;

  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;

  --tier-strong-bg: #064e3b;
  --tier-strong-fg: #6ee7b7;
  --tier-strong-border: #059669;

  --tier-stretch-bg: #451a03;
  --tier-stretch-fg: #fcd34d;
  --tier-stretch-border: #d97706;

  --tier-manual-bg: #1e3a8a;
  --tier-manual-fg: #93c5fd;
  --tier-manual-border: #3b82f6;

  --tier-walkin-bg: #3b0764;
  --tier-walkin-fg: #d8b4fe;
  --tier-walkin-border: #8b5cf6;

  --tier-skipped-bg: #1e293b;
  --tier-skipped-fg: #94a3b8;
  --tier-skipped-border: #475569;

  --action-primary-bg: #2563eb;
  --action-primary-fg: #ffffff;
  --action-primary-hover: #1d4ed8;

  --action-danger-bg: #7f1d1d;
  --action-danger-fg: #fca5a5;
  --action-danger-hover: #991b1b;
}
```

### Light Theme
```css
:root[data-theme="light"] {
  --bg-canvas: #f8fafc;
  --bg-surface: #ffffff;
  --bg-elevated: #f1f5f9;
  --bg-subtle: #e2e8f0;

  --border-subtle: #e2e8f0;
  --border-muted: #cbd5e1;
  --border-focus: #2563eb;

  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #64748b;

  --tier-strong-bg: #ecfdf5;
  --tier-strong-fg: #065f46;
  --tier-strong-border: #34d399;

  --tier-stretch-bg: #fffbeb;
  --tier-stretch-fg: #92400e;
  --tier-stretch-border: #f59e0b;

  --tier-manual-bg: #eff6ff;
  --tier-manual-fg: #1e40af;
  --tier-manual-border: #60a5fa;

  --tier-walkin-bg: #f5f3ff;
  --tier-walkin-fg: #5b21b6;
  --tier-walkin-border: #a78bfa;

  --tier-skipped-bg: #f1f5f9;
  --tier-skipped-fg: #475569;
  --tier-skipped-border: #cbd5e1;

  --action-primary-bg: #2563eb;
  --action-primary-fg: #ffffff;
  --action-primary-hover: #1d4ed8;

  --action-danger-bg: #fee2e2;
  --action-danger-fg: #991b1b;
  --action-danger-hover: #fecaca;
}
```

## 3. Spacing Grid & Touch Targets
- **Spatial Grid:** 4px / 8px / 16px / 24px / 32px rhythm.
- **Minimum Touch Target:** 44px x 44px for all mobile interactive elements (buttons, segmented tab items, filter chips).
- **Responsive Breakpoints:**
  - Phone: `360px` to `640px` (single column vertical stack).
  - Tablet / Desktop: `641px` to `1280px` (two-column split pane for job detail & CV review).

## 4. Key Components
1. **Top Navigation Bar:**
   - App title, live connection status dot, theme toggle button (moon/sun), logout link.
2. **Segmented Tabs:**
   - Pill-shaped container with active background highlight and count badge.
3. **Job Card:**
   - Visual card with subtle border, left-edge colored indicator according to tier, bold role title, company name, deadline chip, matches list, and action buttons.
4. **Detail Drawer / Split Pane:**
   - Left side: Post source & OCR details.
   - Right side: Tailored email draft with live editable fields, verified subject bar, and primary "Approve & Send" button.
