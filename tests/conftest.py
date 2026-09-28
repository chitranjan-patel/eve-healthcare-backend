import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use SQLite for unit tests; override Postgres-specific types via create_all on mapped models.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("PAYMENT_SUCCESS_RATE", "1.0")

from app.config import get_settings
from app.db import Base, get_db
from app.main import app
from app.models import CentreTest, DiagnosticCentre

get_settings.cache_clear()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    centre = DiagnosticCentre(name="Test Centre", location="Test City")
    session.add(centre)
    session.flush()
    test = CentreTest(centre_id=centre.id, name="CBC", price=Decimal("500.00"), is_active=True)
    session.add(test)
    session.commit()

    yield session, centre, test
    session.close()


@pytest.fixture()
def client(db_session):
    session, centre, test = db_session

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        c.centre = centre
        c.test = test
        yield c
    app.dependency_overrides.clear()


def auth_headers(client: TestClient, email: str = "user@example.com") -> dict:
    signup = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "Test User"},
    )
    assert signup.status_code == 201, signup.text
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def future_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
