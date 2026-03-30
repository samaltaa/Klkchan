# tests/test_ban_user.py
"""
Tests para la funcionalidad de ban real de usuario.

Verifica que ban_user marca is_banned=True sin borrar la cuenta,
que el usuario baneado no puede iniciar sesión ni usar tokens activos,
y que un admin puede seguir viéndolo en GET /admin/users.

TODO: Agregar endpoint de unban (PATCH /admin/users/{id}/unban) en
      una iteración futura. Actualmente, PATCH /admin/users/{id}/role
      cambia roles pero no des-banea.
"""
import pytest
from fastapi.testclient import TestClient

import app.services as services


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login falló ({r.status_code}): {r.text}"
    return r.json()["access_token"]


def _mod_token(client: TestClient) -> str:
    return _login(client, "mod@example.com")


def _admin_token(client: TestClient) -> str:
    return _login(client, "admin@example.com")


def _ban_user(client: TestClient, mod_token: str, user_id: int) -> dict:
    """Ejecuta la acción ban_user vía POST /moderation/actions."""
    r = client.post(
        "/moderation/actions",
        json={"target_type": "user", "target_id": user_id, "action": "ban_user"},
        headers={"Authorization": f"Bearer {mod_token}"},
    )
    assert r.status_code == 200, f"ban_user falló ({r.status_code}): {r.text}"
    return r.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ban_user_sets_is_banned_and_keeps_account(client: TestClient):
    """Mod banea usuario → is_banned=True en BD, la cuenta sigue existiendo."""
    mod_token = _mod_token(client)
    result = _ban_user(client, mod_token, user_id=3)

    assert result["applied"] is True
    assert "suspendido" in result["detail"].lower()

    # La cuenta sigue en la BD
    user = services.get_user(3)
    assert user is not None, "La cuenta fue borrada — debería seguir existiendo"
    assert user["is_banned"] is True


def test_banned_user_cannot_login(client: TestClient):
    """Usuario baneado intenta login → 403."""
    mod_token = _mod_token(client)
    _ban_user(client, mod_token, user_id=3)

    r = client.post("/auth/login", data={"username": "alice@example.com", "password": "Aa123456!"})
    assert r.status_code == 403
    assert "suspendida" in r.json()["detail"].lower()


def test_banned_user_active_token_rejected(client: TestClient):
    """Usuario con token activo es baneado → siguientes requests devuelven 403."""
    # 1. Alice obtiene token antes del ban
    alice_token = _login(client, "alice@example.com")
    auth = {"Authorization": f"Bearer {alice_token}"}

    # 2. Verificar que el token funciona
    r = client.get("/users/me", headers=auth)
    assert r.status_code == 200

    # 3. Un mod banea a alice
    mod_token = _mod_token(client)
    _ban_user(client, mod_token, user_id=3)

    # 4. El token activo ya no debe funcionar
    r2 = client.get("/users/me", headers=auth)
    assert r2.status_code == 403


def test_banned_user_cannot_reregister_same_email(client: TestClient):
    """Usuario baneado intenta registrarse con el mismo email → 400 (ya existe)."""
    mod_token = _mod_token(client)
    _ban_user(client, mod_token, user_id=3)

    # La cuenta existe (is_banned=True) → el registro debe rechazarlo por email duplicado
    r = client.post("/auth/register", json={
        "username": "alice_nueva",
        "email": "alice@example.com",
        "password": "NuevaPass1!",
    })
    assert r.status_code == 400
    assert "email" in r.json()["detail"].lower()


def test_admin_can_see_banned_user(client: TestClient):
    """Admin puede ver usuario baneado en GET /admin/users."""
    mod_token = _mod_token(client)
    _ban_user(client, mod_token, user_id=3)

    admin_token = _admin_token(client)
    r = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200

    users = r.json()["items"]
    alice = next((u for u in users if u["id"] == 3), None)
    assert alice is not None, "Alice no aparece en el listado de admin"
    assert alice["is_banned"] is True


def test_ban_removes_user_action_still_deletes(client: TestClient):
    """Acción 'remove' sobre usuario sigue eliminando la cuenta (comportamiento no cambiado)."""
    mod_token = _mod_token(client)
    r = client.post(
        "/moderation/actions",
        json={"target_type": "user", "target_id": 3, "action": "remove"},
        headers={"Authorization": f"Bearer {mod_token}"},
    )
    assert r.status_code == 200
    assert r.json()["applied"] is True

    # La cuenta ya no debe existir
    user = services.get_user(3)
    assert user is None, "La cuenta debería haber sido eliminada con 'remove'"
