# tests/test_comment_retrieve_update.py
"""
Tests para los endpoints GET /comments/{id} y PATCH /comments/{id}.

Cubre los 7 escenarios requeridos:
  GET  200 — comentario existente
  GET  404 — id inexistente
  PATCH 200 — owner actualiza su comentario
  PATCH 403 — usuario sin permisos
  PATCH 404 — comentario inexistente
  PATCH 400 — payload vacío
  PATCH 400 — body con palabra prohibida
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    return r.json()["access_token"]


def _create_comment(client: TestClient, token: str, post_id: int = 1, body: str = "Comentario de prueba") -> int:
    r = client.post(
        "/comments",
        json={"body": body, "post_id": post_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"create_comment failed: {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# GET /comments/{comment_id}
# ---------------------------------------------------------------------------

def test_retrieve_comment_200(client: TestClient, temp_data_path):
    """GET con id existente retorna 200 y el comentario correcto."""
    token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, token, body="Hola mundo")

    r = client.get(f"/comments/{comment_id}")

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == comment_id
    assert data["body"] == "Hola mundo"
    assert data["replies"] == []
    assert data["depth"] == 0


def test_retrieve_comment_404(client: TestClient, temp_data_path):
    """GET con id inexistente retorna 404."""
    r = client.get("/comments/99999")

    assert r.status_code == 404
    assert r.json()["detail"] == "Comment not found"


# ---------------------------------------------------------------------------
# PATCH /comments/{comment_id}
# ---------------------------------------------------------------------------

def test_update_comment_200_owner(client: TestClient, temp_data_path):
    """Owner puede actualizar su propio comentario — retorna 200 con body nuevo."""
    token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, token, body="Texto original")

    r = client.patch(
        f"/comments/{comment_id}",
        json={"body": "Texto editado"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == comment_id
    assert data["body"] == "Texto editado"
    assert data["updated_at"] is not None


def test_update_comment_403_not_owner(client: TestClient, temp_data_path):
    """Usuario que no es owner ni mod/admin recibe 403."""
    alice_token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, alice_token, body="Comentario de alice")

    # mod no es owner de este comentario — pero mod SÍ tiene privilegio,
    # así que usamos un usuario regular diferente registrado en el momento.
    r_reg = client.post(
        "/auth/register",
        json={"username": "bob_test", "email": "bob_test@example.com", "password": "Aa123456!"},
    )
    bob_token = _login(client, "bob_test@example.com")

    r = client.patch(
        f"/comments/{comment_id}",
        json={"body": "Intento de edición"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )

    assert r.status_code == 403


def test_update_comment_404_not_found(client: TestClient, temp_data_path):
    """PATCH sobre id inexistente retorna 404."""
    token = _login(client, "alice@example.com")

    r = client.patch(
        "/comments/99999",
        json={"body": "Cualquier texto"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Comment not found"


def test_update_comment_400_empty_payload(client: TestClient, temp_data_path):
    """Payload sin campos retorna 400 'No fields to update'."""
    token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, token)

    r = client.patch(
        f"/comments/{comment_id}",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 400
    assert r.json()["detail"] == "No fields to update"


def test_update_comment_400_banned_word(client: TestClient, temp_data_path):
    """Body con palabra prohibida retorna 400."""
    token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, token)

    r = client.patch(
        f"/comments/{comment_id}",
        json={"body": "puta mierda"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r.status_code == 400


def test_update_comment_200_mod_can_edit_any(client: TestClient, temp_data_path):
    """Mod puede editar comentario ajeno."""
    alice_token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, alice_token, body="Texto de alice")

    mod_token = _login(client, "mod@example.com")
    r = client.patch(
        f"/comments/{comment_id}",
        json={"body": "Editado por mod"},
        headers={"Authorization": f"Bearer {mod_token}"},
    )

    assert r.status_code == 200
    assert r.json()["body"] == "Editado por mod"


def test_update_comment_401_no_token(client: TestClient, temp_data_path):
    """PATCH sin token retorna 401."""
    alice_token = _login(client, "alice@example.com")
    comment_id = _create_comment(client, alice_token)

    r = client.patch(
        f"/comments/{comment_id}",
        json={"body": "Sin auth"},
    )

    assert r.status_code == 401
