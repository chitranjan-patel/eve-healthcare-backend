from tests.conftest import auth_headers, future_iso


def _create_pending_booking(client, headers):
    resp = client.post(
        "/bookings/",
        headers=headers,
        json={
            "centre_id": str(client.centre.id),
            "centre_test_id": str(client.test.id),
            "appointment_at": future_iso(),
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_payment_success_confirms_booking(client):
    headers = auth_headers(client)
    booking = _create_pending_booking(client, headers)

    payment = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "force_status": "SUCCESS"},
    )
    assert payment.status_code == 201, payment.text
    assert payment.json()["status"] == "SUCCESS"

    fetched = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert fetched.json()["status"] == "CONFIRMED"


def test_payment_failure_fails_booking(client):
    headers = auth_headers(client, email="failpay@example.com")
    booking = _create_pending_booking(client, headers)

    payment = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "force_status": "FAILED"},
    )
    assert payment.status_code == 201
    assert payment.json()["status"] == "FAILED"

    fetched = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert fetched.json()["status"] == "FAILED"


def test_double_payment_rejected(client):
    headers = auth_headers(client, email="double@example.com")
    booking = _create_pending_booking(client, headers)
    first = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "force_status": "SUCCESS"},
    )
    assert first.status_code == 201
    second = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "force_status": "SUCCESS"},
    )
    assert second.status_code == 409


def test_webhook_updates_and_is_idempotent(client):
    headers = auth_headers(client, email="webhook@example.com")
    booking = _create_pending_booking(client, headers)
    payment = client.post(
        "/payments/",
        headers=headers,
        json={"booking_id": booking["id"], "force_status": "FAILED"},
    ).json()

    webhook_body = {
        "event_id": "evt_123",
        "provider_payment_id": payment["provider_payment_id"],
        "status": "SUCCESS",
    }
    secret = {"X-Webhook-Secret": "test-webhook-secret"}

    first = client.post("/payments/webhook/", json=webhook_body, headers=secret)
    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert first.json()["booking_status"] == "CONFIRMED"

    second = client.post("/payments/webhook/", json=webhook_body, headers=secret)
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"

    fetched = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert fetched.json()["status"] == "CONFIRMED"


def test_webhook_invalid_secret(client):
    resp = client.post(
        "/payments/webhook/",
        json={"event_id": "evt_x", "provider_payment_id": "pay_x", "status": "SUCCESS"},
        headers={"X-Webhook-Secret": "wrong"},
    )
    assert resp.status_code == 401


def test_webhook_unknown_payment(client):
    resp = client.post(
        "/payments/webhook/",
        json={"event_id": "evt_missing", "provider_payment_id": "pay_missing", "status": "SUCCESS"},
        headers={"X-Webhook-Secret": "test-webhook-secret"},
    )
    assert resp.status_code == 404
