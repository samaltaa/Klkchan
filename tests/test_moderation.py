# tests/test_moderation.py
"""
Moderation tests: mod/admin permissions on posts, comments, and the queue.
Roles are set directly in seed data since they come from the JWT (which reads
from stored user data at login time).
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app
import app_v1.services as services


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _set_role(user_id: int, roles: list) -> None:
    """Helper: update roles on a seed user directly in storage."""
    data = services.load_data()
    for user in data["users"]:
        if user["id"] == user_id:
            user["roles"] = roles
            break
    services.save_data(data)


def _login(client, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def _make_comment(client, token: str, post_id: int = 1, body: str = "a comment") -> int:
    r = client.post(
        "/comments",
        json={"post_id": post_id, "body": body},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


class TestModeratorDeletesOthersContent:
    def test_moderator_can_delete_others_post(self, client, temp_data_path):
        # Give mod user the "mod" role
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")

        # Post 1 belongs to alice (user_id=3), not to mod (user_id=2)
        r = client.delete("/posts/1", headers={"Authorization": f"Bearer {mod_token}"})
        assert r.status_code == 204

    def test_moderator_can_delete_others_comment(self, client, temp_data_path):
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")
        alice_token = _login(client, "alice@example.com")

        # alice creates a comment
        comment_id = _make_comment(client, alice_token, post_id=1)

        # mod deletes it
        r = client.delete(
            f"/comments/{comment_id}",
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 204

    def test_admin_can_delete_others_post(self, client, temp_data_path):
        _set_role(1, ["user", "admin"])
        admin_token = _login(client, "admin@example.com")

        # Post 1 belongs to alice, admin should be able to delete it
        r = client.delete("/posts/1", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 204

    def test_regular_user_cannot_delete_others_post(self, client, temp_data_path):
        # mod has no elevated role here
        _set_role(2, ["user"])
        mod_token = _login(client, "mod@example.com")

        # mod tries to delete alice's post
        r = client.delete("/posts/1", headers={"Authorization": f"Bearer {mod_token}"})
        assert r.status_code == 403


class TestModerationQueue:
    def test_regular_user_cannot_access_moderation_queue(self, client, temp_data_path):
        _set_role(3, ["user"])
        alice_token = _login(client, "alice@example.com")
        r = client.get("/moderation/queue", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 403

    def test_moderator_can_access_moderation_queue(self, client, temp_data_path):
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")
        r = client.get("/moderation/queue", headers={"Authorization": f"Bearer {mod_token}"})
        assert r.status_code == 200

    def test_admin_can_access_moderation_queue(self, client, temp_data_path):
        _set_role(1, ["user", "admin"])
        admin_token = _login(client, "admin@example.com")
        r = client.get("/moderation/queue", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200


class TestModerationActions:
    def test_moderation_action_remove_post(self, client, temp_data_path):
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": 1, "action": "remove"},
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 200
        assert r.json()["applied"] is True

    def test_moderation_action_requires_auth(self, client, temp_data_path):
        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": 1, "action": "remove"},
        )
        assert r.status_code == 401

    def test_moderation_action_remove_nonexistent_post_fails(self, client, temp_data_path):
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "post", "target_id": 9999, "action": "remove"},
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 404

    def test_moderation_action_remove_comment(self, client, temp_data_path):
        """Mod elimina un comentario via moderation action → 200 applied=True."""
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")
        alice_token = _login(client, "alice@example.com")

        comment_id = _make_comment(client, alice_token, post_id=1)

        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": comment_id, "action": "remove"},
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 200
        assert r.json()["applied"] is True

    def test_moderation_action_remove_nonexistent_comment_fails(self, client, temp_data_path):
        """Intentar eliminar un comentario inexistente → 404."""
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")

        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": 9999, "action": "remove"},
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 404


class TestModerationCommentCascade:
    """FIX 2 (Sprint 2.8): moderation action remove comment debe eliminar votos en cascade."""

    def test_remove_comment_cascades_votes(self, client, temp_data_path):
        """Mod elimina comment via moderation action → votos del comment también eliminados."""
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")
        alice_token = _login(client, "alice@example.com")
        admin_token = _login(client, "admin@example.com")

        # Alice crea un comentario
        comment_id = _make_comment(client, alice_token, post_id=1, body="comment to be moderated")

        # Admin vota el comentario
        r = client.post(
            "/interactions/votes",
            json={"target_type": "comment", "target_id": comment_id, "value": 1},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200

        # Verificar que el voto existe
        data = services.load_data()
        votes_before = [
            v for v in data.get("votes", [])
            if v.get("target_type") == "comment" and v.get("target_id") == comment_id
        ]
        assert len(votes_before) == 1, "el voto debe existir antes del remove"

        # Mod elimina el comentario via moderation action
        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": comment_id, "action": "remove"},
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 200
        assert r.json()["applied"] is True

        # El voto debe haber sido eliminado en cascade
        data = services.load_data()
        votes_after = [
            v for v in data.get("votes", [])
            if v.get("target_type") == "comment" and v.get("target_id") == comment_id
        ]
        assert len(votes_after) == 0, "los votos del comentario deben eliminarse con él"

    def test_remove_comment_no_longer_in_post(self, client, temp_data_path):
        """Tras eliminar por moderation, el comentario no aparece al listar el post."""
        _set_role(2, ["user", "mod"])
        mod_token = _login(client, "mod@example.com")
        alice_token = _login(client, "alice@example.com")

        comment_id = _make_comment(client, alice_token, post_id=1, body="visible then removed")

        # Verificar que aparece
        r = client.get("/posts/1/comments")
        assert r.status_code == 200
        ids = _flat_ids(r.json()["items"])
        assert comment_id in ids, "el comentario debe aparecer antes del remove"

        # Eliminar via moderation
        r = client.post(
            "/moderation/actions",
            json={"target_type": "comment", "target_id": comment_id, "action": "remove"},
            headers={"Authorization": f"Bearer {mod_token}"},
        )
        assert r.status_code == 200

        # Verificar que ya no aparece
        r = client.get("/posts/1/comments")
        assert r.status_code == 200
        ids_after = _flat_ids(r.json()["items"])
        assert comment_id not in ids_after, "el comentario eliminado no debe aparecer"


def _flat_ids(items: list) -> set:
    """Extrae todos los IDs de un árbol de comentarios anidados."""
    ids = set()
    for item in items:
        ids.add(item["id"])
        ids |= _flat_ids(item.get("replies", []))
    return ids
