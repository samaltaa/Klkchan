"""
test_terms.py — Tests del sistema de Términos y Condiciones — KLKCHAN.

Cubre los endpoints GET /terms/latest, POST /terms/accept y GET /terms/status,
así como la dependency require_terms_accepted de app/deps.py.

Fixtures heredadas de conftest.py:
  - temp_data_path: redirige DATA_PATH a un archivo temporal y hace seed base.
  - client: TestClient de FastAPI con scope=module.

Convenciones:
  - Funciones de ayuda con prefijo _  (no son tests).
  - Cada test es independiente gracias a temp_data_path (scope=function).
"""
import json

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

import app_v1.services as services
from app_v1.app import app
from app_v1.deps import get_current_user, require_terms_accepted

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _get_token(client: TestClient, email: str = "alice@example.com", password: str = "Aa123456!") -> str:
    """Obtiene un access token para el usuario indicado (el campo username acepta email)."""
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _seed_active_terms(version: str = "v1.0", content_url: str = "https://example.com/terms/v1.0") -> dict:
    """Inserta un registro de T&C activo en los datos de prueba y retorna el dict."""
    data = services.load_data()
    data.setdefault("terms_and_conditions", [])
    data.setdefault("terms_acceptances", [])
    terms = {
        "id": 1,
        "version": version,
        "content_url": content_url,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00+00:00",
    }
    data["terms_and_conditions"].append(terms)
    services.save_data(data)
    return terms


def _seed_inactive_terms(version: str = "v0.9") -> dict:
    """Inserta un registro de T&C inactivo."""
    data = services.load_data()
    data.setdefault("terms_and_conditions", [])
    data.setdefault("terms_acceptances", [])
    terms = {
        "id": 2,
        "version": version,
        "content_url": "https://example.com/terms/v0.9",
        "is_active": False,
        "created_at": "2023-01-01T00:00:00+00:00",
    }
    data["terms_and_conditions"].append(terms)
    services.save_data(data)
    return terms


def _seed_acceptance(user_id: int, terms_id: int) -> dict:
    """Registra manualmente una aceptación en los datos de prueba."""
    data = services.load_data()
    data.setdefault("terms_acceptances", [])
    acceptance = {
        "id": len(data["terms_acceptances"]) + 1,
        "user_id": user_id,
        "terms_id": terms_id,
        "ip_address": "127.0.0.1",
        "accepted_at": "2024-06-01T00:00:00+00:00",
    }
    data["terms_acceptances"].append(acceptance)
    services.save_data(data)
    return acceptance


# ---------------------------------------------------------------------------
# Fixture de cliente (scope=function para aislar seeds por test)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient con scope de función para aislar el estado por test."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /terms/latest — POSITIVOS
# ---------------------------------------------------------------------------

def test_get_latest_terms_returns_200_when_active(client, temp_data_path):
    """GET /terms/latest retorna 200 con los datos de la versión activa."""
    _seed_active_terms("v1.0", "https://example.com/terms/v1.0")

    resp = client.get("/terms/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "v1.0"
    assert body["content_url"] == "https://example.com/terms/v1.0"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body


def test_get_latest_terms_returns_404_when_no_active(client, temp_data_path):
    """GET /terms/latest retorna 404 si no hay T&C activos."""
    # No se inserta ningún T&C activo
    resp = client.get("/terms/latest")
    assert resp.status_code == 404


def test_get_latest_terms_ignores_inactive(client, temp_data_path):
    """GET /terms/latest retorna 404 cuando solo hay T&C inactivos."""
    _seed_inactive_terms("v0.9")

    resp = client.get("/terms/latest")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /terms/accept — POSITIVOS
# ---------------------------------------------------------------------------

def test_accept_terms_first_time_returns_204(client, temp_data_path):
    """POST /terms/accept primera vez retorna 204 y registra la aceptación."""
    _seed_active_terms()
    token = _get_token(client)

    resp = client.post("/terms/accept", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # Verificar que se guardó la aceptación en los datos
    data = services.load_data()
    acceptances = data.get("terms_acceptances", [])
    assert len(acceptances) == 1
    assert acceptances[0]["user_id"] == 3  # alice es user_id=3


def test_accept_terms_idempotent_returns_204_without_duplicate(client, temp_data_path):
    """POST /terms/accept segunda vez retorna 204 sin duplicar el registro."""
    terms = _seed_active_terms()
    _seed_acceptance(user_id=3, terms_id=terms["id"])  # alice ya aceptó
    token = _get_token(client)

    resp = client.post("/terms/accept", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # No debe haber duplicados
    data = services.load_data()
    acceptances = [a for a in data.get("terms_acceptances", []) if a["user_id"] == 3]
    assert len(acceptances) == 1


# ---------------------------------------------------------------------------
# GET /terms/status — POSITIVOS
# ---------------------------------------------------------------------------

def test_terms_status_up_to_date_when_accepted(client, temp_data_path):
    """GET /terms/status retorna up_to_date=True cuando el usuario aceptó la versión vigente."""
    terms = _seed_active_terms("v1.0")
    _seed_acceptance(user_id=3, terms_id=terms["id"])
    token = _get_token(client)

    resp = client.get("/terms/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["up_to_date"] is True
    assert body["current_version"] == "v1.0"


def test_terms_status_not_up_to_date_when_no_acceptance(client, temp_data_path):
    """GET /terms/status retorna up_to_date=False si el usuario nunca aceptó."""
    _seed_active_terms("v1.0")
    token = _get_token(client)

    resp = client.get("/terms/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["up_to_date"] is False
    assert body["current_version"] == "v1.0"


def test_terms_status_not_up_to_date_when_accepted_old_version(client, temp_data_path):
    """GET /terms/status retorna up_to_date=False si el usuario aceptó una versión antigua."""
    # Versión antigua (inactiva) que el usuario aceptó
    old_terms = _seed_inactive_terms("v0.9")
    _seed_acceptance(user_id=3, terms_id=old_terms["id"])

    # Nueva versión activa que el usuario NO ha aceptado
    _seed_active_terms("v1.0")
    token = _get_token(client)

    resp = client.get("/terms/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["up_to_date"] is False
    assert body["current_version"] == "v1.0"


# ---------------------------------------------------------------------------
# NEGATIVOS — sin JWT
# ---------------------------------------------------------------------------

def test_accept_terms_without_jwt_returns_401(client, temp_data_path):
    """POST /terms/accept sin JWT retorna 401."""
    _seed_active_terms()
    resp = client.post("/terms/accept")
    assert resp.status_code == 401


def test_terms_status_without_jwt_returns_401(client, temp_data_path):
    """GET /terms/status sin JWT retorna 401."""
    resp = client.get("/terms/status")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# NEGATIVOS — require_terms_accepted dependency
# ---------------------------------------------------------------------------

def test_require_terms_accepted_raises_403_when_not_accepted(temp_data_path):
    """require_terms_accepted lanza 403 cuando hay T&C activos y el usuario no los aceptó."""
    from fastapi import HTTPException
    from app_v1.deps import require_terms_accepted

    _seed_active_terms("v1.0")

    # Usuario alice (id=3) sin aceptación
    alice = {"id": 3, "username": "alice", "roles": ["user"]}

    with pytest.raises(HTTPException) as exc_info:
        require_terms_accepted(current_user=alice)

    assert exc_info.value.status_code == 403
    detail = exc_info.value.detail
    assert detail["code"] == "TERMS_NOT_ACCEPTED"
    assert detail["current_version"] == "v1.0"


def test_require_terms_accepted_passes_when_accepted(temp_data_path):
    """require_terms_accepted no lanza excepción cuando el usuario aceptó los T&C vigentes."""
    from app_v1.deps import require_terms_accepted

    terms = _seed_active_terms("v1.0")
    _seed_acceptance(user_id=3, terms_id=terms["id"])

    alice = {"id": 3, "username": "alice", "roles": ["user"]}

    # No debe lanzar excepción
    result = require_terms_accepted(current_user=alice)
    assert result is None


def test_require_terms_accepted_passes_when_no_active_terms(temp_data_path):
    """require_terms_accepted no bloquea cuando no hay T&C activos."""
    from app_v1.deps import require_terms_accepted

    # Sin T&C en el sistema
    alice = {"id": 3, "username": "alice", "roles": ["user"]}

    # No debe lanzar excepción
    result = require_terms_accepted(current_user=alice)
    assert result is None


# ---------------------------------------------------------------------------
# EDGE CASES
# ---------------------------------------------------------------------------

def test_accept_terms_when_no_active_terms_returns_404(client, temp_data_path):
    """POST /terms/accept retorna 404 cuando no hay T&C activos."""
    token = _get_token(client)

    resp = client.post("/terms/accept", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_acceptance_no_duplicate_in_db(temp_data_path):
    """create_acceptance es idempotente: no genera duplicados user_id + terms_id."""
    terms = _seed_active_terms()

    # Llamar dos veces con los mismos parámetros
    acc1 = services.create_acceptance(user_id=3, terms_id=terms["id"], ip_address="1.2.3.4")
    acc2 = services.create_acceptance(user_id=3, terms_id=terms["id"], ip_address="5.6.7.8")

    # Deben ser el mismo registro
    assert acc1["id"] == acc2["id"]

    # Solo un registro en la BD
    data = services.load_data()
    user_acceptances = [
        a for a in data.get("terms_acceptances", [])
        if a["user_id"] == 3 and a["terms_id"] == terms["id"]
    ]
    assert len(user_acceptances) == 1
