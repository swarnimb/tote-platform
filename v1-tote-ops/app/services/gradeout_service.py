from datetime import date

from sqlalchemy.orm import Session

from app.models.gradeout import Gradeout
from app.models.pickup import Pickup
from app.models.supplier import Supplier
from app.services.pickup_service import get_confirmed_pickups_for_supplier


class NotFoundError(Exception):
    pass


def get_gradeouts(
    db: Session,
    supplier_id: str | None = None,
    month: date | None = None,
) -> list:
    query = db.query(Gradeout)
    if supplier_id:
        query = query.filter(Gradeout.supplier_id == supplier_id)
    if month:
        next_month = (
            date(month.year + 1, 1, 1)
            if month.month == 12
            else date(month.year, month.month + 1, 1)
        )
        query = query.filter(
            Gradeout.date_received >= month,
            Gradeout.date_received < next_month,
        )
    return query.order_by(Gradeout.date_received.desc()).all()


def get_gradeout_by_id(db: Session, gradeout_id: str) -> Gradeout:
    gradeout = db.query(Gradeout).filter(Gradeout.id == gradeout_id).first()
    if not gradeout:
        raise NotFoundError(f"Gradeout {gradeout_id} not found")
    return gradeout


def _parse_non_negative_int(data: dict, key: str) -> int:
    try:
        val = int(data.get(key) or 0)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a non-negative integer")
    if val < 0:
        raise ValueError(f"{key} must be >= 0")
    return val


def _parse_gradeout_fields(data: dict) -> dict:
    """Parse and validate tote counts from form data. Returns field dict."""
    gw_275 = _parse_non_negative_int(data, "totes_275_good_washable")
    gc_275 = _parse_non_negative_int(data, "totes_275_good_cage")
    gw_330 = _parse_non_negative_int(data, "totes_330_good_washable")
    gc_330 = _parse_non_negative_int(data, "totes_330_good_cage")
    junk = _parse_non_negative_int(data, "junk")
    return {
        "totes_275_good_washable": gw_275,
        "totes_275_good_cage": gc_275,
        "totes_275_total_usable": gw_275 + gc_275,
        "totes_330_good_washable": gw_330,
        "totes_330_good_cage": gc_330,
        "totes_330_total_usable": gw_330 + gc_330,
        "junk": junk,
    }


def _complete_pickup(db: Session, pickup_id: str) -> None:
    """Mark a pickup as completed. Does NOT commit — caller commits."""
    pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
    if pickup is None:
        raise ValueError("Pickup not found")
    pickup.status = "completed"


def create_gradeout(db: Session, data: dict) -> Gradeout:
    supplier_id = (data.get("supplier_id") or "").strip()
    if not supplier_id:
        raise ValueError("supplier_id is required")

    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.is_deleted == False)  # noqa: E712
        .first()
    )
    if not supplier:
        raise ValueError("Supplier not found")

    try:
        date_received = date.fromisoformat(data["date_received"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("date_received is required (YYYY-MM-DD)")

    pickup_id = (data.get("pickup_id") or "").strip() or None
    if not pickup_id:
        confirmed = get_confirmed_pickups_for_supplier(db, supplier_id)
        if len(confirmed) == 1:
            pickup_id = str(confirmed[0].id)
        elif len(confirmed) >= 2:
            raise ValueError("Select which pickup this gradeout belongs to")

    fields = _parse_gradeout_fields(data)
    gradeout = Gradeout(
        supplier_id=supplier_id,
        date_received=date_received,
        notes=data.get("notes") or None,
        **fields,
    )
    if pickup_id:
        gradeout.pickup_id = pickup_id
        _complete_pickup(db, pickup_id)
    db.add(gradeout)
    supplier.last_pickup_date = date_received
    supplier.last_action_stage = None
    supplier.last_action_date = None
    db.commit()
    db.refresh(gradeout)
    return gradeout


def update_gradeout(db: Session, gradeout_id: str, data: dict) -> Gradeout:
    gradeout = get_gradeout_by_id(db, gradeout_id)

    supplier_id = (data.get("supplier_id") or "").strip()
    if not supplier_id:
        raise ValueError("supplier_id is required")
    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.is_deleted == False)  # noqa: E712
        .first()
    )
    if not supplier:
        raise ValueError("Supplier not found")

    try:
        date_received = date.fromisoformat(data["date_received"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("date_received is required (YYYY-MM-DD)")

    fields = _parse_gradeout_fields(data)
    gradeout.supplier_id = supplier_id
    gradeout.date_received = date_received
    gradeout.notes = data.get("notes") or None
    for key, val in fields.items():
        setattr(gradeout, key, val)

    db.commit()
    db.refresh(gradeout)
    return gradeout


def delete_gradeout(db: Session, gradeout_id: str) -> None:
    gradeout = db.query(Gradeout).filter(Gradeout.id == gradeout_id).first()
    if not gradeout:
        raise NotFoundError(f"Gradeout {gradeout_id} not found")
    db.delete(gradeout)
    db.commit()
