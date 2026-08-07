from datetime import datetime

from sqlalchemy.orm import Session

from app.models.pickup import Pickup
from app.models.supplier import Supplier


class NotFoundError(Exception):
    pass


def create_pickup(db: Session, supplier_id: str) -> Pickup:
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_deleted == False,  # noqa: E712
    ).first()
    if supplier is None:
        raise ValueError("Supplier not found")
    pickup = Pickup(supplier_id=supplier_id, status="confirmed")
    db.add(pickup)
    db.commit()
    db.refresh(pickup)
    return pickup


def get_confirmed_pickups_for_supplier(db: Session, supplier_id: str) -> list[Pickup]:
    return (
        db.query(Pickup)
        .filter(Pickup.supplier_id == supplier_id, Pickup.status == "confirmed")
        .all()
    )


def get_all_confirmed_pickups(db: Session) -> list[dict]:
    pickups = (
        db.query(Pickup)
        .filter(Pickup.status == "confirmed")
        .order_by(Pickup.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "supplier_name": p.supplier.company_name,
            "created_at": p.created_at,
        }
        for p in pickups
    ]


def get_confirmed_pickup_count(db: Session) -> int:
    return db.query(Pickup).filter(Pickup.status == "confirmed").count()


def cancel_pickup(db: Session, pickup_id: str) -> None:
    pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
    if pickup is None:
        raise NotFoundError(f"Pickup {pickup_id!r} not found")
    if pickup.status == "completed":
        raise ValueError("Cannot cancel a completed pickup")
    pickup.status = "cancelled"
    db.commit()
