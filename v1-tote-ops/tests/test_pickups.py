import pytest

from app.models.supplier import Supplier
from app.services.pickup_service import (
    NotFoundError,
    cancel_pickup,
    create_pickup,
    get_confirmed_pickup_count,
    get_confirmed_pickups_for_supplier,
)


def _make_supplier(db, company_name="Acme Corp", is_deleted=False):
    s = Supplier(company_name=company_name, location="Chicago, IL", is_deleted=is_deleted)
    db.add(s)
    db.commit()
    return s


# --- Service tests ---


def test_create_pickup_creates_pickup_with_status_confirmed_for_valid_supplier(test_db):
    supplier = _make_supplier(test_db)
    pickup = create_pickup(test_db, supplier.id)
    assert pickup.id is not None
    assert pickup.supplier_id == supplier.id
    assert pickup.status == "confirmed"


def test_create_pickup_raises_ValueError_when_supplier_not_found(test_db):
    with pytest.raises(ValueError, match="Supplier not found"):
        create_pickup(test_db, "nonexistent-id")


def test_create_pickup_raises_ValueError_when_supplier_is_soft_deleted(test_db):
    supplier = _make_supplier(test_db, is_deleted=True)
    with pytest.raises(ValueError, match="Supplier not found"):
        create_pickup(test_db, supplier.id)


def test_get_confirmed_pickups_for_supplier_returns_only_confirmed_pickups(test_db):
    supplier = _make_supplier(test_db)
    p1 = create_pickup(test_db, supplier.id)
    p2 = create_pickup(test_db, supplier.id)
    cancel_pickup(test_db, p2.id)

    result = get_confirmed_pickups_for_supplier(test_db, supplier.id)
    assert len(result) == 1
    assert result[0].id == p1.id


def test_get_confirmed_pickup_count_returns_correct_count(test_db):
    supplier = _make_supplier(test_db)
    create_pickup(test_db, supplier.id)
    create_pickup(test_db, supplier.id)
    p3 = create_pickup(test_db, supplier.id)
    cancel_pickup(test_db, p3.id)

    assert get_confirmed_pickup_count(test_db) == 2


def test_cancel_pickup_sets_status_to_cancelled(test_db):
    supplier = _make_supplier(test_db)
    pickup = create_pickup(test_db, supplier.id)
    cancel_pickup(test_db, pickup.id)
    test_db.refresh(pickup)
    assert pickup.status == "cancelled"


def test_cancel_pickup_raises_NotFoundError_when_pickup_id_not_found(test_db):
    with pytest.raises(NotFoundError):
        cancel_pickup(test_db, "nonexistent-id")


def test_cancel_pickup_raises_ValueError_when_pickup_is_already_completed(test_db):
    from app.models.pickup import Pickup

    supplier = _make_supplier(test_db)
    pickup = create_pickup(test_db, supplier.id)
    pickup.status = "completed"
    test_db.commit()

    with pytest.raises(ValueError, match="Cannot cancel a completed pickup"):
        cancel_pickup(test_db, pickup.id)


# --- Route tests ---


def test_DELETE_pickups_returns_200_with_HX_Redirect_on_success(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    supplier = _make_supplier(db)
    pickup = create_pickup(db, supplier.id)
    db.commit()

    response = client.delete(
        f"/pickups/{pickup.id}",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == "/"


def test_POST_pickups_redirects_to_supplier_detail_page_on_success(authenticated_client_with_db):
    client, db = authenticated_client_with_db
    supplier = _make_supplier(db)
    db.commit()

    response = client.post("/pickups", data={"supplier_id": supplier.id})
    assert response.status_code == 200
    assert f"/suppliers/{supplier.id}" in str(response.url)


def test_DELETE_pickups_returns_404_when_pickup_not_found(authenticated_client):
    response = authenticated_client.delete(
        "/pickups/nonexistent-id",
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 404
