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


class TestDeleteMeRevokesToken:
    """FIX 2: DELETE /users/me debe revocar el access token activo."""

    def setup_method(self):
        _clear_blacklist()

    def test_token_revoked_after_delete_me(self, client, temp_data_path):
        """Tras DELETE /users/me el mismo token retorna 401."""
        _register(client, "delme_user", "delme@example.com", "Testpass1")
        token = _login(client, "delme@example.com", "Testpass1")

        # Token funciona antes de eliminar
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

        # Eliminar cuenta
        r = client.delete("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204

        # El mismo token debe estar revocado
        r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


class TestLogoutRevokesRefreshToken:
    """FIX 3: Logout con refresh_token en body debe revocar ese refresh token."""

    def setup_method(self):
        _clear_blacklist()

    def _login_full(self, client, email: str, password: str = "Aa123456!") -> dict:
        """Retorna access_token y refresh_token."""
        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, f"login failed: {r.text}"
        return r.json()

    def test_logout_without_refresh_token_still_revokes_access(self, client, temp_data_path):
        """Logout sin body sigue revocando el access token (compatibilidad)."""
        tokens = self._login_full(client, "alice@example.com")
        access = tokens["access_token"]

        r = client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200

        r = client.get("/users/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 401

    def test_logout_with_refresh_token_revokes_refresh(self, client, temp_data_path):
        """Logout con refresh_token hace que POST /auth/refresh devuelva 401."""
        tokens = self._login_full(client, "alice@example.com")
        access = tokens["access_token"]
        refresh = tokens["refresh_token"]

        # Logout incluyendo el refresh token
        r = client.post(
            "/auth/logout",
            json={"refresh_token": refresh},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert r.status_code == 200

        # Intentar usar el refresh token revocado
        r = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401

    def test_logout_with_invalid_refresh_token_still_succeeds(self, client, temp_data_path):
        """Logout con refresh_token inválido no falla — se ignora silenciosamente."""
        tokens = self._login_full(client, "alice@example.com")
        access = tokens["access_token"]

        r = client.post(
            "/auth/logout",
            json={"refresh_token": "token.invalido.aqui"},
            headers={"Authorization": f"Bearer {access}"},
        )
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
