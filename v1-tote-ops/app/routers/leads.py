from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.services.lead_service import (
    NotFoundError,
    build_supplier_prefill,
    create_lead,
    delete_lead,
    get_leads,
    update_lead,
    update_lead_status,
)

router = APIRouter(prefix="/leads")
templates = Jinja2Templates(directory="app/templates")


@router.get("", dependencies=[Depends(require_auth)])
def list_leads(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = None,
):
    leads = get_leads(db, status=status)
    return templates.TemplateResponse(
        request,
        "leads/list.html",
        {"leads": leads, "filter_status": status or ""},
    )


@router.post("", dependencies=[Depends(require_auth)])
async def create_lead_route(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = dict(form)
    try:
        create_lead(db, data)
        return RedirectResponse("/leads", status_code=303)
    except ValueError as e:
        leads = get_leads(db)
        return templates.TemplateResponse(
            request,
            "leads/list.html",
            {
                "leads": leads,
                "filter_status": "",
                "form_error": str(e),
                "show_create_modal": True,
                "form_data": data,
            },
            status_code=422,
        )


@router.patch("/{lead_id}/status", dependencies=[Depends(require_auth)])
async def update_lead_status_route(
    request: Request,
    lead_id: str,
    db: Session = Depends(get_db),
):
    form = await request.form()
    status = str(form.get("status", ""))
    try:
        lead, should_convert = update_lead_status(db, lead_id, status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Lead not found")

    row_tpl = templates.get_template("leads/_row.html")
    row_html = row_tpl.render({"lead": lead, "request": request})

    if not should_convert:
        return HTMLResponse(row_html)

    prefill = build_supplier_prefill(lead)
    modal_tpl = templates.get_template("leads/_convert_modal.html")
    modal_html = modal_tpl.render({"lead": lead, "prefill": prefill, "request": request})
    return HTMLResponse(row_html + modal_html)


@router.patch("/{lead_id}", dependencies=[Depends(require_auth)])
async def update_lead_route(
    request: Request,
    lead_id: str,
    db: Session = Depends(get_db),
):
    form = await request.form()
    data = dict(form)
    try:
        update_lead(db, lead_id, data)
        if request.headers.get("HX-Request"):
            response = HTMLResponse("")
            response.headers["HX-Redirect"] = "/leads"
            return response
        return RedirectResponse("/leads", status_code=303)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Lead not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{lead_id}", dependencies=[Depends(require_auth)])
def delete_lead_route(lead_id: str, db: Session = Depends(get_db)):
    try:
        delete_lead(db, lead_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Lead not found")
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/leads"
    return response
