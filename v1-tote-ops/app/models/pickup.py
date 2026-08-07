import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Pickup(Base):
    __tablename__ = "pickups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"), nullable=False)
    status = Column(String(16), nullable=False, default="confirmed")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    supplier = relationship("Supplier", back_populates="pickups")
    gradeout = relationship("Gradeout", back_populates="pickup", uselist=False)
