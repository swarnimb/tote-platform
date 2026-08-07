import urllib.parse
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.supplier import Supplier

FOLLOWUP_WEEKS_DEFAULT = 4


class NotFoundError(Exception):
    pass


def get_suppliers(
    db: Session,
    search: str | None = None,
    action_stage: str | None = None,
    active_only: bool = True,
) -> list:
    query = db.query(Supplier).filter(Supplier.is_deleted == False)  # noqa: E712

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Supplier.company_name.ilike(pattern) | Supplier.location.ilike(pattern)
        )

    if action_stage:
        query = query.filter(Supplier.last_action_stage == action_stage)

    if active_only:
        query = query.filter(Supplier.is_active == True)  # noqa: E712

    return query.order_by(Supplier.company_name).all()


def create_supplier(db: Session, data: dict) -> Supplier:
    if not data.get("company_name", "").strip():
        raise ValueError("company_name is required")
    if not data.get("location", "").strip():
        raise ValueError("location is required")

    try:
        followup_weeks = max(1, min(10, int(data.get("followup_weeks") or FOLLOWUP_WEEKS_DEFAULT)))
    except (TypeError, ValueError):
        followup_weeks = FOLLOWUP_WEEKS_DEFAULT

    supplier = Supplier(
        company_name=data["company_name"].strip(),
        location=data["location"].strip(),
        contact_name=data.get("contact_name") or None,
        phone=data.get("phone") or None,
        email=data.get("email") or None,
        bol_email=data.get("bol_email") or None,
        bol_same_as_primary=data.get("bol_same_as_primary") == "on",
        industry=data.get("industry") or None,
        tote_types=data.get("tote_types") or None,
        average_quantity_275=data.get("average_quantity_275") or None,
        average_quantity_330=data.get("average_quantity_330") or None,
        working_hours=data.get("working_hours") or None,
        is_hazmat=data.get("is_hazmat") == "on",
        followup_weeks=followup_weeks,
        warnings=data.get("warnings") or None,
        notes=data.get("notes") or None,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(db: Session, supplier_id: str, data: dict) -> Supplier:
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_deleted == False,  # noqa: E712
    ).first()
    if not supplier:
        raise NotFoundError(f"Supplier {supplier_id} not found")

    if "company_name" in data and not data["company_name"].strip():
        raise ValueError("company_name is required")
    if "location" in data and not data["location"].strip():
        raise ValueError("location is required")

    text_fields = [
        "company_name", "location", "contact_name", "phone", "email",
        "bol_email", "industry", "tote_types", "average_quantity_275",
        "average_quantity_330", "working_hours", "warnings", "notes",
    ]
    for field in text_fields:
        if field in data:
            val = data[field].strip() if data[field] else ""
            setattr(supplier, field, val or None)

    supplier.bol_same_as_primary = data.get("bol_same_as_primary") == "on"
    supplier.is_hazmat = data.get("is_hazmat") == "on"
    if "followup_weeks" in data:
        try:
            supplier.followup_weeks = max(1, min(10, int(data["followup_weeks"] or FOLLOWUP_WEEKS_DEFAULT)))
        except (TypeError, ValueError):
            pass
    db.commit()
    db.refresh(supplier)
    return supplier


def soft_delete_supplier(db: Session, supplier_id: str) -> None:
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_deleted == False,  # noqa: E712
    ).first()
    if not supplier:
        raise NotFoundError(f"Supplier {supplier_id} not found")

    supplier.is_deleted = True
    supplier.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


def get_supplier_by_id(db: Session, supplier_id: str) -> Supplier:
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_deleted == False,  # noqa: E712
    ).first()
    if not supplier:
        raise NotFoundError(f"Supplier {supplier_id} not found")
    return supplier


_FOLLOWUP_MESSAGE = (
    "Hey, hope you're doing well. Wanted to check in to see if you're in need of a pickup "
    "of your empty totes. Let us know, we can get them picked up ASAP."
)


def build_followup_mailto(supplier: Supplier, days_since: int | None) -> str:
    body = f"Hi,\n\n{_FOLLOWUP_MESSAGE}\n\nThanks"
    to = supplier.email or ""
    subject = urllib.parse.quote(f"IBC Tote Pickup — {supplier.company_name}", safe="")
    encoded_body = urllib.parse.quote(body, safe="")
    return f"mailto:{to}?subject={subject}&body={encoded_body}"


def build_followup_sms(supplier: Supplier) -> str:
    phone = (supplier.phone or "").strip()
    encoded_body = urllib.parse.quote(_FOLLOWUP_MESSAGE, safe="")
    return f"sms:{phone}?&body={encoded_body}"


def set_supplier_action_stage(db: Session, supplier_id: str, stage: str | None) -> None:
    supplier = get_supplier_by_id(db, supplier_id)
    if not stage:
        supplier.last_action_stage = None
        supplier.last_action_date = None
    else:
        supplier.last_action_stage = stage
        supplier.last_action_date = date.today()
    db.commit()


def set_supplier_followup_weeks(db: Session, supplier_id: str, weeks: int) -> None:
    supplier = get_supplier_by_id(db, supplier_id)
    supplier.followup_weeks = max(1, min(10, weeks))
    db.commit()


def toggle_supplier_active(db: Session, supplier_id: str) -> bool:
    """Toggle is_active. Returns the new state."""
    supplier = get_supplier_by_id(db, supplier_id)
    supplier.is_active = not supplier.is_active
    db.commit()
    return supplier.is_active


def get_supplier_gradeout_stats(db: Session, supplier_ids: list) -> dict:
    from app.models.gradeout import Gradeout
    if not supplier_ids:
        return {}
    rows = (
        db.query(
            Gradeout.supplier_id,
            func.coalesce(func.avg(Gradeout.totes_275_good_washable), 0).label("avg_275_washable"),
            func.coalesce(func.avg(Gradeout.totes_275_good_cage), 0).label("avg_275_cage"),
            func.coalesce(func.avg(Gradeout.totes_330_good_washable), 0).label("avg_330_washable"),
            func.coalesce(func.avg(Gradeout.totes_330_good_cage), 0).label("avg_330_cage"),
            func.max(Gradeout.date_received).label("last_gradeout"),
        )
        .filter(Gradeout.supplier_id.in_(supplier_ids))
        .group_by(Gradeout.supplier_id)
        .all()
    )
    return {
        r.supplier_id: {
            "avg_275_washable": round(float(r.avg_275_washable)),
            "avg_275_cage": round(float(r.avg_275_cage)),
            "avg_330_washable": round(float(r.avg_330_washable)),
            "avg_330_cage": round(float(r.avg_330_cage)),
            "last_gradeout": r.last_gradeout,
        }
        for r in rows
    }


def get_supplier_quality_rate(db: Session, supplier_id: str) -> float | None:
    from app.models.gradeout import Gradeout
    row = db.query(
        func.coalesce(func.sum(Gradeout.totes_275_total_usable), 0),
        func.coalesce(func.sum(Gradeout.totes_330_total_usable), 0),
        func.coalesce(func.sum(Gradeout.junk), 0),
    ).filter(Gradeout.supplier_id == supplier_id).one()
    total_usable = int(row[0]) + int(row[1])
    total_junk = int(row[2])
    if total_usable + total_junk == 0:
        return None
    return round(total_usable / (total_usable + total_junk) * 100, 1)
