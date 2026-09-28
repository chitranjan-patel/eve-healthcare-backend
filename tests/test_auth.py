from tests.conftest import auth_headers


def test_signup_and_login(client):
    headers = auth_headers(client)
    assert "Authorization" in headers


def test_duplicate_signup(client):
    auth_headers(client, email="dup@example.com")
    again = client.post(
        "/auth/signup",
        json={"email": "dup@example.com", "password": "password123", "full_name": "Dup"},
    )
    assert again.status_code == 409


def test_login_invalid_password(client):
    auth_headers(client, email="badpass@example.com")
    resp = client.post("/auth/login", json={"email": "badpass@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_protected_route_without_token(client):
    resp = client.get("/centres/")
    assert resp.status_code == 401
