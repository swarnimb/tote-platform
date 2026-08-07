import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.auth import require_auth
from app.database import get_db
from app.services.invoice_service import (
    NotFoundError,
    delete_invoice,
    generate_invoice_image,
    generate_invoice_preview,
    get_invoice_by_month,
    get_invoices,
    overwrite_invoice,
    save_invoice,
    toggle_invoice_sent,
)

router = APIRouter(prefix="/invoices")
templates = Jinja2Templates(directory="app/templates")


@router.get("", dependencies=[Depends(require_auth)])
def list_invoices(request: Request, db: Session = Depends(get_db)):
    invoices = get_invoices(db)
    return templates.TemplateResponse(
        request,
        "invoices/list.html",
        {"invoices": invoices},
    )


@router.get("/preview", dependencies=[Depends(require_auth)])
def preview_invoice(request: Request, month: str = "", db: Session = Depends(get_db)):
    try:
        month_date = date.fromisoformat(f"{month}-01")
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid month format. Use YYYY-MM.")

    try:
        preview = generate_invoice_preview(db, month_date)
    except ValueError as e:
        logger.warning("Invoice preview failed: %s", e, exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))

    existing = get_invoice_by_month(db, month_date)
    return templates.TemplateResponse(
        request,
        "invoices/_preview_modal.html",
        {
            "month": month_date,
            "preview": preview,
            "existing_invoice": existing,
        },
    )


@router.post("/generate-or-confirm", dependencies=[Depends(require_auth)])
async def generate_or_confirm(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    month_str = str(form.get("month", "")).strip()

    try:
        month_date = date.fromisoformat(f"{month_str}-01")
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid month format. Use YYYY-MM.")

    try:
        preview = generate_invoice_preview(db, month_date)
    except ValueError as e:
        logger.warning("Invoice generate-or-confirm preview failed: %s", e, exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))

    existing = get_invoice_by_month(db, month_date)
    if existing:
        return templates.TemplateResponse(
            request,
            "invoices/_overwrite_confirm.html",
            {"month": month_date},
        )

    save_invoice(db, month_date, preview)
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/invoices"
    return response


@router.post("/overwrite", dependencies=[Depends(require_auth)])
async def overwrite_invoice_route(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    month_str = str(form.get("month", "")).strip()

    try:
        month_date = date.fromisoformat(f"{month_str}-01")
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid month format. Use YYYY-MM.")

    try:
        preview = generate_invoice_preview(db, month_date)
    except ValueError as e:
        logger.warning("Invoice overwrite preview failed: %s", e, exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))

    try:
        overwrite_invoice(db, month_date, preview)
    except NotFoundError as e:
        logger.warning("Invoice overwrite target not found: %s", e, exc_info=True)
        raise HTTPException(status_code=404, detail="No existing invoice to overwrite")

    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/invoices"
    return response


@router.delete("/{invoice_id}", dependencies=[Depends(require_auth)])
def delete_invoice_route(invoice_id: str, db: Session = Depends(get_db)):
    try:
        delete_invoice(db, invoice_id)
    except NotFoundError as e:
        logger.warning("Invoice delete target not found: %s", e, exc_info=True)
        raise HTTPException(status_code=404, detail="Invoice not found")
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/invoices"
    return response


@router.patch("/{invoice_id}/sent", dependencies=[Depends(require_auth)])
def toggle_sent_route(invoice_id: str, db: Session = Depends(get_db)):
    try:
        toggle_invoice_sent(db, invoice_id)
    except NotFoundError as e:
        logger.warning("Invoice sent-toggle target not found: %s", e, exc_info=True)
        raise HTTPException(status_code=404, detail="Invoice not found")
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/invoices"
    return response


@router.get("/{invoice_id}/image", dependencies=[Depends(require_auth)])
def invoice_image_route(invoice_id: str, db: Session = Depends(get_db)):
    try:
        image_bytes = generate_invoice_image(db, invoice_id)
    except NotFoundError as e:
        logger.warning("Invoice image target not found: %s", e, exc_info=True)
        raise HTTPException(status_code=404, detail="Invoice not found")
    except ValueError as e:
        logger.warning("Invoice image generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))
    return Response(content=image_bytes, media_type="image/png")
