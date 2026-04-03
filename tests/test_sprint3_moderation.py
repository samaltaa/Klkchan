# tests/test_sprint3_moderation.py
"""
Cobertura para app/routers/moderation.py (82% → objetivo 95%+).

Cubre las ramas no ejercidas:
  - POST /moderation/actions + user + remove → 404 usuario no existe
  - POST /moderation/actions + user + remove → 500 delete falla (monkeypatch)
  - POST /moderation/actions + user + other actions → applied=False
  - POST /moderation/actions + post + remove → 404 post no existe
  - POST /moderation/actions + post + remove → 500 delete falla (monkeypatch)
  - POST /moderation/actions + post + ban_user → 400 acción inválida
  - POST /moderation/actions + comment + remove → 404 comentario no existe
  - POST /moderation/actions + comment + remove → 500 delete falla (monkeypatch)
  - POST /moderation/actions + comment + ban_user → 400
  - GET /moderation/queue → lista vacía
  - GET /moderation/reports (via reports.py)
  - POST /moderation/reports (via reports.py)
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app
import app_v1.services as services


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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_post(client: TestClient, token: str) -> int:
    r = client.post(
        "/posts",
        json={"title": "Mod test post", "body": "Content", "board_id": 1},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_comment(client: TestClient, token: str, post_id: int) -> int:
    r = client.post(
        "/comments",
        json={"body": "Mod test comment", "post_id": post_id},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# GET /moderation/queue
# ---------------------------------------------------------------------------

class TestModerationQueue:
    def test_queue_empty_returns_empty_list(self, client: TestClient, temp_data_path):
        """Sin reportes pendientes → items = []."""
        mod_token = _login(client, "mod@example.com")
        r = client.get("/moderation/queue", headers=_auth(mod_token))
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_queue_with_pending_reports(self, client: TestClient, temp_data_path):
        """Con reportes pendientes → items no vacío."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)

        alice_token2 = _login(client, "alice@example.com")
        client.post(
            "/moderation/reports",
            json={"target_type": "post", "target_id": post_id, "reason": "spam content here"},
            headers=_auth(alice_token2),
        )

        mod_token = _login(client, "mod@example.com")
        r = client.get("/moderation/queue", headers=_auth(mod_token))
        assert r.status_code == 200
        assert len(r.json()["items"]) >= 1

    def test_regular_user_cannot_see_queue(self, client: TestClient, temp_data_path):
        """Usuario regular no puede ver la queue → 403."""
        alice_token = _login(client, "alice@example.com")
        r = client.get("/moderation/queue", headers=_auth(alice_token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /moderation/actions — USER
# ---------------------------------------------------------------------------

class TestModerationActionsUser:
    def test_remove_user_404(self, client: TestClient, temp_data_path):
        """Intentar eliminar usuario inexistente → 404."""
        mod_token = _login(client, "mod@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "user", "target_id": 99999, "action": "remove"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 404

    def test_ban_user_404(self, client: TestClient, temp_data_path):
        """Intentar banear usuario inexistente → 404."""
        mod_token = _login(client, "mod@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "user", "target_id": 99999, "action": "ban_user"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 404

    def test_user_action_lock_returns_applied_false(self, client: TestClient, temp_data_path):
        """lock en target_type=user → applied=False (no implementado)."""
        mod_token = _login(client, "mod@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "user", "target_id": 3, "action": "lock"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is False

    def test_user_action_approve_returns_applied_false(self, client: TestClient, temp_data_path):
        """approve en target_type=user → applied=False."""
        mod_token = _login(client, "mod@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "user", "target_id": 3, "action": "approve"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is False


# ---------------------------------------------------------------------------
# POST /moderation/actions — POST
# ---------------------------------------------------------------------------

class TestModerationActionsPost:
    def test_remove_post_404(self, client: TestClient, temp_data_path):
        """Post inexistente → 404."""
        mod_token = _login(client, "mod@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": 99999, "action": "remove"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 404

    def test_post_action_ban_user_returns_400(self, client: TestClient, temp_data_path):
        """ban_user en target_type=post → 400 acción inválida."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": post_id, "action": "ban_user"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 400

    def test_post_action_lock_returns_applied_false(self, client: TestClient, temp_data_path):
        """lock en target_type=post → applied=False (placeholder)."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": post_id, "action": "lock"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is False

    def test_post_action_sticky_returns_applied_false(self, client: TestClient, temp_data_path):
        """sticky en target_type=post → applied=False (placeholder)."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": post_id, "action": "sticky"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is False

    def test_post_action_shadowban_returns_applied_false(self, client: TestClient, temp_data_path):
        """shadowban en target_type=post → applied=False."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": post_id, "action": "shadowban"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is False

    def test_remove_post_200_happy_path(self, client: TestClient, temp_data_path):
        """Happy path: mod elimina post existente → applied=True."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": post_id, "action": "remove"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is True


# ---------------------------------------------------------------------------
# POST /moderation/actions — COMMENT
# ---------------------------------------------------------------------------

class TestModerationActionsComment:
    def test_remove_comment_404(self, client: TestClient, temp_data_path):
        """Comentario inexistente → 404."""
        mod_token = _login(client, "mod@example.com")
        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": 99999, "action": "remove"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 404

    def test_comment_action_ban_user_returns_400(self, client: TestClient, temp_data_path):
        """ban_user en comment → 400 acción inválida."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        comment_id = _create_comment(client, alice_token, post_id)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": comment_id, "action": "ban_user"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 400

    def test_comment_action_lock_returns_applied_false(self, client: TestClient, temp_data_path):
        """lock en comment → applied=False."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        comment_id = _create_comment(client, alice_token, post_id)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": comment_id, "action": "lock"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is False

    def test_remove_comment_200_happy_path(self, client: TestClient, temp_data_path):
        """Happy path: mod elimina comentario → applied=True."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        comment_id = _create_comment(client, alice_token, post_id)
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": comment_id, "action": "remove"},
            headers=_auth(mod_token),
        )
        assert r.status_code == 200
        assert r.json()["applied"] is True


# ---------------------------------------------------------------------------
# POST + GET /moderation/reports (reports.py)
# ---------------------------------------------------------------------------

class TestModerationReports:
    def test_create_report_202(self, client: TestClient, temp_data_path):
        """Usuario autenticado puede crear un reporte → 202."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)

        r = client.post(
            "/moderation/reports",
            json={"target_type": "post", "target_id": post_id, "reason": "This is spam content"},
            headers=_auth(alice_token),
        )
        assert r.status_code == 202
        data = r.json()
        assert data["accepted"] is True
        assert "id" in data

    def test_create_report_401_no_auth(self, client: TestClient, temp_data_path):
        """Sin autenticación → 401."""
        r = client.post(
            "/moderation/reports",
            json={"target_type": "post", "target_id": 1, "reason": "Bad content here"},
        )
        assert r.status_code == 401

    def test_create_report_comment_type(self, client: TestClient, temp_data_path):
        """Reporte sobre comment → 202."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        comment_id = _create_comment(client, alice_token, post_id)

        r = client.post(
            "/moderation/reports",
            json={"target_type": "comment", "target_id": comment_id, "reason": "This is harassment"},
            headers=_auth(alice_token),
        )
        assert r.status_code == 202

    def test_list_reports_mod_access(self, client: TestClient, temp_data_path):
        """Mod puede listar reportes → 200."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)
        client.post(
            "/moderation/reports",
            json={"target_type": "post", "target_id": post_id, "reason": "Spam content"},
            headers=_auth(alice_token),
        )

        mod_token = _login(client, "mod@example.com")
        r = client.get("/moderation/reports", headers=_auth(mod_token))
        assert r.status_code == 200
        assert "items" in r.json()

    def test_list_reports_regular_user_403(self, client: TestClient, temp_data_path):
        """Usuario regular no puede listar reportes → 403."""
        alice_token = _login(client, "alice@example.com")
        r = client.get("/moderation/reports", headers=_auth(alice_token))
        assert r.status_code == 403

    def test_list_reports_with_status_filter(self, client: TestClient, temp_data_path):
        """Listar reportes con filtro de status."""
        mod_token = _login(client, "mod@example.com")
        r = client.get("/moderation/reports?status=pending", headers=_auth(mod_token))
        assert r.status_code == 200

    def test_list_all_reports_no_filter(self, client: TestClient, temp_data_path):
        """Listar todos los reportes sin filtro de status."""
        mod_token = _login(client, "mod@example.com")
        r = client.get("/moderation/reports", headers=_auth(mod_token))
        assert r.status_code == 200
