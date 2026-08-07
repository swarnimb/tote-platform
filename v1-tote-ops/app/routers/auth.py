from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import clear_session, require_auth, set_session
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _session_is_valid(request: Request) -> bool:
    if not request.session.get("authenticated"):
        return False
    expires_at_str = request.session.get("expires_at")
    if not expires_at_str:
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_str)
    except ValueError:
        return False
    return datetime.now(timezone.utc).replace(tzinfo=None) <= expires_at


@router.get("/login")
def login_page(request: Request):
    if _session_is_valid(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
def login(request: Request, password: str = Form(...)):
    if password != settings.APP_PASSWORD:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Incorrect password"},
            status_code=200,
        )
    set_session(request)
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    clear_session(request)
    return RedirectResponse("/login", status_code=303)
