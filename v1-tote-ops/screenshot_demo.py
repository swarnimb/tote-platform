"""Capture every Tote-Ops screen for the v1 (before) asset set.

DEMO ONLY. Not part of the production Tote-Ops application.

Assumes the app is already running (see docs/plan.md) and that seed_demo.py
has been run against the same database.

Writes to ../assets/v1-tote-ops/<width>/<name>.png

Run:  python screenshot_demo.py
"""

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from sqlalchemy import func

from app.config import settings
from app.database import _SessionFactory
from app.models.gradeout import Gradeout
from app.models.invoice import Invoice

BASE_URL = os.environ.get("DEMO_BASE_URL", "http://127.0.0.1:8011")
OUT_ROOT = Path(__file__).resolve().parent.parent / "assets" / "v1-tote-ops"

# The app is iPad-primary, so 768 is the design target and 1280 shows the
# desktop layout. Both widths are captured for every screen.
VIEWPORTS = {"desktop-1280": 1280, "ipad-768": 768}


def pick_targets() -> dict:
    """Choose concrete record IDs so the detail screens show a busy record
    rather than an arbitrary one."""
    db = _SessionFactory()
    try:
        busiest = (
            db.query(Gradeout.supplier_id, func.count(Gradeout.id).label("n"))
            .group_by(Gradeout.supplier_id)
            .order_by(func.count(Gradeout.id).desc())
            .first()
        )
        latest_gradeout = (
            db.query(Gradeout)
            .order_by(Gradeout.date_received.desc(), Gradeout.created_at.desc())
            .first()
        )
        latest_invoice = db.query(Invoice).order_by(Invoice.month.desc()).first()
        if not (busiest and latest_gradeout and latest_invoice):
            sys.exit("Database looks unseeded — run seed_demo.py first.")
        return {
            "supplier_id": busiest[0],
            "gradeout_id": latest_gradeout.id,
            "invoice_month": latest_invoice.month.strftime("%Y-%m"),
        }
    finally:
        db.close()


def routes(t: dict) -> list[tuple[str, str]]:
    """(filename, path) pairs, in the order a visitor would walk the app."""
    return [
        ("01-dashboard", "/?period=month"),
        ("01b-dashboard-year", "/?period=year"),
        ("02-suppliers-list", "/suppliers"),
        ("03-supplier-detail", f"/suppliers/{t['supplier_id']}"),
        ("04-suppliers-filtered-pickup-confirmed", "/suppliers?action_stage=pickup_confirmed"),
        ("05-gradeouts-list", "/gradeouts"),
        ("06-gradeout-new", "/gradeouts/new"),
        ("07-gradeout-edit", f"/gradeouts/{t['gradeout_id']}/edit"),
        ("08-leads-list", "/leads"),
        ("09-leads-filtered-contacted", "/leads?status=contacted"),
        ("10-invoices-list", "/invoices"),
        ("11-growth-calculator", "/growth"),
    ]


# The dashboard ships with its three panels collapsed. Screenshotting it
# as-is produces three empty cards, so they are opened before capture.
DASHBOARD_PANELS = ["#chart-toggle-btn", "#gradeouts-toggle-btn", "#followup-toggle-btn"]


def _expand_dashboard(page) -> None:
    for selector in DASHBOARD_PANELS:
        page.click(selector)
        page.wait_for_timeout(250)
    # Chart.js draws into a canvas only once its panel is visible.
    page.wait_for_timeout(1200)


def capture(page, label: str, path: str, out_dir: Path, after_load=None) -> None:
    resp = page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    if resp is None or resp.status >= 400:
        status = resp.status if resp else "no response"
        raise RuntimeError(f"{path} returned {status} — refusing to ship a broken screenshot")
    page.wait_for_timeout(600)
    if after_load:
        after_load(page)
    target = out_dir / f"{label}.png"
    page.screenshot(path=str(target), full_page=True)
    print(f"  {target.relative_to(OUT_ROOT.parent.parent)}")


def main() -> None:
    targets = pick_targets()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp_name, width in VIEWPORTS.items():
            out_dir = OUT_ROOT / vp_name
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n{vp_name}:")
            ctx = browser.new_context(
                viewport={"width": width, "height": 1000},
                device_scale_factor=2,
            )
            page = ctx.new_page()

            # Logged-out login screen, captured before authenticating.
            capture(page, "00-login", "/login", out_dir)

            page.goto(f"{BASE_URL}/login")
            page.fill('input[name="password"]', settings.APP_PASSWORD)
            page.click('button[type="submit"], input[type="submit"]')
            page.wait_for_url(f"{BASE_URL}/", timeout=15000)

            for label, path in routes(targets):
                hook = _expand_dashboard if label.startswith("01") else None
                capture(page, label, path, out_dir, after_load=hook)

            ctx.close()
        browser.close()
    print(f"\nWrote screenshots to {OUT_ROOT}")


if __name__ == "__main__":
    main()
