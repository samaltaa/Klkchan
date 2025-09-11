# tests/test_users.py
import uuid

def _unique_user():
    suf = uuid.uuid4().hex[:6]
    return {
        "username": f"melvin_{suf}",
        "email": f"melvin_{suf}@example.com",
        "password": "Aa123456!",
    }

def test_register_user_success(client):
    payload = _unique_user()
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert "id" in data

def test_register_user_too_short_password(client):
    # Para disparar 422, hoy tu schema tiene min_length=8 -> usa menos de 8
    payload = _unique_user()
    payload["password"] = "12345"  # 5 chars -> 422 por min_length
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422, r.text
