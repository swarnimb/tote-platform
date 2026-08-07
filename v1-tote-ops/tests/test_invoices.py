from datetime import date, datetime

import pytest

from app.models.gradeout import Gradeout
from app.models.invoice import Invoice
from app.models.supplier import Supplier
from app.services.invoice_service import (
    ConflictError,
    NotFoundError,
    build_invoice_mailto,
    delete_invoice,
    generate_invoice_preview,
    mark_invoice_sent,
    overwrite_invoice,
    save_invoice,
    toggle_invoice_sent,
)


def _make_supplier(db):
    supplier = Supplier(company_name="Acme Co", location="Toledo, OH")
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier



def _make_gradeout(db, supplier_id, date_received=date(2026, 3, 10), usable_275=10, usable_330=5):
    gradeout = Gradeout(
        supplier_id=supplier_id,
        date_received=date_received,
        totes_275_total_usable=usable_275,
        totes_330_total_usable=usable_330,
    )
    db.add(gradeout)
    db.commit()
    db.refresh(gradeout)
    return gradeout


def test_generate_invoice_preview_returns_correct_totals_for_month(test_db):
    supplier = _make_supplier(test_db)
    _make_gradeout(test_db, supplier.id, date_received=date(2026, 3, 10), usable_275=10, usable_330=5)

    preview = generate_invoice_preview(test_db, date(2026, 3, 1))

    assert len(preview["rows"]) == 1
    assert preview["totals"]["total_usable_275"] == 10
    assert preview["totals"]["total_usable_330"] == 5
    assert preview["totals"]["gradeout_count"] == 1
    assert preview["totals"]["total_revenue"] == 75  # (10+5) * 5


def test_generate_invoice_preview_raises_ValueError_when_no_gradeouts_exist(test_db):
    with pytest.raises(ValueError, match="No gradeouts found for March 2026"):
        generate_invoice_preview(test_db, date(2026, 3, 1))


def test_save_invoice_raises_ConflictError_when_invoice_for_month_already_exists(test_db):
    supplier = _make_supplier(test_db)
    _make_gradeout(test_db, supplier.id)

    preview = generate_invoice_preview(test_db, date(2026, 3, 1))
    save_invoice(test_db, date(2026, 3, 1), preview)

    with pytest.raises(ConflictError):
        save_invoice(test_db, date(2026, 3, 1), preview)


def test_mark_invoice_sent_sets_sent_at_timestamp(test_db):
    invoice = Invoice(
        month=date(2026, 3, 1),
        gradeout_count=1,
        total_usable_275=10,
        total_usable_330=5,
        total_revenue=75,
    )
    test_db.add(invoice)
    test_db.commit()
    test_db.refresh(invoice)

    assert invoice.sent_at is None
    updated = mark_invoice_sent(test_db, invoice.id)
    assert updated.sent_at is not None


def test_mark_invoice_sent_raises_NotFoundError_when_invoice_not_found(test_db):
    with pytest.raises(NotFoundError):
        mark_invoice_sent(test_db, "nonexistent-id")


def test_build_invoice_mailto_returns_correctly_encoded_mailto_url(test_db):
    invoice = Invoice(
        month=date(2026, 3, 1),
        gradeout_count=1,
        total_usable_275=10,
        total_usable_330=5,
        total_revenue=75,
    )
    test_db.add(invoice)
    test_db.commit()
    test_db.refresh(invoice)

    rows = [{"supplier": "Acme Co", "location": "Cleveland, OH", "total_usable": 15, "revenue": 75, "totes_275": 10, "totes_330": 5}]
    mailto = build_invoice_mailto(invoice, rows)

    assert mailto.startswith("mailto:")
    assert "subject=" in mailto
    assert "body=" in mailto
    assert "Alicia" in mailto
    assert "March%202026" in mailto or "March+2026" in mailto
    assert "%2475" in mailto or "75" in mailto


# ---- Task 27: generate_invoice_preview ----

def test_generate_invoice_preview_returns_date_and_city_state_fields(test_db):
    supplier = Supplier(company_name="Acme Co", location="Toledo, OH")
    test_db.add(supplier)
    test_db.commit()
    test_db.refresh(supplier)
    test_db.add(Gradeout(
        supplier_id=supplier.id,
        date_received=date(2026, 3, 10),
        totes_275_total_usable=10,
        totes_330_total_usable=5,
    ))
    test_db.commit()

    row = generate_invoice_preview(test_db, date(2026, 3, 1))["rows"][0]
    assert row["date"] == date(2026, 3, 10)
    assert row["city_state"] == "Toledo, OH"


def test_generate_invoice_preview_city_state_falls_back_to_full_location_when_no_comma(test_db):
    supplier = Supplier(company_name="Acme Co", location="Springfield")
    test_db.add(supplier)
    test_db.commit()
    test_db.refresh(supplier)
    test_db.add(Gradeout(
        supplier_id=supplier.id,
        date_received=date(2026, 3, 10),
        totes_275_total_usable=10,
        totes_330_total_usable=5,
    ))
    test_db.commit()

    row = generate_invoice_preview(test_db, date(2026, 3, 1))["rows"][0]
    assert row["city_state"] == "Springfield"


# ---- Task 27: overwrite_invoice ----

def test_overwrite_invoice_raises_NotFoundError_when_no_existing_invoice(test_db):
    supplier = _make_supplier(test_db)
    _make_gradeout(test_db, supplier.id)
    preview = generate_invoice_preview(test_db, date(2026, 3, 1))

    with pytest.raises(NotFoundError):
        overwrite_invoice(test_db, date(2026, 3, 1), preview)


def test_overwrite_invoice_deletes_old_and_creates_new_for_same_month(test_db):
    supplier = _make_supplier(test_db)
    _make_gradeout(test_db, supplier.id)
    preview = generate_invoice_preview(test_db, date(2026, 3, 1))
    original = save_invoice(test_db, date(2026, 3, 1), preview)

    new_invoice = overwrite_invoice(test_db, date(2026, 3, 1), preview)

    assert new_invoice.id != original.id
    assert test_db.query(Invoice).filter(Invoice.id == original.id).first() is None
    assert test_db.query(Invoice).filter(Invoice.month == date(2026, 3, 1)).count() == 1


# ---- Task 27: delete_invoice ----

def test_delete_invoice_removes_invoice_from_db(test_db):
    invoice = Invoice(month=date(2026, 3, 1), gradeout_count=1,
                      total_usable_275=10, total_usable_330=5, total_revenue=75)
    test_db.add(invoice)
    test_db.commit()
    test_db.refresh(invoice)

    delete_invoice(test_db, invoice.id)

    assert test_db.query(Invoice).filter(Invoice.id == invoice.id).first() is None


def test_delete_invoice_raises_NotFoundError_when_id_not_found(test_db):
    with pytest.raises(NotFoundError):
        delete_invoice(test_db, "nonexistent-id")


# ---- Task 27: toggle_invoice_sent ----

def test_toggle_invoice_sent_sets_sent_at_when_currently_none(test_db):
    invoice = Invoice(month=date(2026, 3, 1), gradeout_count=1,
                      total_usable_275=10, total_usable_330=5, total_revenue=75)
    test_db.add(invoice)
    test_db.commit()
    test_db.refresh(invoice)

    updated = toggle_invoice_sent(test_db, invoice.id)
    assert updated.sent_at is not None


def test_toggle_invoice_sent_clears_sent_at_when_currently_set(test_db):
    invoice = Invoice(month=date(2026, 3, 1), gradeout_count=1,
                      total_usable_275=10, total_usable_330=5, total_revenue=75,
                      sent_at=datetime(2026, 3, 15, 10, 0, 0))
    test_db.add(invoice)
    test_db.commit()
    test_db.refresh(invoice)

    updated = toggle_invoice_sent(test_db, invoice.id)
    assert updated.sent_at is None


def test_toggle_invoice_sent_raises_NotFoundError_when_invoice_not_found(test_db):
    with pytest.raises(NotFoundError):
        toggle_invoice_sent(test_db, "nonexistent-id")


# ---- Task 28: route tests ----

def _seed_supplier_gradeout(db):
    supplier = Supplier(company_name="Acme Co", location="Toledo, OH")
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    db.add(Gradeout(
        supplier_id=supplier.id,
        date_received=date(2026, 3, 10),
        totes_275_total_usable=10,
        totes_330_total_usable=5,
    ))
    db.commit()
    return supplier


def test_get_invoices_preview_returns_200_with_html(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    _seed_supplier_gradeout(db)

    resp = client.get("/invoices/preview?month=2026-03")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Invoice Preview" in resp.text


def test_post_generate_or_confirm_saves_and_returns_hx_redirect_when_no_existing(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    _seed_supplier_gradeout(db)

    resp = client.post("/invoices/generate-or-confirm", data={"month": "2026-03"})
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/invoices"


def test_post_generate_or_confirm_returns_overwrite_confirm_when_invoice_exists(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    _seed_supplier_gradeout(db)
    db.add(Invoice(month=date(2026, 3, 1), gradeout_count=1,
                   total_usable_275=10, total_usable_330=5, total_revenue=75))
    db.commit()

    resp = client.post("/invoices/generate-or-confirm", data={"month": "2026-03"})
    assert resp.status_code == 200
    assert "Overwrite" in resp.text


def test_post_overwrite_overwrites_existing_invoice_and_returns_hx_redirect(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    _seed_supplier_gradeout(db)
    db.add(Invoice(month=date(2026, 3, 1), gradeout_count=1,
                   total_usable_275=10, total_usable_330=5, total_revenue=75))
    db.commit()

    resp = client.post("/invoices/overwrite", data={"month": "2026-03"})
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/invoices"


def test_delete_invoice_route_deletes_and_returns_hx_redirect(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    invoice = Invoice(month=date(2026, 3, 1), gradeout_count=1,
                      total_usable_275=10, total_usable_330=5, total_revenue=75)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    resp = client.delete(f"/invoices/{invoice.id}")
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/invoices"


def test_delete_invoice_route_returns_404_when_not_found(authenticated_client):
    resp = authenticated_client.delete("/invoices/nonexistent-id")
    assert resp.status_code == 404


def test_get_invoice_image_returns_200_with_png_content_type(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    _seed_supplier_gradeout(db)
    invoice = Invoice(month=date(2026, 3, 1), gradeout_count=1,
                      total_usable_275=10, total_usable_330=5, total_revenue=75)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    resp = client.get(f"/invoices/{invoice.id}/image")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_get_invoice_image_returns_404_when_invoice_not_found(authenticated_client):
    resp = authenticated_client.get("/invoices/nonexistent-id/image")
    assert resp.status_code == 404
