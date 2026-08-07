import pytest

from app.models.lead import Lead
from app.services.lead_service import (
    NotFoundError,
    build_supplier_prefill,
    create_lead,
    update_lead_status,
)


def _make_lead(db, **overrides):
    data = {"company_name": "Prospect Co", "location": "Akron, OH",
            "contact_name": "Jane Smith", "contact_phone": "555-1234",
            "contact_email": "jane@prospect.com"}
    data.update(overrides)
    return create_lead(db, data)


def test_create_lead_raises_ValueError_when_company_name_is_empty(test_db):
    with pytest.raises(ValueError, match="company_name is required"):
        create_lead(test_db, {"company_name": ""})


def test_update_lead_status_returns_should_prompt_convert_True_when_set_to_active_supplier(test_db):
    lead = _make_lead(test_db)
    _, should_convert = update_lead_status(test_db, lead.id, "active_supplier")
    assert should_convert is True


def test_update_lead_status_returns_should_prompt_convert_False_for_all_other_statuses(test_db):
    lead = _make_lead(test_db)
    for status in ("research", "contacted", "responded", "not_interested"):
        _, should_convert = update_lead_status(test_db, lead.id, status)
        assert should_convert is False, f"Expected False for status '{status}'"


def test_build_supplier_prefill_maps_all_contact_fields_correctly(test_db):
    lead = _make_lead(test_db)
    prefill = build_supplier_prefill(lead)

    assert prefill["company_name"] == lead.company_name
    assert prefill["location"] == lead.location
    assert prefill["contact_name"] == lead.contact_name
    assert prefill["phone"] == lead.contact_phone
    assert prefill["email"] == lead.contact_email
