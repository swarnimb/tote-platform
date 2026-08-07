"""Supplier service and route tests — Tasks 8 and 9."""
import urllib.parse

import pytest

from app.models.supplier import Supplier
from app.models.gradeout import Gradeout
from app.services.supplier_service import (
    NotFoundError,
    build_followup_mailto,
    create_supplier,
    get_supplier_by_id,
    get_supplier_gradeout_stats,
    get_suppliers,
    set_supplier_action_stage,
    soft_delete_supplier,
)


def _supplier_data(**overrides):
    base = {"company_name": "Test Co", "location": "Test City"}
    base.update(overrides)
    return base


def test_create_supplier_saves_record_with_required_fields(test_db):
    supplier = create_supplier(test_db, _supplier_data())

    assert supplier.id is not None
    assert supplier.company_name == "Test Co"
    assert supplier.location == "Test City"
    assert supplier.is_deleted is False


def test_create_supplier_raises_ValueError_when_company_name_is_empty(test_db):
    with pytest.raises(ValueError, match="company_name is required"):
        create_supplier(test_db, _supplier_data(company_name=""))


def test_soft_delete_supplier_sets_is_deleted_True(test_db):
    supplier = create_supplier(test_db, _supplier_data())

    soft_delete_supplier(test_db, supplier.id)

    test_db.refresh(supplier)
    assert supplier.is_deleted is True
    assert supplier.deleted_at is not None


def test_get_suppliers_excludes_soft_deleted_records(test_db):
    supplier = create_supplier(test_db, _supplier_data())
    soft_delete_supplier(test_db, supplier.id)

    result = get_suppliers(test_db)

    assert all(s.id != supplier.id for s in result)


def test_get_suppliers_filters_by_action_stage_correctly(test_db):
    s1 = create_supplier(test_db, _supplier_data(company_name="Stage Co"))
    s2 = create_supplier(test_db, _supplier_data(company_name="Confirmed Co"))
    set_supplier_action_stage(test_db, s2.id, "pickup_confirmed")

    result = get_suppliers(test_db, action_stage="pickup_confirmed", active_only=False)

    assert len(result) == 1
    assert result[0].company_name == "Confirmed Co"


def test_get_suppliers_excludes_inactive_suppliers_when_active_only_is_True(test_db):
    from app.services.supplier_service import toggle_supplier_active
    active = create_supplier(test_db, _supplier_data(company_name="Active Co"))
    inactive = create_supplier(test_db, _supplier_data(company_name="Inactive Co"))
    toggle_supplier_active(test_db, inactive.id)

    result = get_suppliers(test_db, active_only=True)

    ids = [s.id for s in result]
    assert active.id in ids
    assert inactive.id not in ids


def test_get_suppliers_includes_inactive_suppliers_when_active_only_is_False(test_db):
    from app.services.supplier_service import toggle_supplier_active
    active = create_supplier(test_db, _supplier_data(company_name="Active Co"))
    inactive = create_supplier(test_db, _supplier_data(company_name="Inactive Co"))
    toggle_supplier_active(test_db, inactive.id)

    result = get_suppliers(test_db, active_only=False)

    ids = [s.id for s in result]
    assert active.id in ids
    assert inactive.id in ids


# --- Task 9 tests ---


def test_build_followup_mailto_returns_correctly_encoded_mailto_url(test_db):
    supplier = create_supplier(
        test_db,
        _supplier_data(company_name="Acme Corp", email="contact@acme.com", contact_name="Jane"),
    )

    result = build_followup_mailto(supplier, days_since=90)

    assert result.startswith("mailto:contact@acme.com?")
    assert "Acme+Corp" in result or "Acme%20Corp" in result
    assert "pickup" in result or "pickup" in urllib.parse.unquote(result)


def test_build_followup_mailto_uses_standard_message(test_db):
    supplier = create_supplier(test_db, _supplier_data())

    result = build_followup_mailto(supplier, days_since=None)

    assert "Hi" in urllib.parse.unquote(result)
    assert "totes" in urllib.parse.unquote(result)


def test_get_supplier_gradeout_stats_returns_avg_275_washable_and_avg_275_cage_separately(test_db):
    from datetime import date
    supplier = create_supplier(test_db, _supplier_data(company_name="Stats Co"))
    test_db.add(
        Gradeout(
            supplier_id=supplier.id,
            date_received=date.today(),
            totes_275_good_washable=6,
            totes_275_good_cage=4,
            totes_275_total_usable=10,
            totes_330_good_washable=3,
            totes_330_good_cage=2,
            totes_330_total_usable=5,
        )
    )
    test_db.commit()

    stats = get_supplier_gradeout_stats(test_db, [supplier.id])
    s = stats[supplier.id]

    assert s["avg_275_washable"] == 6
    assert s["avg_275_cage"] == 4
    assert s["avg_330_washable"] == 3
    assert s["avg_330_cage"] == 2


def test_set_supplier_action_stage_sets_stage_and_todays_date(test_db):
    from datetime import date
    supplier = create_supplier(test_db, _supplier_data())

    set_supplier_action_stage(test_db, supplier.id, "followed_up")

    test_db.refresh(supplier)
    assert supplier.last_action_stage == "followed_up"
    assert supplier.last_action_date == date.today()


def test_set_supplier_action_stage_with_empty_string_clears_both_fields(test_db):
    supplier = create_supplier(test_db, _supplier_data())
    set_supplier_action_stage(test_db, supplier.id, "followed_up")

    set_supplier_action_stage(test_db, supplier.id, "")

    test_db.refresh(supplier)
    assert supplier.last_action_stage is None
    assert supplier.last_action_date is None


def test_set_supplier_action_stage_raises_NotFoundError_for_missing_supplier(test_db):
    with pytest.raises(NotFoundError):
        set_supplier_action_stage(test_db, "nonexistent-id", "followed_up")


def test_PATCH_action_stage_sets_stage_and_returns_200(authenticated_client_with_db):
    from app.services.supplier_service import create_supplier
    client, db = authenticated_client_with_db
    supplier = create_supplier(db, {"company_name": "Stage Co", "location": "Toronto"})

    response = client.patch(
        f"/suppliers/{supplier.id}/action-stage",
        data={"last_action_stage": "pickup_confirmed"},
    )

    assert response.status_code == 200
    db.refresh(supplier)
    assert supplier.last_action_stage == "pickup_confirmed"


def test_PATCH_action_stage_with_empty_value_clears_stage(authenticated_client_with_db):
    from app.services.supplier_service import create_supplier, set_supplier_action_stage
    client, db = authenticated_client_with_db
    supplier = create_supplier(db, {"company_name": "Clear Co", "location": "Toronto"})
    set_supplier_action_stage(db, supplier.id, "followed_up")

    response = client.patch(
        f"/suppliers/{supplier.id}/action-stage",
        data={"last_action_stage": ""},
    )

    assert response.status_code == 200
    db.refresh(supplier)
    assert supplier.last_action_stage is None


def test_GET_suppliers_id_returns_404_for_soft_deleted_supplier(test_db, authenticated_client):
    # Service: get_supplier_by_id raises NotFoundError after soft-delete
    supplier = create_supplier(test_db, _supplier_data(company_name="Gone Corp"))
    soft_delete_supplier(test_db, supplier.id)
    with pytest.raises(NotFoundError):
        get_supplier_by_id(test_db, supplier.id)

    # Route: GET /suppliers/{id} returns 404 for any missing supplier
    # (authenticated_client uses its own DB, so supplier.id is unknown to it — also 404)
    response = authenticated_client.get(f"/suppliers/{supplier.id}")
    assert response.status_code == 404


def test_GET_supplier_detail_passes_confirmed_pickup_count_in_template_context(
    authenticated_client_with_db,
):
    client, db = authenticated_client_with_db
    from app.services.supplier_service import create_supplier
    from app.services.pickup_service import create_pickup

    supplier = create_supplier(db, {"company_name": "Acme Corp", "location": "Chicago, IL"})
    create_pickup(db, supplier.id)
    create_pickup(db, supplier.id)

    response = client.get(f"/suppliers/{supplier.id}")
    assert response.status_code == 200
    assert "2 pickup(s) confirmed" in response.text
