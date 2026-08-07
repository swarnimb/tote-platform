from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def get_engine() -> Engine:
    return create_engine(settings.DATABASE_URL)


def get_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine)


_engine = get_engine()
_SessionFactory = get_session_factory(_engine)


def get_db() -> Generator[Session, None, None]:
    db = _SessionFactory()
    try:
        yield db
    finally:
        db.close()
