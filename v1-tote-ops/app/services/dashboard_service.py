import calendar
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.gradeout import Gradeout
from app.models.pickup import Pickup
from app.models.supplier import Supplier


def get_monthly_stats(db: Session, year: int, month: int) -> dict:
    _, last_day = calendar.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)
    row = db.query(
        func.coalesce(func.sum(Gradeout.totes_275_total_usable), 0),
        func.coalesce(func.sum(Gradeout.totes_330_total_usable), 0),
        func.count(Gradeout.id),
    ).filter(
        Gradeout.date_received >= start,
        Gradeout.date_received <= end,
    ).one()
    total = int(row[0]) + int(row[1])
    return {
        "total_usable_totes": total,
        "revenue": float(total * settings.TOTE_RATE),
        "gradeout_count": int(row[2]),
    }


def get_yearly_stats(db: Session, year: int) -> dict:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    row = db.query(
        func.coalesce(func.sum(Gradeout.totes_275_total_usable), 0),
        func.coalesce(func.sum(Gradeout.totes_330_total_usable), 0),
        func.count(Gradeout.id),
    ).filter(
        Gradeout.date_received >= start,
        Gradeout.date_received <= end,
    ).one()
    total = int(row[0]) + int(row[1])
    return {
        "total_usable_totes": total,
        "revenue": float(total * settings.TOTE_RATE),
        "gradeout_count": int(row[2]),
    }


def get_active_supplier_count(db: Session) -> int:
    return db.query(Supplier).filter(Supplier.is_deleted == False).count()  # noqa: E712


def get_recent_gradeouts(db: Session) -> list:
    cutoff = date.today() - timedelta(days=30)
    return (
        db.query(Gradeout)
        .join(Supplier)
        .filter(Gradeout.date_received >= cutoff)
        .order_by(Gradeout.date_received.desc(), Gradeout.created_at.desc())
        .all()
    )


def get_followup_suppliers(db: Session) -> list:
    last_subq = (
        db.query(
            Gradeout.supplier_id,
            func.max(Gradeout.date_received).label("last_gradeout"),
        )
        .group_by(Gradeout.supplier_id)
        .subquery()
    )
    avg_subq = (
        db.query(
            Gradeout.supplier_id,
            func.coalesce(func.avg(Gradeout.totes_275_good_washable), 0).label("avg_275_washable"),
            func.coalesce(func.avg(Gradeout.totes_275_good_cage), 0).label("avg_275_cage"),
            func.coalesce(func.avg(Gradeout.totes_330_good_washable), 0).label("avg_330_washable"),
            func.coalesce(func.avg(Gradeout.totes_330_good_cage), 0).label("avg_330_cage"),
        )
        .group_by(Gradeout.supplier_id)
        .subquery()
    )
    days_since = func.current_date() - last_subq.c.last_gradeout
    threshold = Supplier.followup_weeks * 7
    days_past = func.coalesce(days_since - threshold, 9999)
    rows = (
        db.query(
            Supplier,
            last_subq.c.last_gradeout,
            avg_subq.c.avg_275_washable,
            avg_subq.c.avg_275_cage,
            avg_subq.c.avg_330_washable,
            avg_subq.c.avg_330_cage,
        )
        .outerjoin(last_subq, Supplier.id == last_subq.c.supplier_id)
        .outerjoin(avg_subq, Supplier.id == avg_subq.c.supplier_id)
        .filter(Supplier.is_deleted == False)  # noqa: E712
        .filter(Supplier.is_active == True)  # noqa: E712
        .filter(
            (last_subq.c.last_gradeout == None) | (days_since >= threshold)  # noqa: E711
        )
        .order_by(days_past.desc())
        .all()
    )
    return [
        {
            "supplier": s,
            "last_gradeout": last,
            "avg_275_washable": round(float(w275)) if w275 is not None else None,
            "avg_275_cage": round(float(c275)) if c275 is not None else None,
            "avg_330_washable": round(float(w330)) if w330 is not None else None,
            "avg_330_cage": round(float(c330)) if c330 is not None else None,
        }
        for s, last, w275, c275, w330, c330 in rows
    ]


def get_confirmed_pickup_count(db: Session) -> int:
    return db.query(Pickup).filter(Pickup.status == "confirmed").count()


def get_all_confirmed_pickups(db: Session) -> list[dict]:
    pickups = (
        db.query(Pickup)
        .filter(Pickup.status == "confirmed")
        .order_by(Pickup.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(p.id),
            "supplier_name": p.supplier.company_name,
            "created_at": p.created_at,
        }
        for p in pickups
    ]


def get_revenue_chart_data(db: Session) -> dict:
    rows = db.query(
        Gradeout.date_received,
        Gradeout.totes_275_total_usable,
        Gradeout.totes_330_total_usable,
    ).all()

    today = date.today()
    monthly: dict[tuple, float] = {}
    for i in range(11, -1, -1):
        m = today.month - i
        y = today.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        monthly[(y, m)] = 0.0

    annual: dict[int, float] = {today.year - i: 0.0 for i in range(4, -1, -1)}

    for received, u275, u330 in rows:
        rev = float((int(u275 or 0) + int(u330 or 0)) * settings.TOTE_RATE)
        key = (received.year, received.month)
        if key in monthly:
            monthly[key] += rev
        if received.year in annual:
            annual[received.year] += rev

    return {
        "monthly": [
            {"label": date(y, m, 1).strftime("%b %Y"), "revenue": round(rev, 2)}
            for (y, m), rev in monthly.items()
        ],
        "annual": [
            {"label": str(y), "revenue": round(rev, 2)}
            for y, rev in annual.items()
        ],
    }
