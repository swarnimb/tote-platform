# Skill: @ui-tote-ops

## Purpose
Builds Jinja2 HTML templates for the Tote-Ops project — applying the established design system, layout patterns, and HTMX interaction conventions exactly as defined in `docs/design-decisions.md`. Produces production-ready templates that are iPad-first (768px), visually consistent, and tap-target compliant.

---

## Pre-conditions

Before executing:
1. Read `docs/design-decisions.md` — it is the single source of truth for colors, typography, layout, and component patterns. Do not deviate from it.
2. Confirm `app/templates/base.html` exists — all page templates extend it. If it doesn't exist, Task 6 must be completed first.
3. Read any existing templates in the same section (e.g., other templates in `suppliers/`) for consistency before writing new ones.

---

## Process

### Building a page template

1. Start with `{% extends "base.html" %}` and `{% block content %}`
2. Apply the layout pattern for the page type (data page, dashboard, form — see Patterns below)
3. Use only colors from the defined palette — no inline hex values that aren't in the system
4. All interactive elements must meet the 44px minimum tap target
5. Wrap tables in `overflow-x-auto` for iPad horizontal scroll
6. Test the mental model at 768px before declaring done: does the layout compress gracefully? Are tap targets reachable?

### Building an HTMX partial (fragment)

1. The partial must be a standalone HTML fragment — no `<html>`, `<head>`, or `{% extends %}` tags
2. The partial replaces only the target element — size it accordingly (a table row, a modal, a toast)
3. For toasts: use `hx-swap-oob="beforeend:#toast-container"` to inject into the toast container
4. Keep the partial under 50 lines

---

## Design System Reference

### Colors (from design-decisions.md — use these exactly)

| Role | Hex | Use |
|---|---|---|
| Background | `#f8f9fb` | `<body>` and page bg |
| Surface | `#ffffff` | Cards, sidebar, modals |
| Border | `#e5e7eb` | Card borders, dividers, table separators |
| Text primary | `#111827` | Headings, key data |
| Text secondary | `#6b7280` | Labels, metadata |
| Text muted | `#9ca3af` | Placeholder, hints |
| Primary accent | `#2563eb` | Buttons, links, active nav, focus rings |
| Primary light | `#eff6ff` | Active nav bg, icon bg |
| Success | `#16a34a` / `bg-green-50` | Revenue, positive |
| Warning | `#f59e0b` / `bg-yellow-50` | Follow-up needed, requested |
| Danger | `#dc2626` / `bg-red-50` | Overdue, cancelled |
| Info | `#2563eb` / `bg-blue-50` | Scheduled, informational |

### Typography

- Font: Inter (loaded via CDN in `base.html` — do not re-declare)
- Page titles: `text-2xl font-bold` (`font-weight: 700`)
- Section titles: `text-sm font-semibold`
- Body: `text-sm` (14px), `font-normal` or `font-medium`
- Labels: `text-xs font-medium`
- Stat numbers: `text-2xl font-bold`

### Buttons

```html
<!-- Primary -->
<button class="..." style="background:#2563eb; color:#fff; border-radius:8px; padding:10px 18px; font-size:14px; font-weight:500; min-height:44px; border:none; cursor:pointer;">
  Label
</button>

<!-- Secondary -->
<button class="..." style="background:#fff; border:1px solid #d1d5db; color:#374151; border-radius:8px; padding:10px 18px; font-size:14px; font-weight:500; min-height:44px; cursor:pointer;">
  Label
</button>
```

### Form inputs

```html
<input type="text" style="border:1px solid #d1d5db; border-radius:8px; padding:11px 13px; font-size:14px; color:#111827; width:100%; outline:none;" />
```
Focus state (via CSS class):
```css
border-color: #2563eb;
box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
```

### Status badges

```html
<span style="background:#eff6ff; color:#2563eb; border-radius:9999px; font-size:12px; font-weight:500; padding:2px 8px;">Scheduled</span>
<span style="background:#fef9c3; color:#ca8a04; border-radius:9999px; font-size:12px; font-weight:500; padding:2px 8px;">Requested</span>
<span style="background:#fef2f2; color:#dc2626; border-radius:9999px; font-size:12px; font-weight:500; padding:2px 8px;">Cancelled</span>
<span style="background:#f0fdf4; color:#16a34a; border-radius:9999px; font-size:12px; font-weight:500; padding:2px 8px;">Completed</span>
<span style="background:#f3f4f6; color:#6b7280; border-radius:9999px; font-size:12px; font-weight:500; padding:2px 8px;">Inactive</span>
```

### Cards / stat cards

```html
<div style="background:#fff; border:1px solid #e5e7eb; border-radius:12px; padding:20px 24px;">
  <!-- content -->
</div>
```

Stat card with icon:
```html
<div style="display:flex; align-items:flex-start; gap:16px;">
  <div style="background:#eff6ff; border-radius:8px; width:36px; height:36px; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
    <!-- SVG icon, stroke:#2563eb, 18x18 -->
  </div>
  <div>
    <p style="font-size:12px; font-weight:500; color:#6b7280; margin:0 0 4px;">Label</p>
    <p style="font-size:24px; font-weight:700; color:#111827; margin:0;">42</p>
  </div>
</div>
```

### Tables

```html
<div style="overflow-x:auto;">
  <table style="width:100%; border-collapse:collapse;">
    <thead>
      <tr style="background:#f9fafb; border-bottom:1px solid #e5e7eb;">
        <th style="text-align:left; font-size:11px; font-weight:600; color:#6b7280; text-transform:uppercase; letter-spacing:0.05em; padding:10px 16px;">Column</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid #f3f4f6;" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background=''">
        <td style="font-size:14px; color:#111827; padding:14px 16px;">Value</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Modals

```html
<!-- Overlay -->
<div style="position:fixed; inset:0; background:rgba(0,0,0,0.35); z-index:60; display:flex; align-items:center; justify-content:center;">
  <!-- Dialog -->
  <div style="background:#fff; border-radius:16px; padding:28px 32px; width:100%; max-width:520px; max-height:90vh; overflow-y:auto; margin:0 16px;">
    <!-- content -->
  </div>
</div>
```

### Layout Patterns

**Data page (list view):**
```
Page title + primary action button
Filter bar (search input + filter selects)
Table (overflow-x-auto wrapper)
```

**Dashboard:**
```
Page title
4 stat cards (2-col mobile / 4-col desktop)
2-col content grid at xl breakpoint (upcoming pickups + needs follow-up)
```

**Form page:**
```
Page title + back link
Form card (bg-white, border, rounded-xl)
Field groups with labels
Action buttons (primary + cancel)
```

---

## Icons

Inline SVG only. Stroke-based, 18–20px, `stroke-width="2"`, `fill="none"`. Match color to context (`stroke="currentColor"` for inheriting from parent, or explicit hex for icon-in-badge).

Never use icon fonts or external icon libraries.

---

## HTMX Patterns

| Interaction | Attributes |
|---|---|
| Supplier search | `hx-get="/suppliers/search" hx-trigger="input changed delay:300ms" hx-target="#supplier-list" hx-swap="innerHTML"` |
| Pickup status update | `hx-patch="/pickups/{id}/status" hx-target="#pickup-row-{id}" hx-swap="outerHTML"` |
| Lead status update | `hx-patch="/leads/{id}/status" hx-target="#lead-row-{id}" hx-swap="outerHTML"` |
| Toast (from server) | Server returns fragment with `hx-swap-oob="beforeend:#toast-container"` |

HTMX partial routes return HTML fragments — no full page wrapper.

---

## iPad Checklist (before marking any UI task complete)

- [ ] All buttons and tap targets ≥ 44px height
- [ ] Tables wrapped in `overflow-x-auto`
- [ ] No fixed-width elements that overflow at 768px
- [ ] Sidebar collapses on mobile (inherited from `base.html`)
- [ ] Form inputs have visible focus states
- [ ] Modals scroll if content overflows (`overflow-y:auto`, `max-height:90vh`)

---

## Tools

Uses Playwright MCP (`mcp__playwright__browser_resize`, `mcp__playwright__browser_take_screenshot`) to verify layouts at 768px viewport when `## Tests` for the task specifies "Manual: verify at 768px viewport."

---

## When To Invoke

- Any task creating or modifying Jinja2 templates
- Any task that includes `**Specialist:** @ui-tote-ops` in `docs/plan.md`

---

## When Not To Invoke

- Non-template work (services, models, routes, tests) — use `@dev`
- PDF extraction logic — use `@pdf-extractor` (V2 only)
- Architecture decisions about template structure — use `@cto`

---

## Closing

After completing template work: confirm files written, confirm 768px viewport check passed (or note if manual check is pending), and note any design system deviations made (with rationale).
