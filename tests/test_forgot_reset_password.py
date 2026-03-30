# tests/test_forgot_reset_password.py
"""
Tests para el flujo completo forgot-password / reset-password.
Requiere: alice (id=3) en el seed con email alice@example.com.

Nota de seguridad (post-fix C-2):
  POST /auth/forgot-password ya NO devuelve el reset_token en el body.
  Para tests que necesitan el token se obtiene directamente del servicio
  de seguridad (app.utils.security.create_password_reset_token), simulando
  lo que haría la integración de email en producción (MODEL-32).
"""
import pytest
from fastapi.testclient import TestClient

from app.utils.security import create_password_reset_token
from app.services import get_user_by_email


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


def _get_reset_token_for(email: str) -> str:
    """
    Obtiene un token de reset directamente del servicio de seguridad.

    Simula lo que haría la integración de email en producción:
    el token se genera y se enviaría al usuario por email.
    En tests lo generamos directamente para poder probar /reset-password
    sin depender del response de /forgot-password.
    """
    user = get_user_by_email(email)
    assert user is not None, f"Usuario con email {email} no encontrado en el seed"
    token, _jti, _exp = create_password_reset_token(user["id"])
    return token


def _reset(client: TestClient, token: str, new_password: str):
    r = client.post("/auth/reset-password", json={
        "token": token,
        "new_password": new_password,
    })
    return r


# ---------------------------------------------------------------------------
# forgot-password — respuesta sin token
# ---------------------------------------------------------------------------

def test_forgot_password_existing_email_returns_message_not_token(client: TestClient):
    """Para un email existente retorna 202 con message — NO expone reset_token."""
    data = _forgot(client, "alice@example.com")
    assert "message" in data
    assert "reset_token" not in data


def test_forgot_password_unknown_email_returns_same_message(client: TestClient):
    """Para email desconocido retorna 202 con el mismo mensaje genérico (anti-enumeración)."""
    data = _forgot(client, "noexiste@nada.com")
    assert "message" in data
    assert "reset_token" not in data


def test_forgot_password_always_202(client: TestClient):
    """El status siempre es 202 independientemente del email."""
    r = client.post("/auth/forgot-password", json={"email": "cualquiera@test.com"})
    assert r.status_code == 202


def test_forgot_password_message_is_generic(client: TestClient):
    """El mensaje para email existente y no existente es idéntico (anti-enumeración)."""
    data_known = _forgot(client, "alice@example.com")
    data_unknown = _forgot(client, "noexiste@nada.com")
    assert data_known["message"] == data_unknown["message"]


# ---------------------------------------------------------------------------
# reset-password — sigue funcionando con token del servicio
# ---------------------------------------------------------------------------

def test_reset_password_valid_flow(client: TestClient):
    """Flujo completo: generar token internamente → reset → login con nueva contraseña."""
    new_pw = "NuevaPass123!!"

    # El token se obtiene del servicio, no del response de forgot-password
    reset_token = _get_reset_token_for("alice@example.com")

    r = _reset(client, reset_token, new_pw)
    assert r.status_code == 200
    assert r.json()["detail"] == "Password updated"

    new_token = _login(client, "alice@example.com", new_pw)
    assert len(new_token) > 20


def test_reset_password_token_is_single_use(client: TestClient):
    """El mismo reset_token solo puede usarse una vez."""
    new_pw = "NuevaPass456!!"

    reset_token = _get_reset_token_for("alice@example.com")

    r = _reset(client, reset_token, new_pw)
    assert r.status_code == 200

    r2 = _reset(client, reset_token, "OtraPass789!!")
    assert r2.status_code == 400
    assert "utilizado" in r2.json()["detail"].lower()


def test_reset_password_invalid_token_fails(client: TestClient):
    """Token inventado retorna 400."""
    r = _reset(client, "not.a.real.token", "NuevaPass123!!")
    assert r.status_code == 400


def test_reset_password_weak_password_fails(client: TestClient):
    """Contraseña que no cumple la política retorna 422."""
    reset_token = _get_reset_token_for("alice@example.com")

    r = _reset(client, reset_token, "solominusculas123456")
    assert r.status_code == 422


def test_reset_password_invalidates_active_sessions(client: TestClient):
    """Tras el reset, los access tokens anteriores son rechazados."""
    new_pw = "NuevaPass789!!"

    old_token = _login(client, "alice@example.com")
    auth = {"Authorization": f"Bearer {old_token}"}

    r = client.get("/users/me", headers=auth)
    assert r.status_code == 200

    reset_token = _get_reset_token_for("alice@example.com")
    _reset(client, reset_token, new_pw)

    r2 = client.get("/users/me", headers=auth)
    assert r2.status_code == 401
