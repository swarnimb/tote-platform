import uuid

from sqlalchemy import Column, Date, Index, Integer, Numeric, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from app.models.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    month = Column(Date, nullable=False)
    gradeout_count = Column(Integer, nullable=False)
    total_usable_275 = Column(Integer, nullable=False)
    total_usable_330 = Column(Integer, nullable=False)
    total_revenue = Column(Numeric(10, 2), nullable=False)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
    sent_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("month", name="uq_invoices_month"),
        Index("idx_invoices_month", "month"),
    )
