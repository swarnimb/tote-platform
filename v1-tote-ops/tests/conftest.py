import base64
import json
import os
from datetime import datetime, timedelta, timezone

import itsdangerous
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set all required env vars before any app module is imported.
# Must happen at module level so imports in test files succeed.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("SUPABASE_STORAGE_BUCKET", "test-bucket")
os.environ.setdefault("APP_PASSWORD", "test-password")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret-key-32-chars!!")
os.environ.setdefault("INVOICE_RECIPIENT_EMAIL", "test@example.com")


def _make_session_cookie(data: dict, secret: str) -> str:
    """Craft a signed Starlette session cookie from a dict."""
    payload = base64.b64encode(json.dumps(data).encode()).decode()
    signer = itsdangerous.TimestampSigner(secret)
    return signer.sign(payload).decode()


def _sqlite_engine():
    """Create a SQLite in-memory engine with a single shared connection."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def test_db():
    """SQLite in-memory session for service-level unit tests."""
    from app.models import Base

    engine = _sqlite_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    from app.database import get_db
    from app.main import app
    from app.models import Base

    engine = _sqlite_engine()
    Base.metadata.create_all(engine)
    ClientSession = sessionmaker(bind=engine)

    def override_get_db():
        db = ClientSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture
def authenticated_client(client):
    client.post("/login", data={"password": "test-password"})
    return client


@pytest.fixture
def authenticated_client_with_db():
    """Authenticated TestClient sharing the same SQLite engine as the yielded db session.

    Use this when a test needs to both seed data via service calls (db) AND make
    HTTP requests that must see that data (client). Both use the same StaticPool engine.
    """
    from app.database import get_db
    from app.main import app
    from app.models import Base

    engine = _sqlite_engine()
    Base.metadata.create_all(engine)
    SharedSession = sessionmaker(bind=engine)
    db = SharedSession()

    def override_get_db():
        sess = SharedSession()
        try:
            yield sess
        finally:
            sess.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        c.post("/login", data={"password": "test-password"})
        yield c, db
    db.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture
def expired_session_client():
    from app.main import app
    from app.config import settings

    session_data = {
        "authenticated": True,
        "expires_at": (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).isoformat(),
    }
    cookie_value = _make_session_cookie(session_data, settings.SESSION_SECRET_KEY)

    with TestClient(app, raise_server_exceptions=True) as c:
        c.cookies.set("session", cookie_value)
        yield c
