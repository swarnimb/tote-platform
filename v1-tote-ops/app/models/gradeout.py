import uuid

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Gradeout(Base):
    __tablename__ = "gradeouts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    pickup_id = Column(String(36), ForeignKey("pickups.id"), nullable=True)
    date_received = Column(Date, nullable=False)
    totes_275_good_washable = Column(Integer, default=0)
    totes_275_good_cage = Column(Integer, default=0)
    totes_275_total_usable = Column(Integer, default=0)
    totes_330_good_washable = Column(Integer, default=0)
    totes_330_good_cage = Column(Integer, default=0)
    totes_330_total_usable = Column(Integer, default=0)
    junk = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    supplier = relationship("Supplier", back_populates="gradeouts")
    pickup = relationship("Pickup", back_populates="gradeout")

    __table_args__ = (
        Index("idx_gradeouts_supplier_id", "supplier_id"),
        Index("idx_gradeouts_date_received", "date_received"),
    )
