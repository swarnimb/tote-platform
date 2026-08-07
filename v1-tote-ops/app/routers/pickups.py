from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.services.pickup_service import NotFoundError, cancel_pickup, create_pickup

router = APIRouter(prefix="/pickups")


@router.post("", dependencies=[Depends(require_auth)])
async def create_pickup_route(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    supplier_id = form.get("supplier_id", "").strip()
    if not supplier_id:
        raise HTTPException(status_code=422, detail="supplier_id is required")
    try:
        create_pickup(db, supplier_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if request.headers.get("HX-Request"):
        return HTMLResponse("")
    return RedirectResponse(f"/suppliers/{supplier_id}", status_code=303)


@router.delete("/{pickup_id}", dependencies=[Depends(require_auth)])
def cancel_pickup_route(pickup_id: str, db: Session = Depends(get_db)):
    try:
        cancel_pickup(db, pickup_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    response = HTMLResponse("")
    response.headers["HX-Redirect"] = "/"
    return response
