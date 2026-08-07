from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import AuthenticationRequired
from app.config import settings
from app.routers import auth, dashboard, gradeouts, growth, invoices, leads, pickups, suppliers

app = FastAPI(title="Tote-Ops")

app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(suppliers.router)
app.include_router(pickups.router)
app.include_router(gradeouts.router)
app.include_router(invoices.router)
app.include_router(leads.router)
app.include_router(growth.router)


@app.exception_handler(AuthenticationRequired)
async def auth_redirect_handler(request: Request, exc: AuthenticationRequired):
    return RedirectResponse("/login", status_code=302)
