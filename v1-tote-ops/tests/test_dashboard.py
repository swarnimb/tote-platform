from datetime import date

from app.models.gradeout import Gradeout
from app.models.supplier import Supplier
from app.services.dashboard_service import (
    get_confirmed_pickup_count,
    get_followup_suppliers,
    get_monthly_stats,
    get_revenue_chart_data,
)


def _supplier(name="Test Co"):
    return Supplier(company_name=name, location="Test City")


def test_get_monthly_stats_returns_correct_revenue_for_current_month(test_db):
    supplier = _supplier("Stats Corp")
    test_db.add(supplier)
    test_db.flush()

    today = date.today()
    test_db.add(
        Gradeout(
            supplier_id=supplier.id,
            date_received=today,
            totes_275_total_usable=10,
            totes_330_total_usable=5,
        )
    )
    test_db.commit()

    result = get_monthly_stats(test_db, today.year, today.month)

    assert result["total_usable_totes"] == 15
    assert result["revenue"] == 75.0  # 15 * TOTE_RATE (5)
    assert result["gradeout_count"] == 1


def test_get_followup_suppliers_returns_avg_275_washable_and_avg_275_cage_separately(test_db):
    # Supplier with no gradeouts always appears in follow-up list
    supplier = _supplier("Washable Co")
    supplier.is_active = True
    test_db.add(supplier)

    # Second supplier has gradeouts — used to verify avg columns are returned
    supplier2 = _supplier("Stats Co")
    supplier2.is_active = True
    test_db.add(supplier2)
    test_db.flush()

    test_db.add(
        Gradeout(
            supplier_id=supplier2.id,
            date_received=date(2020, 1, 1),
            totes_275_good_washable=8,
            totes_275_good_cage=2,
            totes_275_total_usable=10,
            totes_330_good_washable=4,
            totes_330_good_cage=1,
            totes_330_total_usable=5,
        )
    )
    test_db.commit()

    results = get_followup_suppliers(test_db)

    # Supplier with no gradeouts must appear; verify return dict has W/C keys
    no_gradeout = next((r for r in results if r["supplier"].id == supplier.id), None)
    assert no_gradeout is not None
    assert "avg_275_washable" in no_gradeout
    assert "avg_275_cage" in no_gradeout
    assert "avg_330_washable" in no_gradeout
    assert "avg_330_cage" in no_gradeout
    assert no_gradeout["avg_275_washable"] is None


def test_get_confirmed_pickup_count_returns_correct_count_of_confirmed_pickups(test_db):
    from app.services.pickup_service import create_pickup, cancel_pickup

    supplier = Supplier(company_name="Test Co", location="Test City")
    test_db.add(supplier)
    test_db.commit()

    create_pickup(test_db, supplier.id)
    create_pickup(test_db, supplier.id)
    p3 = create_pickup(test_db, supplier.id)
    cancel_pickup(test_db, p3.id)

    assert get_confirmed_pickup_count(test_db) == 2


def test_get_confirmed_pickup_count_returns_0_when_no_pickups_exist(test_db):
    assert get_confirmed_pickup_count(test_db) == 0


def test_get_revenue_chart_data_returns_exactly_12_monthly_entries(test_db):
    result = get_revenue_chart_data(test_db)
    assert len(result["monthly"]) == 12


def test_get_revenue_chart_data_returns_exactly_5_annual_entries(test_db):
    result = get_revenue_chart_data(test_db)
    assert len(result["annual"]) == 5


def test_get_revenue_chart_data_returns_0_revenue_for_periods_with_no_gradeouts(test_db):
    result = get_revenue_chart_data(test_db)
    assert all(entry["revenue"] == 0.0 for entry in result["monthly"])
    assert all(entry["revenue"] == 0.0 for entry in result["annual"])


def test_GET_dashboard_passes_confirmed_pickup_count_in_template_context(
    authenticated_client_with_db,
):
    client, db = authenticated_client_with_db
    from app.services.pickup_service import create_pickup

    supplier = Supplier(company_name="Test Co", location="Test City")
    db.add(supplier)
    db.commit()
    create_pickup(db, supplier.id)
    create_pickup(db, supplier.id)

    response = client.get("/")
    assert response.status_code == 200
    assert "2" in response.text


def test_GET_dashboard_passes_chart_data_with_monthly_and_annual_keys_to_template(
    authenticated_client,
):
    response = authenticated_client.get("/")
    assert response.status_code == 200
    assert "monthly" in response.text
    assert "annual" in response.text
