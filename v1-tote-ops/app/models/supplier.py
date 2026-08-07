import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(
        "id",
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    company_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    phone = Column(String(50))
    email = Column(String(255))
    bol_email = Column(String(255))
    bol_same_as_primary = Column(Boolean, default=False, nullable=False)
    industry = Column(String(255))
    tote_types = Column(String(20))
    average_quantity_275 = Column("average_quantity_275", String(50))
    average_quantity_330 = Column("average_quantity_330", String(50))
    last_pickup_date = Column(Date)
    last_action_stage = Column(String(32))
    last_action_date = Column(Date)
    working_hours = Column(String(255))
    is_hazmat = Column(Boolean, default=False, nullable=False)
    warnings = Column(Text)
    notes = Column(Text)
    followup_weeks = Column(Integer, default=4, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    gradeouts = relationship("Gradeout", back_populates="supplier")
    pickups = relationship("Pickup", back_populates="supplier")

    __table_args__ = (Index("idx_suppliers_is_deleted", "is_deleted"),)
