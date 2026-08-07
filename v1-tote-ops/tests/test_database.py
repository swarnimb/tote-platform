from unittest.mock import MagicMock, patch

import pytest


def test_get_db_yields_session_and_closes():
    import app.database as db_module

    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)

    original_factory = db_module._SessionFactory
    db_module._SessionFactory = mock_factory
    try:
        gen = db_module.get_db()
        yielded = next(gen)

        assert yielded is mock_session

        with pytest.raises(StopIteration):
            next(gen)

        mock_session.close.assert_called_once()
    finally:
        db_module._SessionFactory = original_factory


def test_raises_on_invalid_database_url_format(monkeypatch):
    from sqlalchemy.exc import ArgumentError

    from app.config import settings
    from app.database import get_engine

    monkeypatch.setattr(settings, "DATABASE_URL", "not-a-valid-url")

    with pytest.raises(ArgumentError):
        get_engine()
