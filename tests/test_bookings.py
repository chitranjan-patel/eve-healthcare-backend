from tests.conftest import auth_headers, future_iso


def test_list_centres(client):
    headers = auth_headers(client)
    resp = client.get("/centres/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


def test_get_centre_and_tests(client):
    headers = auth_headers(client)
    centre_id = str(client.centre.id)
    detail = client.get(f"/centres/{centre_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Test Centre"
    assert len(detail.json()["tests"]) == 1

    tests = client.get(f"/centres/{centre_id}/tests", headers=headers)
    assert tests.status_code == 200
    assert tests.json()["total"] == 1


def test_create_and_get_booking(client):
    headers = auth_headers(client)
    payload = {
        "centre_id": str(client.centre.id),
        "centre_test_id": str(client.test.id),
        "appointment_at": future_iso(),
    }
    created = client.post("/bookings/", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["status"] == "PENDING"
    assert booking["amount"] == "500.00"

    fetched = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == booking["id"]


def test_cancel_booking(client):
    headers = auth_headers(client)
    created = client.post(
        "/bookings/",
        headers=headers,
        json={
            "centre_id": str(client.centre.id),
            "centre_test_id": str(client.test.id),
            "appointment_at": future_iso(),
        },
    )
    booking_id = created.json()["id"]
    cancelled = client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_booking_forbidden_for_other_user(client):
    headers_a = auth_headers(client, email="a@example.com")
    created = client.post(
        "/bookings/",
        headers=headers_a,
        json={
            "centre_id": str(client.centre.id),
            "centre_test_id": str(client.test.id),
            "appointment_at": future_iso(),
        },
    )
    booking_id = created.json()["id"]

    headers_b = auth_headers(client, email="b@example.com")
    resp = client.get(f"/bookings/{booking_id}", headers=headers_b)
    assert resp.status_code == 403
