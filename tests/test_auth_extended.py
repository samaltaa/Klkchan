# tests/test_auth_extended.py
"""Extended authentication tests."""
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.app import app
from app.utils.security import SECRET_KEY, ALGORITHM


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _register(client, username: str, email: str, password: str = "Testpass1"):
    r = client.post("/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, f"register failed: {r.text}"
    return r.json()


def _login(client, email: str, password: str):
    return client.post("/auth/login", data={"username": email, "password": password})


class TestLoginFailures:
    def test_login_with_wrong_password_fails(self, client, temp_data_path):
        r = _login(client, "alice@example.com", "WrongPassword1")
        assert r.status_code == 401

    def test_login_with_nonexistent_email_fails(self, client, temp_data_path):
        r = _login(client, "nobody@example.com", "SomePass1")
        assert r.status_code == 401

    def test_login_returns_token_pair(self, client, temp_data_path):
        r = _login(client, "alice@example.com", "Aa123456!")
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"


class TestRegisterValidation:
    def test_register_with_invalid_email_fails(self, client, temp_data_path):
        r = client.post(
            "/auth/register",
            json={"username": "baduser", "email": "not-an-email", "password": "Testpass1"},
        )
        assert r.status_code == 422

    def test_register_with_weak_password_fails(self, client, temp_data_path):
        # Password less than 8 characters
        r = client.post(
            "/auth/register",
            json={"username": "weakpwd", "email": "weak@example.com", "password": "abc"},
        )
        assert r.status_code == 422

    def test_register_with_no_uppercase_fails(self, client, temp_data_path):
        r = client.post(
            "/auth/register",
            json={"username": "nocase", "email": "nocase@example.com", "password": "alllower1"},
        )
        assert r.status_code in (400, 422)

    def test_register_duplicate_email_fails(self, client, temp_data_path):
        r = client.post(
            "/auth/register",
            json={"username": "alice2", "email": "alice@example.com", "password": "Testpass1"},
        )
        assert r.status_code == 400

    def test_register_duplicate_username_fails(self, client, temp_data_path):
        r = client.post(
            "/auth/register",
            json={"username": "alice", "email": "different@example.com", "password": "Testpass1"},
        )
        assert r.status_code == 400


class TestTokenSecurity:
    def test_malformed_token_fails(self, client, temp_data_path):
        r = client.get("/users/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert r.status_code == 401

    def test_token_signed_with_different_secret_fails(self, client, temp_data_path):
        """A token signed with a wrong key must be rejected."""
        fake_token = jwt.encode(
            {"sub": "1", "exp": 9999999999, "iss": "klkchan"},
            "wrong_secret_key",
            algorithm=ALGORITHM,
        )
        r = client.get("/users/me", headers={"Authorization": f"Bearer {fake_token}"})
        assert r.status_code == 401

    def test_no_token_fails(self, client, temp_data_path):
        r = client.get("/users/me")
        assert r.status_code == 401


class TestRefreshToken:
    def test_refresh_token_valid(self, client, temp_data_path):
        login_r = _login(client, "alice@example.com", "Aa123456!")
        assert login_r.status_code == 200
        refresh_token = login_r.json().get("refresh_token")
        if not refresh_token:
            pytest.skip("Refresh token not in login response")

        r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body

    def test_refresh_token_invalid_fails(self, client, temp_data_path):
        r = client.post("/auth/refresh", json={"refresh_token": "bad.refresh.token"})
        assert r.status_code == 401


class TestMultipleSessions:
    def test_multiple_concurrent_logins(self, client, temp_data_path):
        """Multiple logins for the same account should all produce valid tokens."""
        t1 = _login(client, "alice@example.com", "Aa123456!").json()["access_token"]
        t2 = _login(client, "alice@example.com", "Aa123456!").json()["access_token"]

        r1 = client.get("/users/me", headers={"Authorization": f"Bearer {t1}"})
        r2 = client.get("/users/me", headers={"Authorization": f"Bearer {t2}"})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["username"] == r2.json()["username"] == "alice"
