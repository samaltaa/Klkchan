# tests/test_forgot_reset_password.py
"""
Tests para el flujo completo forgot-password / reset-password.
Requiere: alice (id=3) en el seed con email alice@example.com.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login falló: {r.text}"
    return r.json()["access_token"]


def _forgot(client: TestClient, email: str) -> dict:
    r = client.post("/auth/forgot-password", json={"email": email})
    assert r.status_code == 202
    return r.json()


def _reset(client: TestClient, token: str, new_password: str) -> dict:
    r = client.post("/auth/reset-password", json={
        "token": token,
        "new_password": new_password,
    })
    return r


# ---------------------------------------------------------------------------
# forgot-password
# ---------------------------------------------------------------------------

def test_forgot_password_existing_email_returns_token(client: TestClient):
    """Para un email existente se genera un reset_token en la respuesta."""
    data = _forgot(client, "alice@example.com")
    assert data["reset_token"] is not None
    assert len(data["reset_token"]) > 20  # es un JWT, no vacío


def test_forgot_password_unknown_email_returns_202_without_token(client: TestClient):
    """Para un email desconocido retorna 202 pero sin token (no revela existencia)."""
    data = _forgot(client, "noexiste@nada.com")
    assert data["reset_token"] is None


def test_forgot_password_always_202(client: TestClient):
    """El status siempre es 202 independientemente del email."""
    r = client.post("/auth/forgot-password", json={"email": "cualquiera@test.com"})
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# reset-password
# ---------------------------------------------------------------------------

def test_reset_password_valid_flow(client: TestClient):
    """Flujo completo: forgot → reset → login con nueva contraseña."""
    new_pw = "NuevaPass123!!"

    # 1. Obtener token de reset
    data = _forgot(client, "alice@example.com")
    reset_token = data["reset_token"]
    assert reset_token is not None

    # 2. Resetear contraseña
    r = _reset(client, reset_token, new_pw)
    assert r.status_code == 200
    assert r.json()["detail"] == "Password updated"

    # 3. Login con nueva contraseña funciona
    new_token = _login(client, "alice@example.com", new_pw)
    assert len(new_token) > 20


def test_reset_password_token_is_single_use(client: TestClient):
    """El mismo reset_token solo puede usarse una vez."""
    new_pw = "NuevaPass456!!"

    data = _forgot(client, "alice@example.com")
    reset_token = data["reset_token"]

    # Primer uso: ok
    r = _reset(client, reset_token, new_pw)
    assert r.status_code == 200

    # Segundo uso con el mismo token: debe fallar
    r2 = _reset(client, reset_token, "OtraPass789!!")
    assert r2.status_code == 400
    assert "utilizado" in r2.json()["detail"].lower()


def test_reset_password_invalid_token_fails(client: TestClient):
    """Token inventado retorna 400."""
    r = _reset(client, "not.a.real.token", "NuevaPass123!!")
    assert r.status_code == 400


def test_reset_password_weak_password_fails(client: TestClient):
    """Contraseña que no cumple la política retorna 422."""
    data = _forgot(client, "alice@example.com")
    reset_token = data["reset_token"]

    # Contraseña sin mayúscula
    r = _reset(client, reset_token, "solominusculas123456")
    assert r.status_code == 422


def test_reset_password_invalidates_active_sessions(client: TestClient):
    """Tras el reset, los access tokens anteriores son rechazados."""
    new_pw = "NuevaPass789!!"

    # 1. Login previo al reset
    old_token = _login(client, "alice@example.com")
    auth = {"Authorization": f"Bearer {old_token}"}

    # Verificar que el token funciona
    r = client.get("/users/me", headers=auth)
    assert r.status_code == 200

    # 2. Resetear contraseña
    data = _forgot(client, "alice@example.com")
    _reset(client, data["reset_token"], new_pw)

    # 3. El token anterior ya no debe funcionar
    r2 = client.get("/users/me", headers=auth)
    assert r2.status_code == 401
