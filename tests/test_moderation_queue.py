# tests/test_moderation_queue.py
"""
Tests para la queue real de moderación y el listado de reports.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_report(client: TestClient, token: str, target_type: str = "post",
                   target_id: int = 1, reason: str = "Contenido inapropiado") -> dict:
    r = client.post("/moderation/reports", json={
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
    }, headers=_auth(token))
    assert r.status_code == 202, f"create_report falló: {r.text}"
    return r.json()


# ---------------------------------------------------------------------------
# Moderation queue
# ---------------------------------------------------------------------------

def test_moderation_queue_empty_initially(client: TestClient):
    """Con el seed inicial (sin reports) la queue retorna items vacía."""
    mod_token = _login(client, "mod@example.com")
    r = client.get("/moderation/queue", headers=_auth(mod_token))
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_moderation_queue_returns_real_reports(client: TestClient):
    """Tras crear un report, aparece en la queue con status=pending."""
    alice_token = _login(client, "alice@example.com")
    mod_token = _login(client, "mod@example.com")

    # Crear un report
    created = _create_report(client, alice_token)
    report_id = created["id"]

    # Verificar que aparece en la queue
    r = client.get("/moderation/queue", headers=_auth(mod_token))
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(item["id"] == report_id for item in items)


def test_moderation_queue_requires_auth(client: TestClient):
    """Sin token no se puede acceder a la queue."""
    r = client.get("/moderation/queue")
    assert r.status_code == 401


def test_moderation_queue_requires_mod_role(client: TestClient):
    """Un usuario sin rol mod/admin recibe 403."""
    alice_token = _login(client, "alice@example.com")
    r = client.get("/moderation/queue", headers=_auth(alice_token))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Reports CRUD
# ---------------------------------------------------------------------------

def test_create_report_persists(client: TestClient):
    """POST /moderation/reports crea un reporte real con id asignado."""
    alice_token = _login(client, "alice@example.com")
    data = _create_report(client, alice_token, reason="Spam detectado")
    assert data["accepted"] is True
    assert isinstance(data["id"], int)


def test_list_reports_returns_created_items(client: TestClient):
    """GET /moderation/reports lista los reportes creados."""
    alice_token = _login(client, "alice@example.com")
    mod_token = _login(client, "mod@example.com")

    # Crear dos reports
    r1 = _create_report(client, alice_token, reason="Reporte uno")
    r2 = _create_report(client, alice_token, reason="Reporte dos")

    r = client.get("/moderation/reports", headers=_auth(mod_token))
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()["items"]}
    assert r1["id"] in ids
    assert r2["id"] in ids


def test_list_reports_requires_mod_role(client: TestClient):
    """Un usuario normal no puede listar reports."""
    alice_token = _login(client, "alice@example.com")
    r = client.get("/moderation/reports", headers=_auth(alice_token))
    assert r.status_code == 403
