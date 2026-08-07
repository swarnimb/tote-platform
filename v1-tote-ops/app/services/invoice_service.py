import io
import urllib.parse
from datetime import date, datetime, timezone

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.config import settings
from app.models.gradeout import Gradeout
from app.models.invoice import Invoice
from app.models.supplier import Supplier


class ConflictError(Exception):
    pass


class NotFoundError(Exception):
    pass


def get_invoices(db: Session) -> list:
    return db.query(Invoice).order_by(Invoice.month.desc()).all()


def get_invoice_by_month(db: Session, month: date) -> Invoice | None:
    return db.query(Invoice).filter(Invoice.month == month).first()


def _city_state(location: str) -> str:
    parts = location.split(",")
    if len(parts) >= 2:
        return parts[-2].strip() + ", " + parts[-1].strip()
    return location


def generate_invoice_preview(db: Session, month: date) -> dict:
    next_month = (
        date(month.year + 1, 1, 1)
        if month.month == 12
        else date(month.year, month.month + 1, 1)
    )
    gradeouts = (
        db.query(Gradeout)
        .join(Supplier, Gradeout.supplier_id == Supplier.id)
        .filter(
            Gradeout.date_received >= month,
            Gradeout.date_received < next_month,
        )
        .order_by(Gradeout.date_received)
        .all()
    )
    if not gradeouts:
        raise ValueError(f"No gradeouts found for {month.strftime('%B %Y')}")

    rows = []
    for g in gradeouts:
        total_usable = g.totes_275_total_usable + g.totes_330_total_usable
        revenue = total_usable * settings.TOTE_RATE
        location = g.supplier.location or ""
        rows.append({
            "supplier": g.supplier.company_name,
            "location": location,
            "city_state": _city_state(location),
            "date": g.date_received,
            "total_usable": total_usable,
            "revenue": revenue,
            "totes_275": g.totes_275_total_usable,
            "totes_330": g.totes_330_total_usable,
        })

    totals = {
        "gradeout_count": len(rows),
        "total_usable": sum(r["total_usable"] for r in rows),
        "total_usable_275": sum(r["totes_275"] for r in rows),
        "total_usable_330": sum(r["totes_330"] for r in rows),
        "total_revenue": sum(r["revenue"] for r in rows),
    }
    return {"rows": rows, "totals": totals}


def save_invoice(db: Session, month: date, preview_data: dict) -> Invoice:
    existing = db.query(Invoice).filter(Invoice.month == month).first()
    if existing:
        raise ConflictError(f"Invoice for {month.strftime('%B %Y')} already exists")

    totals = preview_data["totals"]
    invoice = Invoice(
        month=month,
        gradeout_count=totals["gradeout_count"],
        total_usable_275=totals["total_usable_275"],
        total_usable_330=totals["total_usable_330"],
        total_revenue=totals["total_revenue"],
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def mark_invoice_sent(db: Session, invoice_id: str) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError(f"Invoice {invoice_id} not found")
    invoice.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(invoice)
    return invoice


def overwrite_invoice(db: Session, month: date, preview_data: dict) -> Invoice:
    existing = db.query(Invoice).filter(Invoice.month == month).first()
    if not existing:
        raise NotFoundError(f"No invoice found for {month.strftime('%B %Y')}")
    db.delete(existing)
    db.commit()
    return save_invoice(db, month, preview_data)


def delete_invoice(db: Session, invoice_id: str) -> None:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError(f"Invoice {invoice_id} not found")
    db.delete(invoice)
    db.commit()


def toggle_invoice_sent(db: Session, invoice_id: str) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError(f"Invoice {invoice_id} not found")
    if invoice.sent_at is None:
        invoice.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        invoice.sent_at = None
    db.commit()
    db.refresh(invoice)
    return invoice


def _draw_table_rows(draw, rows: list, column_widths: list, pad: int, row_height: int, font, image_width: int, y: int) -> int:
    for row in rows:
        date_val = row.get("date", "")
        date_str = date_val.strftime("%b %d, %Y") if hasattr(date_val, "strftime") else ""
        vals = [
            str(row["supplier"])[:28],
            str(row.get("city_state") or row.get("location", ""))[:18],
            date_str,
            str(row["total_usable"]),
            f"${int(row['revenue'])}",
        ]
        x = pad
        for i, val in enumerate(vals):
            draw.text((x, y + 9), val, fill="#111827", font=font)
            x += column_widths[i]
        draw.line([0, y + row_height, image_width, y + row_height], fill="#f3f4f6")
        y += row_height
    return y


def _build_invoice_image(rows: list, totals: dict, month_str: str) -> bytes:
    column_widths = [200, 130, 100, 100, 80]
    pad, row_height = 16, 30
    image_width = sum(column_widths) + pad * 2
    image_height = pad + row_height * (len(rows) + 3) + pad

    img = Image.new("RGB", (image_width, image_height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=13)
    font_small = ImageFont.load_default(size=11)

    y = pad
    draw.text((pad, y), f"Invoice \u2014 {month_str}", fill="#111827", font=font)
    y += row_height

    draw.rectangle([0, y, image_width, y + row_height], fill="#f9fafb")
    x = pad
    for i, col in enumerate(["Supplier", "Address", "Date", "Usable Totes", "Revenue"]):
        draw.text((x, y + 9), col.upper(), fill="#6b7280", font=font_small)
        x += column_widths[i]
    draw.line([0, y + row_height, image_width, y + row_height], fill="#e5e7eb")
    y += row_height

    y = _draw_table_rows(draw, rows, column_widths, pad, row_height, font, image_width, y)

    draw.line([0, y, image_width, y], fill="#e5e7eb", width=2)
    draw.rectangle([0, y, image_width, y + row_height], fill="#f9fafb")
    count = totals["gradeout_count"]
    tfoot = [f"Total \u2014 {count} gradeout{'s' if count != 1 else ''}", "", "",
             str(int(totals["total_usable"])), f"${int(totals['total_revenue'])}"]
    x = pad
    for i, val in enumerate(tfoot):
        draw.text((x, y + 9), val, fill="#111827", font=font)
        x += column_widths[i]

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_invoice_image(db: Session, invoice_id: str) -> bytes:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise NotFoundError(f"Invoice {invoice_id} not found")

    preview = generate_invoice_preview(db, invoice.month)
    rows, totals = preview["rows"], preview["totals"]
    month_str = invoice.month.strftime("%B %Y")
    return _build_invoice_image(rows, totals, month_str)


def build_invoice_mailto(invoice: Invoice, rows: list[dict]) -> str:
    month_str = invoice.month.strftime("%B %Y")
    total_revenue = int(invoice.total_revenue)
    subject = f"Alicia {month_str} Invoice - ${total_revenue}"

    intro = (
        f"Hi,\n\n"
        f"Hope you're doing well! Included below are the gradeouts for {month_str}, "
        f"totalling ${total_revenue}. Let me know if you have any questions.\n\n"
    )

    col1, col2, col3, col4 = 30, 22, 14, 10
    header = f"{'Supplier':<{col1}}  {'Address':<{col2}}  {'Usable Totes':>{col3}}  {'Revenue':>{col4}}"
    divider = "-" * (col1 + col2 + col3 + col4 + 6)
    lines = [header, divider]
    for row in rows:
        lines.append(
            f"{row['supplier'][:col1]:<{col1}}  "
            f"{row['location'][:col2]:<{col2}}  "
            f"{row['total_usable']:>{col3}}  "
            f"${row['revenue']:>{col4 - 1}}"
        )
    lines.append(divider)
    total_usable = int(invoice.total_usable_275) + int(invoice.total_usable_330)
    lines.append(
        f"{'TOTAL':<{col1}}  {'':<{col2}}  "
        f"{total_usable:>{col3}}  "
        f"${total_revenue:>{col4 - 1}}"
    )

    body = intro + "\n".join(lines)
    return (
        f"mailto:{settings.INVOICE_RECIPIENT_EMAIL}"
        f"?subject={urllib.parse.quote(subject, safe='')}"
        f"&body={urllib.parse.quote(body, safe='')}"
    )
