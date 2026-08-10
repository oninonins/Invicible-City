import uuid


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def test_data_endpoints_require_auth(auth_client):
    resp = auth_client.get("/api/v1/cities/")
    assert resp.status_code == 401
    resp = auth_client.get("/api/v1/facilities/")
    assert resp.status_code == 401
    resp = auth_client.get("/api/v1/analytics/ufs?city_id=1")
    assert resp.status_code == 401
    resp = auth_client.get("/api/v1/analytics/recommendations?city_id=1")
    assert resp.status_code == 401


def test_invalid_token_rejected(auth_client):
    resp = auth_client.get(
        "/api/v1/cities/", headers={"Authorization": "Bearer not-a-valid-jwt"}
    )
    assert resp.status_code == 403


def test_register_login_and_access_data(auth_client):
    email = _unique_email("tester")
    reg = auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret123", "full_name": "Tester"},
    )
    assert reg.status_code == 200

    login = auth_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    resp = auth_client.get(
        "/api/v1/cities/", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


def test_login_wrong_password(auth_client):
    email = _unique_email("wrongpw")
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "okpass123", "full_name": "X"},
    )
    login = auth_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "wrongpass"},
    )
    assert login.status_code == 400
