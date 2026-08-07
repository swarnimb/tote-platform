from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import settings
from app.database import get_db
from app.services import growth_service
from app.services.dashboard_service import get_active_supplier_count

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/growth", dependencies=[Depends(require_auth)])
def growth_page(request: Request, db: Session = Depends(get_db)):
    target_str = growth_service.get_setting(db, "growth_target")
    target = float(target_str) if target_str is not None else None
    return templates.TemplateResponse(
        request,
        "growth/index.html",
        {
            "growth_target": target,
            "default_suppliers": get_active_supplier_count(db),
            "default_shipments": growth_service.get_avg_shipments_per_supplier(db),
            "default_totes": growth_service.get_avg_totes_per_shipment(db),
            "default_rate": settings.TOTE_RATE,
        },
    )


@router.post("/growth/target", dependencies=[Depends(require_auth)])
async def save_growth_target(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    try:
        target = float(form.get("target", ""))
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Target must be a number")
    if target < 0:
        raise HTTPException(status_code=422, detail="Target must be 0 or greater")
    growth_service.set_setting(db, "growth_target", str(target))
    return RedirectResponse("/growth", status_code=303)
