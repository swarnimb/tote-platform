from datetime import date

from sqlalchemy.orm import Session

from app.models.lead import Lead, LEAD_STATUS


class NotFoundError(Exception):
    pass


def get_leads(db: Session, status: str | None = None) -> list:
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.outreach_status == status)
    return query.order_by(Lead.created_at.desc()).all()


def create_lead(db: Session, data: dict) -> Lead:
    company_name = (data.get("company_name") or "").strip()
    if not company_name:
        raise ValueError("company_name is required")

    last_contact_date = None
    if data.get("last_contact_date"):
        try:
            last_contact_date = date.fromisoformat(data["last_contact_date"])
        except ValueError:
            raise ValueError("last_contact_date must be a valid date (YYYY-MM-DD)")

    lead = Lead(
        company_name=company_name,
        location=data.get("location") or None,
        industry=data.get("industry") or None,
        contact_name=data.get("contact_name") or None,
        contact_phone=data.get("contact_phone") or None,
        contact_email=data.get("contact_email") or None,
        outreach_status=data.get("outreach_status") or "research",
        last_contact_date=last_contact_date,
        potential_volume=data.get("potential_volume") or None,
        notes=data.get("notes") or None,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def update_lead(db: Session, lead_id: str, data: dict) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise NotFoundError(f"Lead {lead_id} not found")

    if "company_name" in data:
        company_name = (data["company_name"] or "").strip()
        if not company_name:
            raise ValueError("company_name is required")
        lead.company_name = company_name

    for field in ("location", "industry", "contact_name", "contact_phone",
                  "contact_email", "potential_volume", "notes"):
        if field in data:
            setattr(lead, field, data[field] or None)

    if data.get("last_contact_date"):
        try:
            lead.last_contact_date = date.fromisoformat(data["last_contact_date"])
        except ValueError:
            raise ValueError("last_contact_date must be a valid date (YYYY-MM-DD)")
    elif "last_contact_date" in data and not data["last_contact_date"]:
        lead.last_contact_date = None

    db.commit()
    db.refresh(lead)
    return lead


def update_lead_status(db: Session, lead_id: str, status: str) -> tuple:
    if status not in LEAD_STATUS:
        raise ValueError(
            f"Invalid status '{status}'. Valid: {', '.join(LEAD_STATUS)}"
        )
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise NotFoundError(f"Lead {lead_id} not found")
    lead.outreach_status = status
    db.commit()
    db.refresh(lead)
    return lead, (status == "active_supplier")


def delete_lead(db: Session, lead_id: str) -> None:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise NotFoundError(f"Lead {lead_id} not found")
    db.delete(lead)
    db.commit()


def build_supplier_prefill(lead: Lead) -> dict:
    return {
        "company_name": lead.company_name or "",
        "location": lead.location or "",
        "contact_name": lead.contact_name or "",
        "phone": lead.contact_phone or "",
        "email": lead.contact_email or "",
    }
