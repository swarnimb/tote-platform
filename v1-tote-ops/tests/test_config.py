import os

import pytest

REQUIRED_VARS = {
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-supabase-key",
    "SUPABASE_STORAGE_BUCKET": "test-bucket",
    "APP_PASSWORD": "test-password",
    "SESSION_SECRET_KEY": "test-session-secret-key-32-chars!!",
    "INVOICE_RECIPIENT_EMAIL": "test@example.com",
}


def test_loads_all_required_env_vars(monkeypatch):
    for key, value in REQUIRED_VARS.items():
        monkeypatch.setenv(key, value)

    from app.config import Settings

    s = Settings()

    assert s.DATABASE_URL == REQUIRED_VARS["DATABASE_URL"]
    assert s.SUPABASE_URL == REQUIRED_VARS["SUPABASE_URL"]
    assert s.SUPABASE_KEY == REQUIRED_VARS["SUPABASE_KEY"]
    assert s.SUPABASE_STORAGE_BUCKET == REQUIRED_VARS["SUPABASE_STORAGE_BUCKET"]
    assert s.APP_PASSWORD == REQUIRED_VARS["APP_PASSWORD"]
    assert s.SESSION_SECRET_KEY == REQUIRED_VARS["SESSION_SECRET_KEY"]
    assert s.INVOICE_RECIPIENT_EMAIL == REQUIRED_VARS["INVOICE_RECIPIENT_EMAIL"]
    assert s.TOTE_RATE == 5
    assert s.FOLLOWUP_DAYS_THRESHOLD == 60
    assert s.UPCOMING_PICKUP_DAYS == 14
    assert s.SESSION_EXPIRY_DAYS == 30
    assert s.PDF_SIGNED_URL_EXPIRY_SECONDS == 3600


def test_raises_KeyError_on_missing_required_env_var(monkeypatch):
    for key, value in REQUIRED_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("DATABASE_URL")

    from app.config import Settings

    with pytest.raises(KeyError, match="DATABASE_URL"):
        Settings()
