"""Seed diagnostic centres and tests. Safe to run multiple times."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.cache import cache_delete_pattern
from app.db import SessionLocal, engine, Base
from app.models import CentreTest, DiagnosticCentre


SEED_DATA = [
    {
        "name": "EVE Diagnostics Koramangala",
        "location": "Koramangala, Bengaluru",
        "tests": [
            ("Complete Blood Count", Decimal("499.00")),
            ("Lipid Profile", Decimal("799.00")),
            ("HbA1c", Decimal("450.00")),
            ("Thyroid Panel (T3/T4/TSH)", Decimal("699.00")),
        ],
    },
    {
        "name": "EVE Diagnostics Indiranagar",
        "location": "Indiranagar, Bengaluru",
        "tests": [
            ("Complete Blood Count", Decimal("520.00")),
            ("Vitamin D", Decimal("999.00")),
            ("Liver Function Test", Decimal("650.00")),
            ("Kidney Function Test", Decimal("600.00")),
        ],
    },
    {
        "name": "EVE Diagnostics Whitefield",
        "location": "Whitefield, Bengaluru",
        "tests": [
            ("COVID RTPCR", Decimal("799.00")),
            ("Full Body Checkup", Decimal("2499.00")),
            ("ECG", Decimal("350.00")),
        ],
    },
]


def seed(db: Session) -> None:
    for centre_data in SEED_DATA:
        centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.name == centre_data["name"]).first()
        if centre is None:
            centre = DiagnosticCentre(name=centre_data["name"], location=centre_data["location"])
            db.add(centre)
            db.flush()

        for test_name, price in centre_data["tests"]:
            existing = (
                db.query(CentreTest)
                .filter(CentreTest.centre_id == centre.id, CentreTest.name == test_name)
                .first()
            )
            if existing is None:
                db.add(CentreTest(centre_id=centre.id, name=test_name, price=price, is_active=True))

    db.commit()
    cache_delete_pattern("centres:*")
    print("Seed completed.")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
