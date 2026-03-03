# tests/test_token_blacklist.py
"""Token blacklist tests: verify logout and password change revoke access tokens."""
import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.utils.token_blacklist import _store, _lock


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _clear_blacklist():
    with _lock:
        _store.clear()


def _register(client, username: str, email: str, password: str = "Testpass1") -> None:
    r = client.post("/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, f"register failed: {r.text}"


def _login(client, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


class TestLogoutRevokesToken:
    def setup_method(self):
        _clear_blacklist()

    def test_token_works_before_logout(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_token_rejected_after_logout(self, client, temp_data_path):
        token = _login(client, "alice@example.com")

        # Logout — should revoke the token
        r = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

        # Same token should now be rejected
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
        assert "revocado" in r.json()["detail"].lower() or "revoked" in r.json()["detail"].lower() or "invalid" in r.json()["detail"].lower()

    def test_new_token_works_after_logout(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

        # Login again — new token must work
        new_token = _login(client, "alice@example.com")
        r = client.get("/users/me", headers={"Authorization": f"Bearer {new_token}"})
        assert r.status_code == 200


class TestChangePasswordRevokesToken:
    def setup_method(self):
        _clear_blacklist()

    def test_token_rejected_after_password_change(self, client, temp_data_path):
        # Register a fresh user so we can control the password
        _register(client, "pwuser", "pwuser@example.com", "OldPass1")
        token = _login(client, "pwuser@example.com", "OldPass1")

        # Confirm token works
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

        # Change password
        r = client.patch(
            "/auth/change-password",
            json={"old_password": "OldPass1", "new_password": "NewPass1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 204

        # Old token should now be blacklisted
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_new_token_works_after_password_change(self, client, temp_data_path):
        _register(client, "pwuser2", "pwuser2@example.com", "OldPass1")
        token = _login(client, "pwuser2@example.com", "OldPass1")

        client.patch(
            "/auth/change-password",
            json={"old_password": "OldPass1", "new_password": "NewPass1"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # New login with new password must succeed
        new_token = _login(client, "pwuser2@example.com", "NewPass1")
        r = client.get("/users/me", headers={"Authorization": f"Bearer {new_token}"})
        assert r.status_code == 200


class TestBlacklistInternals:
    def setup_method(self):
        _clear_blacklist()

    def test_revoke_and_is_revoked(self):
        import time
        from app.utils.token_blacklist import revoke, is_revoked

        jti = "test-jti-1"
        assert not is_revoked(jti)

        # Revoke with a future expiry
        revoke(jti, time.time() + 3600)
        assert is_revoked(jti)

    def test_expired_entry_not_revoked(self):
        import time
        from app.utils.token_blacklist import revoke, is_revoked

        jti = "test-jti-expired"
        # Revoke with an already-past expiry
        revoke(jti, time.time() - 1)
        # Should be evicted immediately on next is_revoked call
        assert not is_revoked(jti)
