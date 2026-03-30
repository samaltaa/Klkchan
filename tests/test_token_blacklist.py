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


class TestDeletedUserTokenInvalid:
    """
    FIX 1 (Sprint 2.8): Tokens de usuarios eliminados deben retornar 401.

    deps.py verifica la existencia del usuario en BD tras decodificar el token.
    Si el usuario fue eliminado (por admin o por ban_user via moderation),
    get_user_by_id() retorna None y el dep lanza 401.
    No se necesita revocar el JTI explícitamente — la ausencia del usuario
    ya invalida cualquier token emitido para ese sub.
    """

    def setup_method(self):
        _clear_blacklist()

    def test_admin_delete_user_token_becomes_invalid(self, client, temp_data_path):
        """Admin elimina a alice → el token de alice retorna 401."""
        # Registrar un usuario temporal para no afectar seed
        _register(client, "victim1", "victim1@test.com", "Testpass1")
        victim_token = client.post(
            "/auth/login", data={"username": "victim1@test.com", "password": "Testpass1"}
        ).json()["access_token"]

        # Verificar que el token funciona antes de la eliminación
        r = client.get("/users/me", headers={"Authorization": f"Bearer {victim_token}"})
        assert r.status_code == 200

        # Admin elimina al usuario
        victim_id = r.json()["id"]
        admin_token = _login(client, "admin@example.com")
        r = client.delete(
            f"/admin/users/{victim_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 204

        # El token del usuario eliminado debe retornar 401
        r = client.get("/users/me", headers={"Authorization": f"Bearer {victim_token}"})
        assert r.status_code == 401

    def test_mod_ban_user_token_becomes_invalid(self, client, temp_data_path):
        """Mod banea (ban_user) a un usuario → el token del usuario retorna 403.

        Nota: a diferencia de delete (que retorna 401 porque el usuario ya no existe),
        ban_user marca is_banned=True sin borrar la cuenta. El access token sigue
        siendo válido criptográficamente, pero get_current_user devuelve 403 al
        detectar is_banned=True ("Tu cuenta ha sido suspendida").
        """
        # Registrar usuario temporal
        _register(client, "victim2", "victim2@test.com", "Testpass1")
        victim_token = client.post(
            "/auth/login", data={"username": "victim2@test.com", "password": "Testpass1"}
        ).json()["access_token"]

        victim_id = client.get(
            "/users/me", headers={"Authorization": f"Bearer {victim_token}"}
        ).json()["id"]

        # Mod ejecuta ban_user
        admin_token = _login(client, "admin@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "user", "target_id": victim_id, "action": "ban_user"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200
        assert r.json()["applied"] is True

        # El token del usuario baneado debe retornar 403 (suspendido, no eliminado)
        r = client.get("/users/me", headers={"Authorization": f"Bearer {victim_token}"})
        assert r.status_code == 403


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
