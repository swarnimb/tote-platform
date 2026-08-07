import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Gradeout, Pickup, Supplier


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_supplier_instantiates_with_required_fields(db):
    s = Supplier(company_name="Acme Corp", location="Chicago, IL")
    db.add(s)
    db.commit()

    assert s.id is not None
    assert s.company_name == "Acme Corp"
    assert s.location == "Chicago, IL"
    assert s.is_deleted is False
    assert s.is_hazmat is False


def test_gradeout_instantiates_with_required_fields(db):
    supplier = Supplier(company_name="Acme Corp", location="Chicago, IL")
    db.add(supplier)
    db.commit()

    gradeout = Gradeout(
        supplier_id=supplier.id,
        date_received=datetime.date.today(),
    )
    db.add(gradeout)
    db.commit()

    assert gradeout.id is not None
    assert gradeout.supplier_id == supplier.id


def test_pickup_instantiates_with_supplier_id_and_status_defaults_to_confirmed(db):
    supplier = Supplier(company_name="Acme Corp", location="Chicago, IL")
    db.add(supplier)
    db.commit()

    pickup = Pickup(supplier_id=supplier.id)
    db.add(pickup)
    db.commit()

    assert pickup.id is not None
    assert pickup.supplier_id == supplier.id
    assert pickup.status == "confirmed"


def test_gradeout_accepts_nullable_pickup_id(db):
    supplier = Supplier(company_name="Acme Corp", location="Chicago, IL")
    db.add(supplier)
    db.commit()

    gradeout = Gradeout(supplier_id=supplier.id, date_received=datetime.date.today())
    db.add(gradeout)
    db.commit()

    assert gradeout.pickup_id is None
