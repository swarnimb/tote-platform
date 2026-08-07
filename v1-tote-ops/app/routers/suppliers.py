from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.services.pickup_service import get_confirmed_pickups_for_supplier
from app.services.supplier_service import (
    NotFoundError,
    build_followup_mailto,
    build_followup_sms,
    create_supplier,
    get_supplier_by_id,
    get_supplier_gradeout_stats,
    get_supplier_quality_rate,
    get_suppliers,
    set_supplier_action_stage,
    set_supplier_followup_weeks,
    soft_delete_supplier,
    toggle_supplier_active,
    update_supplier,
)

router = APIRouter(prefix="/suppliers")
templates = Jinja2Templates(directory="app/templates")


@router.get("", dependencies=[Depends(require_auth)])
def list_suppliers(
    request: Request,
    db: Session = Depends(get_db),
    action_stage: str | None = Query(None),
    active_only: bool = Query(True),
):
    suppliers = get_suppliers(db, action_stage=action_stage, active_only=active_only)
    supplier_stats = get_supplier_gradeout_stats(db, [s.id for s in suppliers])
    return templates.TemplateResponse(
        request,
        "suppliers/list.html",
        {
            "suppliers": suppliers,
            "action_stage": action_stage or "",
            "active_only": active_only,
            "supplier_stats": supplier_stats,
        },
    )


@router.post("", dependencies=[Depends(require_auth)])
async def create_supplier_route(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = dict(form)
    try:
        create_supplier(db, data)
        return RedirectResponse("/suppliers", status_code=303)
    except ValueError as e:
        suppliers = get_suppliers(db)
        supplier_stats = get_supplier_gradeout_stats(db, [s.id for s in suppliers])
        return templates.TemplateResponse(
            request,
            "suppliers/list.html",
            {
                "suppliers": suppliers,
                "action_stage": "",
                "active_only": True,
                "form_error": str(e),
                "show_create_modal": True,
                "form_data": data,
                "supplier_stats": supplier_stats,
            },
            status_code=422,
        )


@router.post("/quick", dependencies=[Depends(require_auth)])
async def quick_create_supplier(request: Request, db: Session = Depends(get_db)):
    """Create a supplier inline from the gradeout form. Returns updated supplier select."""
    form = await request.form()
    data = dict(form)
    try:
        supplier = create_supplier(db, data)
    except ValueError as e:
        suppliers = get_suppliers(db)
        return templates.TemplateResponse(
            request,
            "suppliers/_quick_select.html",
            {"suppliers": suppliers, "selected_id": "", "quick_error": str(e)},
            status_code=422,
        )
    suppliers = get_suppliers(db)
    response = templates.TemplateResponse(
        request,
        "suppliers/_quick_select.html",
        {"suppliers": suppliers, "selected_id": supplier.id},
    )
    response.headers["HX-Trigger"] = "closeSupplierModal"
    return response


@router.get("/search", dependencies=[Depends(require_auth)])
def search_suppliers(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
    action_stage: str | None = Query(None),
    active_only: bool = Query(True),
):
    suppliers = get_suppliers(db, search=q, action_stage=action_stage or None, active_only=active_only)
    if not suppliers:
        return HTMLResponse(
            '<tr><td colspan="8" style="text-align:center; padding:24px; font-size:13px;'
            ' color:#9ca3af;">No suppliers match your search.</td></tr>'
        )
    supplier_stats = get_supplier_gradeout_stats(db, [s.id for s in suppliers])
    row_template = templates.get_template("suppliers/_row.html")
    content = "".join(
        row_template.render({"supplier": s, "request": request, "supplier_stats": supplier_stats})
        for s in suppliers
    )
    return HTMLResponse(content)


@router.put("/{supplier_id}", dependencies=[Depends(require_auth)])
async def update_supplier_route(
    request: Request,
    supplier_id: str,
    db: Session = Depends(get_db),
):
    form = await request.form()
    data = dict(form)
    try:
        update_supplier(db, supplier_id, data)
        if request.headers.get("HX-Request"):
            response = HTMLResponse("")
            response.headers["HX-Redirect"] = f"/suppliers/{supplier_id}"
            return response
        return RedirectResponse(f"/suppliers/{supplier_id}", status_code=303)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{supplier_id}", dependencies=[Depends(require_auth)])
def get_supplier_detail(
    request: Request,
    supplier_id: str,
    db: Session = Depends(get_db),
):
    try:
        supplier = get_supplier_by_id(db, supplier_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    followup_mailto = build_followup_mailto(supplier, None)
    followup_sms = build_followup_sms(supplier)
    quality_rate = get_supplier_quality_rate(db, supplier_id)
    gradeout_stats = get_supplier_gradeout_stats(db, [supplier_id])
    stats = gradeout_stats.get(supplier_id)
    confirmed_pickup_count = len(get_confirmed_pickups_for_supplier(db, str(supplier.id)))
    return templates.TemplateResponse(
        request,
        "suppliers/detail.html",
        {
            "supplier": supplier,
            "followup_mailto": followup_mailto,
            "followup_sms": followup_sms,
            "quality_rate": quality_rate,
            "gradeout_stats": stats,
            "confirmed_pickup_count": confirmed_pickup_count,
        },
    )


@router.patch("/{supplier_id}/action-stage", dependencies=[Depends(require_auth)])
async def update_action_stage(
    supplier_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    stage = (form.get("last_action_stage") or "").strip() or None
    try:
        set_supplier_action_stage(db, supplier_id, stage)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return HTMLResponse("")


@router.post("/{supplier_id}/followup-weeks", dependencies=[Depends(require_auth)])
async def update_followup_weeks(
    supplier_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    try:
        weeks = int(form.get("followup_weeks") or 4)
    except (TypeError, ValueError):
        weeks = 4
    try:
        set_supplier_followup_weeks(db, supplier_id, weeks)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return HTMLResponse("")


@router.post("/{supplier_id}/toggle-active", dependencies=[Depends(require_auth)])
def toggle_active(
    supplier_id: str,
    db: Session = Depends(get_db),
):
    try:
        toggle_supplier_active(db, supplier_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return RedirectResponse(f"/suppliers/{supplier_id}", status_code=303)


@router.delete("/{supplier_id}", dependencies=[Depends(require_auth)])
def delete_supplier_route(supplier_id: str, db: Session = Depends(get_db)):
    try:
        soft_delete_supplier(db, supplier_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/suppliers"
    return response
