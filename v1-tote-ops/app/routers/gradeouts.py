from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config import settings
from app.database import get_db
from app.services.gradeout_service import (
    NotFoundError,
    create_gradeout,
    delete_gradeout,
    get_gradeout_by_id,
    get_gradeouts,
    update_gradeout,
)
from app.services.pickup_service import get_confirmed_pickups_for_supplier
from app.services.supplier_service import get_suppliers

router = APIRouter(prefix="/gradeouts")
templates = Jinja2Templates(directory="app/templates")


@router.get("", dependencies=[Depends(require_auth)])
def list_gradeouts(
    request: Request,
    db: Session = Depends(get_db),
    supplier_id: str | None = None,
    month: str | None = None,
):
    from datetime import date

    month_date = None
    if month:
        try:
            month_date = date.fromisoformat(f"{month}-01")
        except ValueError:
            pass

    gradeouts = get_gradeouts(db, supplier_id=supplier_id, month=month_date)
    suppliers = get_suppliers(db)
    return templates.TemplateResponse(
        request,
        "gradeouts/list.html",
        {
            "gradeouts": gradeouts,
            "suppliers": suppliers,
            "filter_supplier": supplier_id or "",
            "filter_month": month or "",
            "tote_rate": settings.TOTE_RATE,
        },
    )


def _confirmed_pickups_by_supplier(db: Session, suppliers: list) -> dict:
    result = {}
    for s in suppliers:
        pickups = get_confirmed_pickups_for_supplier(db, str(s.id))
        if pickups:
            result[str(s.id)] = [
                {"id": str(p.id), "label": f"Confirmed {p.created_at.strftime('%b %d')}"}
                for p in pickups
            ]
    return result


@router.get("/new", dependencies=[Depends(require_auth)])
def new_gradeout_form(request: Request, db: Session = Depends(get_db)):
    suppliers = get_suppliers(db)
    return templates.TemplateResponse(
        request,
        "gradeouts/new.html",
        {
            "suppliers": suppliers,
            "confirmed_pickups_by_supplier": _confirmed_pickups_by_supplier(db, suppliers),
        },
    )


@router.post("", dependencies=[Depends(require_auth)])
async def create_gradeout_route(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = dict(form)
    try:
        create_gradeout(db, data)
        return RedirectResponse("/gradeouts", status_code=303)
    except ValueError as e:
        suppliers = get_suppliers(db)
        return templates.TemplateResponse(
            request,
            "gradeouts/new.html",
            {
                "suppliers": suppliers,
                "confirmed_pickups_by_supplier": _confirmed_pickups_by_supplier(db, suppliers),
                "form_error": str(e),
                "form_data": data,
            },
            status_code=422,
        )


@router.get("/{gradeout_id}/edit", dependencies=[Depends(require_auth)])
def edit_gradeout_form(gradeout_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        gradeout = get_gradeout_by_id(db, gradeout_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Gradeout not found")
    suppliers = get_suppliers(db)
    return templates.TemplateResponse(
        request,
        "gradeouts/edit.html",
        {"gradeout": gradeout, "suppliers": suppliers},
    )


@router.post("/{gradeout_id}/edit", dependencies=[Depends(require_auth)])
async def update_gradeout_route(
    gradeout_id: str, request: Request, db: Session = Depends(get_db)
):
    form = await request.form()
    data = dict(form)
    try:
        update_gradeout(db, gradeout_id, data)
        return RedirectResponse("/gradeouts", status_code=303)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Gradeout not found")
    except ValueError as e:
        suppliers = get_suppliers(db)
        try:
            gradeout = get_gradeout_by_id(db, gradeout_id)
        except NotFoundError:
            raise HTTPException(status_code=404, detail="Gradeout not found")
        return templates.TemplateResponse(
            request,
            "gradeouts/edit.html",
            {"gradeout": gradeout, "suppliers": suppliers, "form_error": str(e), "form_data": data},
            status_code=422,
        )


@router.delete("/{gradeout_id}", dependencies=[Depends(require_auth)])
def delete_gradeout_route(gradeout_id: str, db: Session = Depends(get_db)):
    try:
        delete_gradeout(db, gradeout_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Gradeout not found")
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/gradeouts"
    return response
