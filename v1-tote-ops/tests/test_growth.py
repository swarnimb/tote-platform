import uuid
from datetime import date, timedelta

import pytest

from app.models.app_settings import AppSettings
from app.models.gradeout import Gradeout
from app.models.supplier import Supplier
from app.services import growth_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_supplier(db, active=True):
    s = Supplier(
        id=str(uuid.uuid4()),
        company_name="Test Supplier",
        location="Toronto",
        is_active=active,
        is_deleted=False,
    )
    db.add(s)
    db.flush()
    return s


def make_gradeout(db, supplier_id, days_ago=10, usable_275=10, usable_330=5):
    g = Gradeout(
        id=str(uuid.uuid4()),
        supplier_id=supplier_id,
        date_received=date.today() - timedelta(days=days_ago),
        totes_275_total_usable=usable_275,
        totes_330_total_usable=usable_330,
        totes_275_good_washable=usable_275,
        totes_275_good_cage=0,
        totes_330_good_washable=usable_330,
        totes_330_good_cage=0,
        junk=0,
    )
    db.add(g)
    db.flush()
    return g


# ---------------------------------------------------------------------------
# AppSettings model
# ---------------------------------------------------------------------------

def test_app_settings_instantiates(test_db):
    row = AppSettings(key="test_key", value="test_value")
    test_db.add(row)
    test_db.commit()
    result = test_db.query(AppSettings).filter_by(key="test_key").first()
    assert result.value == "test_value"


def test_app_settings_duplicate_key_raises(test_db):
    from sqlalchemy.exc import IntegrityError
    test_db.add(AppSettings(key="dup_key", value="v1"))
    test_db.commit()
    test_db.add(AppSettings(key="dup_key", value="v2"))
    with pytest.raises(IntegrityError):
        test_db.commit()


# ---------------------------------------------------------------------------
# growth_service — get_avg_shipments_per_supplier
# ---------------------------------------------------------------------------

def test_get_avg_shipments_per_supplier_returns_correct_average(test_db):
    s1 = make_supplier(test_db)
    s2 = make_supplier(test_db)
    make_gradeout(test_db, s1.id, days_ago=10)
    make_gradeout(test_db, s1.id, days_ago=20)
    make_gradeout(test_db, s2.id, days_ago=5)
    # s1 has 2 gradeouts, s2 has 1 → avg = 1.5
    result = growth_service.get_avg_shipments_per_supplier(test_db)
    assert result == 1.5


def test_get_avg_shipments_per_supplier_returns_default_when_no_gradeouts(test_db):
    # Function returns 4.0 as a sensible UI default when no data exists
    result = growth_service.get_avg_shipments_per_supplier(test_db)
    assert result == 4.0


# ---------------------------------------------------------------------------
# growth_service — get_avg_totes_per_shipment
# ---------------------------------------------------------------------------

def test_get_avg_totes_per_shipment_returns_correct_average(test_db):
    s = make_supplier(test_db)
    make_gradeout(test_db, s.id, usable_275=10, usable_330=5)   # total 15
    make_gradeout(test_db, s.id, usable_275=20, usable_330=5)   # total 25
    # avg = 20.0
    result = growth_service.get_avg_totes_per_shipment(test_db)
    assert result == 20.0


def test_get_avg_totes_per_shipment_returns_zero_when_no_gradeouts(test_db):
    result = growth_service.get_avg_totes_per_shipment(test_db)
    assert result == 0.0


# ---------------------------------------------------------------------------
# growth_service — set_setting / get_setting
# ---------------------------------------------------------------------------

def test_set_setting_creates_new_key(test_db):
    growth_service.set_setting(test_db, "growth_target", "30000.0")
    result = growth_service.get_setting(test_db, "growth_target")
    assert result == "30000.0"


def test_set_setting_updates_existing_key_without_duplicate(test_db):
    growth_service.set_setting(test_db, "growth_target", "20000.0")
    growth_service.set_setting(test_db, "growth_target", "40000.0")
    rows = test_db.query(AppSettings).filter_by(key="growth_target").all()
    assert len(rows) == 1
    assert rows[0].value == "40000.0"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def test_post_growth_target_saves_and_redirects(authenticated_client):
    response = authenticated_client.post(
        "/growth/target", data={"target": "30000"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/growth"


def test_post_growth_target_rejects_negative_value(authenticated_client):
    response = authenticated_client.post(
        "/growth/target", data={"target": "-500"}, follow_redirects=False
    )
    assert response.status_code == 422
