from sqlalchemy import Column, String

from app.models.base import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(64), primary_key=True)
    value = Column(String(512), nullable=False)
