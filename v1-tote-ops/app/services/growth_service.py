from datetime import date, timedelta

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
from app.models.gradeout import Gradeout
from app.models.supplier import Supplier


def get_avg_shipments_per_supplier(db: Session) -> float:
    """Average gradeout count per active supplier over the last 12 months.
    Includes active suppliers with zero gradeouts in the period."""
    start = date.today() - timedelta(days=365)
    subq = (
        db.query(
            Supplier.id.label("supplier_id"),
            func.count(Gradeout.id).label("cnt"),
        )
        .outerjoin(
            Gradeout,
            and_(
                Supplier.id == Gradeout.supplier_id,
                Gradeout.date_received >= start,
            ),
        )
        .filter(
            Supplier.is_deleted == False,  # noqa: E712
            Supplier.is_active == True,  # noqa: E712
        )
        .group_by(Supplier.id)
        .subquery()
    )
    avg = db.query(func.avg(subq.c.cnt)).scalar()
    result = round(float(avg), 1) if avg is not None else 0.0
    return result if result > 0 else 4.0


def get_avg_totes_per_shipment(db: Session) -> float:
    """Average total usable totes (275 + 330) per gradeout, all time."""
    avg = db.query(
        func.avg(
            Gradeout.totes_275_total_usable + Gradeout.totes_330_total_usable
        )
    ).scalar()
    return round(float(avg), 1) if avg is not None else 0.0


def get_setting(db: Session, key: str) -> str | None:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else None


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    db.commit()
