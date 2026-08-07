# Design Decisions

## Visual Direction
**Type:** internal
**Feeling:** Calm and focused — a clean operational tool that gets out of the way and lets you work. Nothing decorative, everything purposeful.
**Reference products:** The existing prototype at `C:/Users/bagre/tote-ops/index.html` is the design baseline. Adopt it directly.

## Audience
**Primary user:** Solo contractor, iPad primary, opens the app multiple times daily
**Platform priority:** Mobile-first (iPad). Sidebar collapses to hamburger on screens ≤768px. Desktop is secondary.
**Use frequency:** Daily — animation and motion should be minimal. No distractions.

## Color System
Adopt directly from prototype:

| Role | Color | Usage |
|------|-------|-------|
| Background | #f8f9fb | Page background |
| Surface | #ffffff | Cards, sidebar, modals |
| Border | #e5e7eb | Card borders, dividers |
| Text primary | #111827 | Headings, key data |
| Text secondary | #6b7280 | Labels, metadata |
| Text muted | #9ca3af | Placeholder, hints |
| Primary accent | #2563eb | Buttons, links, active nav, focus rings |
| Primary light | #eff6ff | Active nav background, icon backgrounds |
| Success | #16a34a / bg-green-50 | Revenue, positive trends |
| Warning | #f59e0b / bg-yellow-50 | Follow-up needed, requested status |
| Danger | #dc2626 / bg-red-50 | Overdue, cancelled |
| Info | #2563eb / bg-blue-50 | Scheduled, informational |
| Purple | #7c3aed / bg-purple-50 | Supplier count stats |
| Orange | #f97316 / bg-orange-50 | Pickup/calendar stats |

## Typography
**Font:** Inter (Google Fonts CDN) — weights 300, 400, 500, 600, 700
**Scale:**
- Page titles: text-2xl font-700
- Section titles: text-sm font-600
- Body: text-sm (14px), font-400/500
- Labels: text-xs (12px), font-500
- Stat numbers: text-2xl font-700

## Layout Patterns
- **Sidebar:** Fixed left, 240px wide on desktop. Collapses off-screen on mobile, toggled by hamburger button. Contains logo, nav items, user footer.
- **Nav items:** 8px border radius, 11px/18px padding, blue active state (#eff6ff background, #2563eb text)
- **Main content:** `margin-left: 240px` on desktop, full width on mobile. Max-width 7xl, padding p-6 md:p-8.
- **Dashboard:** 4 stat cards (2-col mobile, 4-col desktop) → 2-col content grid below (xl breakpoint)
- **Data pages:** Filter bar → table with tbl-wrap → pagination footer
- **Modals:** Centered overlay, rounded-2xl (16px), max-w-520px, heavy shadow

## Navigation Items (in order)
1. Dashboard
2. Suppliers
3. Pickups
4. Gradeouts *(new — not in prototype)*
5. Invoices
6. Leads

## Component Style
**Cards / stat cards:**
- bg-white, rounded-xl, border border-gray-200, shadow-sm (or no shadow)
- Icon in colored rounded-lg (w-9 h-9, bg-color-50)
- Trend badge: text-xs rounded-full px-2 py-0.5

**Badges / status pills:**
- rounded-full, text-xs, font-500, px-2 py-0.5
- Colors: badge-blue, badge-yellow, badge-red, badge-green, badge-gray

**Buttons:**
- Primary: bg-blue-600, text-white, rounded-lg, px-18 py-10, hover: bg-blue-700
- Secondary: bg-white, border border-gray-300, text-gray-700, hover: bg-gray-50
- Destructive: bg-red-600 (modals only, delete confirmations)

**Form inputs:**
- border border-gray-300, rounded-lg (8px), padding 11px 13px
- Focus: border-blue-600, box-shadow 0 0 0 3px rgba(37,99,235,0.12)

**Tables:**
- thead: bg-gray-50, text-xs uppercase tracking-wide, text-gray-500
- tbody rows: border-b border-gray-100, hover: bg-gray-50
- Wrapped in overflow-x-auto for iPad

**Modals:**
- rounded-2xl (16px), bg-white, padding 28px 32px
- Overlay: rgba(0,0,0,0.35)
- Max-height 90vh, overflow-y-auto

## Interaction Principles
**Motion:** Subtle only — 0.15s transitions on hover/focus. 0.25s for sidebar slide. No page animations.
**Density:** Moderate — enough breathing room for iPad tap targets (min 44px), not so spacious it wastes screen space.
**Feedback:**
- Form saves: inline success state or toast notification (top-right, auto-dismiss 3s)
- Errors: red border on input + text below field
- Destructive actions: confirmation modal before executing
- PDF extraction: loading state → confirmation screen → save

**Tap targets:** All interactive elements minimum 44px height for iPad compatibility.

## Scrollbar
Thin custom scrollbar: 5px width, #d1d5db thumb, rounded, transparent track.

## What to Avoid
- Dark mode (explicitly out for V1)
- Heavy animations or page transitions
- Charts or graphs (V2)
- Decorative elements that serve no function
- Dense text without visual hierarchy
- Full-page reloads on simple actions where avoidable (use HTMX for small updates)
- Hardcoded colors in HTML — use the defined palette only

## Component Approach
**Primary library:** Tailwind CSS via CDN (no build step)
**Accent libraries:** None — custom components following prototype patterns
**Icons:** Inline SVG (stroke-based, 18-20px, strokeWidth 2) — matching prototype
**Rationale:** The prototype already establishes the full component language. Replicate it in Jinja2 templates exactly. No external component library needed.

## JavaScript
**HTMX:** Yes — loaded via CDN (~14KB). Used for:
- PDF upload → extract → confirm multi-step flow
- Pickup status updates (row updates in place)
- Form submissions with inline success/error feedback

Full page reloads retained for: all navigation, dashboard load, initial page renders.

**Open Questions for @cto:** None — resolved.
