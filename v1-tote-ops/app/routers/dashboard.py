from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import settings
from app.database import get_db
from app.services.dashboard_service import (
    get_active_supplier_count,
    get_all_confirmed_pickups,
    get_confirmed_pickup_count,
    get_followup_suppliers,
    get_monthly_stats,
    get_recent_gradeouts,
    get_revenue_chart_data,
    get_yearly_stats,
)
from app.services.supplier_service import get_suppliers

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", dependencies=[Depends(require_auth)])
def dashboard(request: Request, db: Session = Depends(get_db), period: str = "month"):
    today = date.today()
    if period == "year":
        stats = get_yearly_stats(db, today.year)
        period_label = str(today.year)
    else:
        period = "month"
        stats = get_monthly_stats(db, today.year, today.month)
        period_label = today.strftime("%B %Y")
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "stats": stats,
            "active_suppliers": get_active_supplier_count(db),
            "recent_gradeouts": get_recent_gradeouts(db),
            "followup_suppliers": get_followup_suppliers(db),
            "period_label": period_label,
            "period": period,
            "tote_rate": settings.TOTE_RATE,
            "confirmed_pickup_count": get_confirmed_pickup_count(db),
            "confirmed_pickups": get_all_confirmed_pickups(db),
            "chart_data": get_revenue_chart_data(db),
            "all_suppliers": get_suppliers(db, active_only=True),
        },
    )
