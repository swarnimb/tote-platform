"""Seed Tote-Ops with realistic synthetic demo data.

DEMO ONLY. This script is not part of the production Tote-Ops application.
Every company, contact, phone number and email below is invented. No data
here corresponds to a real supplier, lead or person.

Coverage targets (see docs/plan.md "Seed data standard"):
  - Gradeouts span 5 calendar years so the dashboard's 5-bar annual revenue
    chart has no empty bar, with the trailing 12 months densely populated so
    the 12-bar monthly chart is also full.
  - Every enum value is represented: pickup status, lead outreach status,
    supplier action stage.
  - Recent activity inside 30 days so "Recent Gradeouts" is never empty.
  - Follow-up table has both overdue and current suppliers.
  - Invoices are computed from the seeded gradeouts, so regenerating an
    invoice in the UI reproduces the stored totals exactly.

Run:  python seed_demo.py
"""

import random
import sys
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.database import _SessionFactory
from app.models.app_settings import AppSettings
from app.models.gradeout import Gradeout
from app.models.invoice import Invoice
from app.models.lead import Lead
from app.models.pickup import Pickup
from app.models.supplier import Supplier

# Deterministic output — reseeding produces the identical dataset, so
# screenshots taken across separate runs stay consistent.
random.seed(20260806)

TODAY = date.today()
HISTORY_START = date(TODAY.year - 4, 1, 1)

ACTION_STAGES = ["followed_up", "responded_no", "pickup_confirmed", "maybe", None]
PICKUP_STATUSES = ["contacted", "confirmed", "completed", "cancelled"]
LEAD_STATUSES = ["research", "contacted", "responded", "not_interested", "active_supplier"]

# (company, city/state, industry, contact, phone area code)
SUPPLIER_SEED = [
    ("Braxton Chemical Works", "1420 Foundry Rd, Akron, OH", "Industrial Chemicals", "Dale Whitmore", "330"),
    ("Kettleridge Coatings", "88 Harbor Ave, Toledo, OH", "Paints & Coatings", "Renata Voss", "419"),
    ("Palmer Agri Supply", "7 County Line Rd, Findlay, OH", "Agricultural Inputs", "Owen Petrie", "567"),
    ("Cortland Food Ingredients", "2200 Millbrook Dr, Cortland, NY", "Food Manufacturing", "Simone Achebe", "607"),
    ("Vandergrift Lubricants", "515 Slate St, Vandergrift, PA", "Lubricants", "Marcus Deel", "724"),
    ("Ashby Polymer Group", "31 Enterprise Way, Erie, PA", "Plastics & Resins", "Priya Raman", "814"),
    ("Halstead Cleaning Products", "904 Trellis Blvd, Muncie, IN", "Cleaning Products", "Trent Kowalczyk", "765"),
    ("Nova Bay Beverages", "610 Dockside Ln, Bay City, MI", "Beverage", "Lucia Ferrante", "989"),
    ("Ridgeway Adhesives", "45 Kiln Ct, Kalamazoo, MI", "Adhesives", "Bernard Osei", "269"),
    ("Sutter Creek Winery Supply", "12 Vineyard Loop, Sandusky, OH", "Beverage", "Hallie Brandt", "419"),
    ("Delmar Water Treatment", "3300 Aqueduct Rd, Wheeling, WV", "Water Treatment", "Curtis Nakamura", "304"),
    ("Pinehurst Ink & Pigment", "77 Pressman St, Fort Wayne, IN", "Printing Inks", "Adaeze Nwosu", "260"),
    ("Corley Metal Finishing", "1801 Anodize Dr, Youngstown, OH", "Metal Finishing", "Frank Delacroix", "330"),
    ("Windham Dairy Cooperative", "4 Creamery Rd, Meadville, PA", "Dairy", "Sonja Lindqvist", "814"),
    ("Bellwether Specialty Fluids", "220 Pumphouse Rd, Lima, OH", "Specialty Chemicals", "Alonzo Rivera", "419"),
    ("Trenholm Soap Works", "58 Lather Ln, South Bend, IN", "Personal Care", "Gita Bhattacharya", "574"),
    ("Grantley Asphalt Emulsions", "990 Quarry Rd, Canton, OH", "Construction Materials", "Wes Hoffmeier", "330"),
    ("Marlowe Pharmaceutical Intermediates", "16 Cleanroom Ct, Columbus, OH", "Pharmaceutical", "Ingrid Sandoval", "614"),
    ("Cape Vincent Fisheries", "3 Netmender Way, Cape Vincent, NY", "Food Manufacturing", "Rory McKellen", "315"),
    ("Fairhaven Pet Nutrition", "1250 Kibble Rd, Elkhart, IN", "Animal Feed", "Damaris Ocampo", "574"),
    ("Sinclair Textile Dyes", "605 Loom St, Greensboro, NC", "Textiles", "Yusuf Karadag", "336"),
    ("Ashland Ridge Ethanol", "8800 Silo Rd, Marion, OH", "Biofuels", "Colette Duprey", "740"),
    ("Herrington Roof Products", "24 Shingle Ave, Zanesville, OH", "Construction Materials", "Nate Abernathy", "740"),
    ("Quarry Point Mineral Slurry", "1 Basin Rd, Cambridge, OH", "Mining", "Beatrix Olander", "740"),
    ("Loman Brothers Rendering", "700 Tallow Rd, Defiance, OH", "Rendering", "Sal Moretti", "419"),
    ("Whitlock Sanitizer Co", "82 Peroxide Pl, Dayton, OH", "Cleaning Products", "Odette Marchand", "937"),
    ("Ferris Point Antifreeze", "410 Glycol Dr, Battle Creek, MI", "Automotive Chemicals", "Hugo Vance", "269"),
    ("Baywood Juice Concentrates", "9 Press Ln, Traverse City, MI", "Beverage", "Marisol Quintero", "231"),
]

WORKING_HOURS = [
    "Mon–Fri 7:00am–3:30pm", "Mon–Fri 6:00am–2:00pm", "Mon–Thu 7:00am–5:00pm",
    "Mon–Fri 8:00am–4:00pm", "Mon–Sat 6:30am–2:30pm", "Mon–Fri 7:30am–4:00pm",
]

SUPPLIER_NOTES = [
    "Dock 3 only — call ahead for a gate code.",
    "Prefers a text the morning of pickup. Slow on email.",
    "Forklift available on site, no need to bring one.",
    "Consolidates totes behind the maintenance shed. Ask for the shift lead.",
    "Wants the BOL emailed to accounting the same day.",
    "Holiday shutdown the last two weeks of December.",
    "Volumes climb in Q2 when the seasonal line runs.",
    "New plant manager as of this spring — rebuilt the relationship.",
    "Will hold totes for up to six weeks if given notice.",
    "Requires a signed safety acknowledgment on every visit.",
]

SUPPLIER_WARNINGS = [
    "Residual caustic in some 275s — rinse before grading.",
    "Hard hat, steel toe and hi-vis required past the guard shack.",
    "Do not enter the north yard without an escort.",
    "Occasional unrinsed totes in this batch — check valves.",
]

LEAD_SEED = [
    ("Northgate Resin Partners", "Cleveland, OH", "Plastics & Resins", "Elena Marchetti", "216"),
    ("Cobalt Line Solvents", "Pittsburgh, PA", "Specialty Chemicals", "Desmond Frye", "412"),
    ("Harrow Valley Cider", "Ann Arbor, MI", "Beverage", "Junia Castellanos", "734"),
    ("Prairie Fork Fertilizer", "Peoria, IL", "Agricultural Inputs", "Ben Oyelaran", "309"),
    ("Sable Creek Detergents", "Louisville, KY", "Cleaning Products", "Nadia Kirilenko", "502"),
    ("Meridian Plating Supply", "Buffalo, NY", "Metal Finishing", "Roland Beaumont", "716"),
    ("Kestrel Labs Reagents", "Indianapolis, IN", "Pharmaceutical", "Farrah Osman", "317"),
    ("Old Mill Flavor House", "Rochester, NY", "Food Manufacturing", "Gunnar Sjoberg", "585"),
    ("Bexley Road Sealants", "Columbus, OH", "Adhesives", "Tamsin Reyes", "614"),
    ("Ironwood Pulp Chemicals", "Green Bay, WI", "Pulp & Paper", "Achille Duval", "920"),
    ("Sandhill Ag Cooperative", "Lansing, MI", "Agricultural Inputs", "Petra Novakova", "517"),
    ("Cormorant Marine Coatings", "Duluth, MN", "Paints & Coatings", "Isaiah Bergstrom", "218"),
    ("Vale Street Brewing", "Cincinnati, OH", "Beverage", "Margit Hollander", "513"),
    ("Halloway Industrial Waxes", "Charleston, WV", "Specialty Chemicals", "Terrence Amadi", "304"),
    ("Fenwick Poultry Nutrition", "Fort Wayne, IN", "Animal Feed", "Dolores Villanueva", "260"),
    ("Rutherford Glycols", "Detroit, MI", "Automotive Chemicals", "Anton Krylov", "313"),
    ("Silverbank Water Systems", "Toledo, OH", "Water Treatment", "Chidinma Eze", "419"),
    ("Ellisport Seafood Processing", "Erie, PA", "Food Manufacturing", "Viktor Lindgren", "814"),
    ("Calder Ridge Biodiesel", "Springfield, OH", "Biofuels", "Rosalind Achterberg", "937"),
    ("Manton Hollow Tanneries", "Grand Rapids, MI", "Leather", "Emeka Balogun", "616"),
    ("Beacon Field Crop Science", "Champaign, IL", "Agricultural Inputs", "Sylvie Rochon", "217"),
    ("Trask & Doyle Solvents", "Akron, OH", "Specialty Chemicals", "Malik Ferreira", "330"),
    ("Winterbourne Cosmetics", "Chicago, IL", "Personal Care", "Anouk Delacroix", "312"),
    ("Pell Junction Rail Services", "Toledo, OH", "Logistics", "Garrett Umeh", "419"),
]

LEAD_NOTES = {
    "research": [
        "Found on the state manufacturers directory. Two plants in region.",
        "LinkedIn shows a plant expansion — likely running more totes now.",
        "Competitor's truck spotted at their dock. Worth a call.",
        "No phone listed yet. Need to find the ops contact.",
    ],
    "contacted": [
        "Left a voicemail with the front desk. Following up in a week.",
        "Emailed the plant manager. No bounce, no reply yet.",
        "Spoke to a receptionist — correct contact is on vacation until next week.",
        "Sent the one-pager and rate sheet. Waiting.",
    ],
    "responded": [
        "Interested but needs sign-off from corporate EHS first.",
        "Asked for references from two current suppliers. Sent them.",
        "Wants to start with a trial pickup of about 30 totes.",
        "Timing is the issue — revisit after their Q4 shutdown.",
    ],
    "not_interested": [
        "Locked into a national contract through next year.",
        "Reconditions totes in house. No outbound volume.",
        "Switched to bulk tanker delivery — no totes at all now.",
        "Corporate policy routes all container disposal through one vendor.",
    ],
    "active_supplier": [
        "Converted after a trial pickup. Now on a regular cycle.",
        "Started small, volume has roughly doubled since.",
        "Referred by an existing supplier. Onboarded quickly.",
    ],
}

VOLUME_BANDS = [
    "~15–20 totes/month", "~25–40 totes/month", "~40–60 totes/month",
    "~60–90 totes/month", "~10 totes/month", "Unknown — needs a site visit",
]

GRADEOUT_NOTES = [
    "Two 275s had cracked cages — pulled to junk.",
    "Clean load, no rinse needed.",
    "Driver noted a partial pallet left behind for next trip.",
    "Three totes still had product residue. Set aside.",
    "Best load from this site so far.",
    "Valves missing on a handful of 330s.",
    "Weather delayed the pickup by a day.",
    None, None, None, None,
]


def _phone(area: str) -> str:
    return f"({area}) {random.randint(200, 989)}-{random.randint(1000, 9999):04d}"


def _email(company: str, person: str) -> str:
    domain = "".join(c for c in company.lower() if c.isalnum())[:18]
    first = person.split()[0].lower()
    return f"{first}@{domain}.com"


def _month_starts(start: date, end: date) -> list[date]:
    """Every month start from `start` through the month containing `end`."""
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(date(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def wipe(db: Session) -> None:
    """Clear demo tables. Order respects foreign keys."""
    for model in (Gradeout, Pickup, Invoice, Lead, Supplier, AppSettings):
        db.query(model).delete()
    db.commit()


def build_suppliers(db: Session) -> list[Supplier]:
    suppliers = []
    for i, (company, location, industry, contact, area) in enumerate(SUPPLIER_SEED):
        # Suppliers onboard progressively over the history window rather than
        # all appearing on day one.
        onboarded = HISTORY_START + timedelta(days=int(i * (len(SUPPLIER_SEED) and 1250 / len(SUPPLIER_SEED))))
        bol_same = i % 3 == 0
        s = Supplier(
            company_name=company,
            location=location,
            contact_name=contact,
            phone=_phone(area),
            email=_email(company, contact),
            bol_email=None if bol_same else f"bol@{''.join(c for c in company.lower() if c.isalnum())[:18]}.com",
            bol_same_as_primary=bol_same,
            industry=industry,
            tote_types="275+330" if i % 4 else "275",
            average_quantity_275=f"{random.randint(8, 55)}",
            average_quantity_330=f"{random.randint(4, 30)}",
            working_hours=random.choice(WORKING_HOURS),
            is_hazmat=i % 6 == 0,
            warnings=random.choice(SUPPLIER_WARNINGS) if i % 4 == 0 else None,
            notes=random.choice(SUPPLIER_NOTES) if i % 2 == 0 else None,
            # Spread across the whole selectable range so the follow-up
            # threshold produces both overdue and current suppliers.
            followup_weeks=random.choice([2, 3, 4, 4, 6, 8, 12]),
            # Two suppliers retired, one soft-deleted — exercises the
            # active-only filter and the deleted-row path.
            is_active=i not in (24, 25),
            is_deleted=i == 27,
            deleted_at=datetime.combine(TODAY - timedelta(days=48), datetime.min.time()) if i == 27 else None,
            created_at=datetime.combine(onboarded, datetime.min.time()),
        )
        db.add(s)
        suppliers.append(s)
    db.commit()
    for s in suppliers:
        db.refresh(s)
    return suppliers


def build_activity(db: Session, suppliers: list[Supplier]) -> None:
    """Create pickups and gradeouts across the full history window."""
    months = _month_starts(HISTORY_START, TODAY)
    recent_cutoff = TODAY - timedelta(days=30)
    dense_cutoff = TODAY - timedelta(days=365)

    for s in suppliers:
        if s.is_deleted:
            continue
        onboard_month = date(s.created_at.year, s.created_at.month, 1)
        # Cadence in weeks — drives how often this supplier produces a load.
        cadence = s.followup_weeks
        cursor = onboard_month + timedelta(days=random.randint(0, 20))
        last_pickup = None

        while cursor <= TODAY:
            if cursor >= HISTORY_START:
                # Older years are sampled more thinly than the trailing 12
                # months, which keeps the annual chart populated while making
                # the monthly chart dense.
                keep = True if cursor >= dense_cutoff else random.random() < 0.55
                if keep and not (s.is_active is False and cursor > TODAY - timedelta(days=120)):
                    created = datetime.combine(cursor, datetime.min.time()) + timedelta(
                        hours=random.randint(7, 16), minutes=random.choice([0, 15, 30, 45])
                    )
                    # Most pickups complete; a minority sit in other states so
                    # every status value is represented in the data.
                    roll = random.random()
                    if roll < 0.80:
                        status = "confirmed"
                    elif roll < 0.90:
                        status = "completed"
                    elif roll < 0.96:
                        status = "contacted"
                    else:
                        status = "cancelled"

                    pickup = Pickup(supplier_id=s.id, status=status, created_at=created)
                    db.add(pickup)
                    db.flush()

                    if status in ("confirmed", "completed"):
                        base_275 = int(s.average_quantity_275)
                        base_330 = int(s.average_quantity_330)
                        w275 = max(0, int(random.gauss(base_275 * 0.62, base_275 * 0.18)))
                        c275 = max(0, int(random.gauss(base_275 * 0.30, base_275 * 0.12)))
                        w330 = max(0, int(random.gauss(base_330 * 0.58, base_330 * 0.18)))
                        c330 = max(0, int(random.gauss(base_330 * 0.30, base_330 * 0.12)))
                        db.add(Gradeout(
                            supplier_id=s.id,
                            pickup_id=pickup.id,
                            date_received=cursor,
                            totes_275_good_washable=w275,
                            totes_275_good_cage=c275,
                            totes_275_total_usable=w275 + c275,
                            totes_330_good_washable=w330,
                            totes_330_good_cage=c330,
                            totes_330_total_usable=w330 + c330,
                            junk=max(0, int(random.gauss(3, 2))),
                            notes=random.choice(GRADEOUT_NOTES),
                            created_at=created + timedelta(hours=random.randint(1, 30)),
                        ))
                        last_pickup = cursor

            cursor += timedelta(weeks=cadence, days=random.randint(-4, 4))

        s.last_pickup_date = last_pickup
        # Action stage reflects where the relationship sits right now.
        if last_pickup and last_pickup >= recent_cutoff:
            s.last_action_stage = "pickup_confirmed"
            s.last_action_date = last_pickup
        elif not s.is_active:
            s.last_action_stage = "responded_no"
            s.last_action_date = TODAY - timedelta(days=random.randint(40, 150))
        else:
            s.last_action_stage = random.choice(ACTION_STAGES)
            s.last_action_date = (
                TODAY - timedelta(days=random.randint(3, 90))
                if s.last_action_stage else None
            )
    db.commit()


def ensure_current_month_activity(db: Session, suppliers: list[Supplier]) -> None:
    """Top up the month in progress.

    The dashboard opens on the current month. Cadence-driven scheduling alone
    can leave the first days of a month nearly empty, which reads as a broken
    app rather than an early month. This adds loads on distinct recent days
    until the month-to-date total looks like a working week.
    """
    month_start = date(TODAY.year, TODAY.month, 1)
    existing = (
        db.query(Gradeout).filter(Gradeout.date_received >= month_start).count()
    )
    target = max(8, min(TODAY.day, 14))
    if existing >= target:
        return

    live = [s for s in suppliers if not s.is_deleted and s.is_active]
    span = (TODAY - month_start).days
    for i in range(target - existing):
        s = live[i % len(live)]
        when = month_start + timedelta(days=(i * 2) % (span + 1))
        created = datetime.combine(when, datetime.min.time()) + timedelta(
            hours=random.randint(7, 16), minutes=random.choice([0, 15, 30, 45])
        )
        pickup = Pickup(supplier_id=s.id, status="confirmed", created_at=created)
        db.add(pickup)
        db.flush()

        base_275 = int(s.average_quantity_275)
        base_330 = int(s.average_quantity_330)
        w275 = max(1, int(random.gauss(base_275 * 0.62, base_275 * 0.18)))
        c275 = max(0, int(random.gauss(base_275 * 0.30, base_275 * 0.12)))
        w330 = max(1, int(random.gauss(base_330 * 0.58, base_330 * 0.18)))
        c330 = max(0, int(random.gauss(base_330 * 0.30, base_330 * 0.12)))
        db.add(Gradeout(
            supplier_id=s.id,
            pickup_id=pickup.id,
            date_received=when,
            totes_275_good_washable=w275,
            totes_275_good_cage=c275,
            totes_275_total_usable=w275 + c275,
            totes_330_good_washable=w330,
            totes_330_good_cage=c330,
            totes_330_total_usable=w330 + c330,
            junk=max(0, int(random.gauss(3, 2))),
            notes=random.choice(GRADEOUT_NOTES),
            created_at=created + timedelta(hours=random.randint(1, 30)),
        ))
        if s.last_pickup_date is None or when > s.last_pickup_date:
            s.last_pickup_date = when
    db.commit()


def force_stage_coverage(db: Session, suppliers: list[Supplier]) -> None:
    """Guarantee at least three suppliers on every action stage."""
    live = [s for s in suppliers if not s.is_deleted]
    for idx, stage in enumerate(ACTION_STAGES):
        for offset in range(3):
            s = live[(idx * 3 + offset) % len(live)]
            s.last_action_stage = stage
            s.last_action_date = (
                TODAY - timedelta(days=random.randint(2, 70)) if stage else None
            )
    db.commit()


def force_pickup_status_coverage(db: Session) -> None:
    """Guarantee every pickup status has rows, even after random sampling."""
    for status in PICKUP_STATUSES:
        if db.query(Pickup).filter(Pickup.status == status).count() >= 3:
            continue
        spares = (
            db.query(Pickup)
            .filter(Pickup.status == "confirmed")
            .order_by(Pickup.created_at)
            .limit(3)
            .all()
        )
        for p in spares:
            if p.gradeout is None:
                p.status = status
    db.commit()


def build_leads(db: Session) -> None:
    per_status = len(LEAD_SEED) // len(LEAD_STATUSES)
    for i, (company, location, industry, contact, area) in enumerate(LEAD_SEED):
        status = LEAD_STATUSES[min(i // per_status, len(LEAD_STATUSES) - 1)]
        # Research leads have not been contacted yet — no contact date.
        last_contact = (
            None if status == "research"
            else TODAY - timedelta(days=random.randint(2, 240))
        )
        db.add(Lead(
            company_name=company,
            location=location,
            industry=industry,
            contact_name=contact,
            contact_phone=_phone(area),
            contact_email=_email(company, contact),
            outreach_status=status,
            last_contact_date=last_contact,
            potential_volume=random.choice(VOLUME_BANDS),
            notes=random.choice(LEAD_NOTES[status]),
            created_at=datetime.combine(
                TODAY - timedelta(days=random.randint(20, 400)), datetime.min.time()
            ),
        ))
    db.commit()


def build_invoices(db: Session) -> None:
    """Invoices are derived from the seeded gradeouts so that regenerating
    one in the UI reproduces the stored totals exactly."""
    months = _month_starts(HISTORY_START, TODAY)
    for month in months:
        nxt = date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
        rows = (
            db.query(Gradeout)
            .filter(Gradeout.date_received >= month, Gradeout.date_received < nxt)
            .all()
        )
        if not rows:
            continue
        # The current month is still in progress — no invoice raised yet.
        if month.year == TODAY.year and month.month == TODAY.month:
            continue

        u275 = sum(g.totes_275_total_usable for g in rows)
        u330 = sum(g.totes_330_total_usable for g in rows)
        generated = datetime.combine(nxt + timedelta(days=random.randint(1, 4)), datetime.min.time())
        # The most recent closed month is generated but not yet sent, so the
        # Sent/Unsent toggle has rows on both sides.
        months_back = (TODAY.year - month.year) * 12 + (TODAY.month - month.month)
        sent = None if months_back <= 1 else generated + timedelta(days=random.randint(0, 3))
        db.add(Invoice(
            month=month,
            gradeout_count=len(rows),
            total_usable_275=u275,
            total_usable_330=u330,
            total_revenue=(u275 + u330) * settings.TOTE_RATE,
            generated_at=generated,
            sent_at=sent,
        ))
    db.commit()


def build_settings(db: Session) -> None:
    db.add(AppSettings(key="growth_target", value="9500.0"))
    db.commit()


def report(db: Session) -> None:
    recent = db.query(Gradeout).filter(
        Gradeout.date_received >= TODAY - timedelta(days=30)
    ).count()
    print("\nSeed complete.")
    print(f"  suppliers        {db.query(Supplier).count():>6}")
    print(f"  pickups          {db.query(Pickup).count():>6}")
    print(f"  gradeouts        {db.query(Gradeout).count():>6}")
    print(f"  leads            {db.query(Lead).count():>6}")
    print(f"  invoices         {db.query(Invoice).count():>6}")
    print(f"  gradeouts <30d   {recent:>6}")

    print("\n  pickups by status:")
    for status in PICKUP_STATUSES:
        print(f"    {status:<14} {db.query(Pickup).filter(Pickup.status == status).count():>5}")
    print("\n  leads by status:")
    for status in LEAD_STATUSES:
        print(f"    {status:<16} {db.query(Lead).filter(Lead.outreach_status == status).count():>5}")
    print("\n  suppliers by action stage:")
    for stage in ACTION_STAGES:
        n = db.query(Supplier).filter(Supplier.last_action_stage == stage).count()
        print(f"    {str(stage):<16} {n:>5}")

    # Fail loudly rather than producing a demo with empty screens.
    problems = []
    if recent == 0:
        problems.append("no gradeouts in the last 30 days — Recent Gradeouts would be empty")
    # The dashboard opens on the current month — a near-empty one reads as broken.
    mtd = db.query(Gradeout).filter(
        Gradeout.date_received >= date(TODAY.year, TODAY.month, 1)
    ).count()
    if mtd < 8:
        problems.append(f"only {mtd} gradeouts month-to-date — dashboard month view would look empty")
    for status in PICKUP_STATUSES:
        if db.query(Pickup).filter(Pickup.status == status).count() == 0:
            problems.append(f"no pickups with status '{status}'")
    for status in LEAD_STATUSES:
        if db.query(Lead).filter(Lead.outreach_status == status).count() == 0:
            problems.append(f"no leads with status '{status}'")
    for year in range(TODAY.year - 4, TODAY.year + 1):
        n = db.query(Gradeout).filter(
            Gradeout.date_received >= date(year, 1, 1),
            Gradeout.date_received <= date(year, 12, 31),
        ).count()
        if n == 0:
            problems.append(f"no gradeouts in {year} — annual revenue chart would have an empty bar")
    for i in range(12):
        m = TODAY.month - i
        y = TODAY.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        n = db.query(Gradeout).filter(
            Gradeout.date_received >= date(y, m, 1),
            Gradeout.date_received < nxt,
        ).count()
        if n == 0:
            problems.append(f"no gradeouts in {y}-{m:02d} — monthly revenue chart would have an empty bar")

    if problems:
        print("\nCOVERAGE FAILURES:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("\nCoverage checks passed — no empty screens.")


def main() -> None:
    db = _SessionFactory()
    try:
        wipe(db)
        suppliers = build_suppliers(db)
        build_activity(db, suppliers)
        ensure_current_month_activity(db, suppliers)
        force_stage_coverage(db, suppliers)
        force_pickup_status_coverage(db)
        build_leads(db)
        build_invoices(db)
        build_settings(db)
        report(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
