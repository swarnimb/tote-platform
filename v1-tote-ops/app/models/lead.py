import uuid

from sqlalchemy import Column, Date, Enum, Index, String, Text, DateTime
from sqlalchemy.sql import func

from app.models.base import Base

LEAD_STATUS = ("research", "contacted", "responded", "not_interested", "active_supplier")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(255), nullable=False)
    location = Column(String(255))
    industry = Column(String(255))
    contact_name = Column(String(255))
    contact_phone = Column(String(50))
    contact_email = Column(String(255))
    outreach_status = Column(
        Enum(*LEAD_STATUS, name="lead_status"),
        nullable=False,
        default="research",
    )
    last_contact_date = Column(Date)
    potential_volume = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_leads_outreach_status", "outreach_status"),)
