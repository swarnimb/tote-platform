from datetime import datetime, timedelta, timezone

from fastapi import Request

from app.config import settings


class AuthenticationRequired(Exception):
    """Raised by require_auth when session is missing or expired."""
    pass


def require_auth(request: Request) -> None:
    authenticated = request.session.get("authenticated")
    expires_at_str = request.session.get("expires_at")

    if not authenticated or not expires_at_str:
        raise AuthenticationRequired()

    try:
        expires_at = datetime.fromisoformat(expires_at_str)
    except ValueError:
        request.session.clear()
        raise AuthenticationRequired()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now > expires_at:
        request.session.clear()
        raise AuthenticationRequired()


def set_session(request: Request) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = now + timedelta(days=settings.SESSION_EXPIRY_DAYS)
    request.session["authenticated"] = True
    request.session["expires_at"] = expires_at.isoformat()


def clear_session(request: Request) -> None:
    request.session.clear()
