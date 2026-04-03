# tests/test_boards_security.py
"""Security tests for boards write endpoints (Sprint 2.7)."""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestPostBoardAuth:
    """POST /boards — cualquier usuario autenticado puede crear boards."""

    def test_anonymous_cannot_create_board(self, client, temp_data_path):
        """Sin token → 401."""
        r = client.post("/boards", json={"name": "NoAuthBoard", "description": "test"})
        assert r.status_code == 401

    def test_authenticated_user_can_create_board(self, client, temp_data_path):
        """Usuario normal autenticado → 201 con creator_id asignado."""
        token = _login(client, "alice@example.com")
        r = client.post(
            "/boards",
            json={"name": "AliceBoard", "description": "created by alice"},
            headers=_auth(token),
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "AliceBoard"
        assert body["creator_id"] is not None


class TestPutBoardAuth:
    """PUT /boards/{id} — solo owner o admin."""

    def test_anonymous_cannot_update_board(self, client, temp_data_path):
        """Sin token → 401."""
        r = client.put("/boards/1", json={"name": "Hacked"})
        assert r.status_code == 401

    def test_non_owner_cannot_update_board(self, client, temp_data_path):
        """Alice crea un board; Bob intenta editarlo → 403."""
        alice_token = _login(client, "alice@example.com")
        # Alice crea el board
        created = client.post(
            "/boards",
            json={"name": "AliceOwned", "description": "alice only"},
            headers=_auth(alice_token),
        )
        assert created.status_code == 201
        board_id = created.json()["id"]

        # Mod intenta editarlo → 403 (no es owner ni admin)
        mod_token = _login(client, "mod@example.com")
        r = client.put(
            f"/boards/{board_id}",
            json={"name": "ModHijacked"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 403

    def test_owner_can_update_own_board(self, client, temp_data_path):
        """Owner edita su propio board → 200."""
        alice_token = _login(client, "alice@example.com")
        created = client.post(
            "/boards",
            json={"name": "AliceEditable", "description": "to be edited"},
            headers=_auth(alice_token),
        )
        assert created.status_code == 201
        board_id = created.json()["id"]

        r = client.put(
            f"/boards/{board_id}",
            json={"name": "AliceEditedBoard"},
            headers=_auth(alice_token),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "AliceEditedBoard"

    def test_admin_can_update_any_board(self, client, temp_data_path):
        """Admin puede editar cualquier board (incluso uno de otro usuario) → 200."""
        alice_token = _login(client, "alice@example.com")
        created = client.post(
            "/boards",
            json={"name": "AliceForAdmin", "description": "admin will edit"},
            headers=_auth(alice_token),
        )
        assert created.status_code == 201
        board_id = created.json()["id"]

        admin_token = _login(client, "admin@example.com")
        r = client.put(
            f"/boards/{board_id}",
            json={"name": "AdminOverride"},
            headers=_auth(admin_token),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "AdminOverride"


class TestDeleteBoardAuth:
    """DELETE /boards/{id} — solo admin."""

    def test_anonymous_cannot_delete_board(self, client, temp_data_path):
        """Sin token → 401."""
        r = client.delete("/boards/1")
        assert r.status_code == 401

    def test_regular_user_cannot_delete_board(self, client, temp_data_path):
        """Usuario normal → 403."""
        token = _login(client, "alice@example.com")
        r = client.delete("/boards/1", headers=_auth(token))
        assert r.status_code == 403

    def test_mod_cannot_delete_board(self, client, temp_data_path):
        """Moderador → 403 (no es admin)."""
        token = _login(client, "mod@example.com")
        r = client.delete("/boards/1", headers=_auth(token))
        assert r.status_code == 403

    def test_admin_can_delete_board(self, client, temp_data_path):
        """Admin puede borrar un board → 204."""
        # Crear un board temporal para no romper otros tests
        alice_token = _login(client, "alice@example.com")
        created = client.post(
            "/boards",
            json={"name": "ToDelete", "description": "will be deleted"},
            headers=_auth(alice_token),
        )
        assert created.status_code == 201
        board_id = created.json()["id"]

        admin_token = _login(client, "admin@example.com")
        r = client.delete(f"/boards/{board_id}", headers=_auth(admin_token))
        assert r.status_code == 204

        # Verificar que ya no existe
        r2 = client.get(f"/boards/{board_id}")
        assert r2.status_code == 404
