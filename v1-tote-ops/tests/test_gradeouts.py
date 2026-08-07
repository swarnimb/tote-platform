import pytest

from app.models.supplier import Supplier
from app.services.gradeout_service import create_gradeout


def _make_supplier(db, **overrides):
    data = {"company_name": "Test Co", "location": "Cleveland, OH"}
    data.update(overrides)
    supplier = Supplier(**data)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def _gradeout_data(supplier_id, **overrides):
    data = {
        "supplier_id": supplier_id,
        "date_received": "2026-03-10",
        "totes_275_good_washable": "10",
        "totes_275_good_cage": "5",
        "totes_330_good_washable": "3",
        "totes_330_good_cage": "2",
        "junk": "2",
    }
    data.update(overrides)
    return data


def test_create_gradeout_saves_record_with_correct_supplier(test_db):
    supplier = _make_supplier(test_db)
    data = _gradeout_data(supplier.id)

    gradeout = create_gradeout(test_db, data)

    assert gradeout.supplier_id == supplier.id
    assert gradeout.id is not None


def test_create_gradeout_raises_ValueError_when_supplier_id_is_missing(test_db):
    with pytest.raises(ValueError, match="supplier_id is required"):
        create_gradeout(test_db, {"supplier_id": "", "date_received": "2026-03-10"})


def test_create_gradeout_raises_ValueError_when_supplier_not_found(test_db):
    with pytest.raises(ValueError, match="Supplier not found"):
        create_gradeout(test_db, _gradeout_data("nonexistent-id"))


def test_create_gradeout_sets_supplier_last_pickup_date_and_resets_action_stage(test_db):
    from datetime import date
    supplier = _make_supplier(test_db)
    supplier.last_action_stage = "followed_up"
    test_db.commit()

    create_gradeout(test_db, _gradeout_data(supplier.id, date_received="2026-03-10"))

    test_db.refresh(supplier)
    assert supplier.last_pickup_date == date(2026, 3, 10)
    assert supplier.last_action_stage is None
    assert supplier.last_action_date is None


def test_create_gradeout_succeeds_with_pickup_id_None_when_no_confirmed_pickups_exist(test_db):
    supplier = _make_supplier(test_db)
    gradeout = create_gradeout(test_db, _gradeout_data(supplier.id))
    assert gradeout.pickup_id is None


def test_create_gradeout_auto_links_single_confirmed_pickup_and_marks_it_completed(test_db):
    from app.services.pickup_service import create_pickup

    supplier = _make_supplier(test_db)
    pickup = create_pickup(test_db, supplier.id)

    gradeout = create_gradeout(test_db, _gradeout_data(supplier.id))

    test_db.refresh(pickup)
    assert gradeout.pickup_id == pickup.id
    assert pickup.status == "completed"


def test_create_gradeout_raises_ValueError_when_multiple_confirmed_pickups_exist_and_no_pickup_id_provided(
    test_db,
):
    from app.services.pickup_service import create_pickup
    import pytest

    supplier = _make_supplier(test_db)
    create_pickup(test_db, supplier.id)
    create_pickup(test_db, supplier.id)

    with pytest.raises(ValueError, match="Select which pickup this gradeout belongs to"):
        create_gradeout(test_db, _gradeout_data(supplier.id))


def test_create_gradeout_sets_gradeout_pickup_id_when_pickup_is_linked(test_db):
    from app.services.pickup_service import create_pickup

    supplier = _make_supplier(test_db)
    pickup = create_pickup(test_db, supplier.id)

    gradeout = create_gradeout(test_db, _gradeout_data(supplier.id, pickup_id=pickup.id))

    assert gradeout.pickup_id == pickup.id


def test_post_gradeouts_returns_422_when_tote_275_total_usable_is_negative(
    authenticated_client_with_db,
):
    client, db = authenticated_client_with_db
    supplier = _make_supplier(db)

    response = client.post(
        "/gradeouts",
        data={
            "supplier_id": supplier.id,
            "date_received": "2026-03-10",
            "totes_275_good_washable": "-1",
            "totes_275_good_cage": "3",
            "totes_330_good_washable": "0",
            "totes_330_good_cage": "0",
            "junk": "0",
        },
        follow_redirects=False,
    )
    assert response.status_code == 422
