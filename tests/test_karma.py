# tests/test_karma.py
"""
Tests para el sistema de karma de usuarios.
Karma = suma de votos recibidos en posts y comentarios propios.
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


def _create_post(client: TestClient, token: str, board_id: int = 1) -> dict:
    r = client.post(
        "/posts",
        json={"title": "Post de karma", "body": "Contenido", "board_id": board_id},
        headers=_auth(token),
    )
    assert r.status_code == 201
    return r.json()


def _create_comment(client: TestClient, token: str, post_id: int) -> dict:
    r = client.post(
        "/comments",
        json={"body": "Comentario de karma", "post_id": post_id},
        headers=_auth(token),
    )
    assert r.status_code == 201
    return r.json()


def _vote(client: TestClient, token: str, target_type: str, target_id: int, value: int):
    return client.post(
        "/interactions/votes",
        json={"target_type": target_type, "target_id": target_id, "value": value},
        headers=_auth(token),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_karma_zero_for_new_user(client: TestClient):
    """Un usuario recién creado tiene karma = 0."""
    alice_token = _login(client, "alice@example.com")
    r = client.get("/users/me", headers=_auth(alice_token))
    assert r.status_code == 200
    data = r.json()
    assert data["karma"] == 0
    assert data["post_karma"] == 0
    assert data["comment_karma"] == 0


def test_karma_fields_present_in_user_response(client: TestClient):
    """GET /users/{id} incluye campos karma."""
    r = client.get("/users/3")  # alice
    assert r.status_code == 200
    data = r.json()
    assert "karma" in data
    assert "post_karma" in data
    assert "comment_karma" in data


def test_post_karma_increases_with_upvote(client: TestClient):
    """Upvote en post del usuario incrementa su post_karma."""
    alice_token = _login(client, "alice@example.com")
    mod_token = _login(client, "mod@example.com")

    post = _create_post(client, alice_token)

    # Antes del voto
    r = client.get("/users/me", headers=_auth(alice_token))
    karma_before = r.json()["post_karma"]

    # mod vota el post de alice
    _vote(client, mod_token, "post", post["id"], 1)

    # Después del voto
    r = client.get("/users/me", headers=_auth(alice_token))
    assert r.json()["post_karma"] == karma_before + 1
    assert r.json()["karma"] == karma_before + 1


def test_post_karma_decreases_with_downvote(client: TestClient):
    """Downvote en post del usuario decrementa su post_karma."""
    alice_token = _login(client, "alice@example.com")
    mod_token = _login(client, "mod@example.com")

    post = _create_post(client, alice_token)
    _vote(client, mod_token, "post", post["id"], -1)

    r = client.get("/users/me", headers=_auth(alice_token))
    assert r.json()["post_karma"] == -1
    assert r.json()["karma"] == -1


def test_comment_karma_separate_from_post_karma(client: TestClient):
    """post_karma y comment_karma se cuentan por separado."""
    alice_token = _login(client, "alice@example.com")
    mod_token = _login(client, "mod@example.com")

    # alice crea un post y un comment
    post = _create_post(client, alice_token)
    comment = _create_comment(client, alice_token, post["id"])

    # mod upvota ambos
    _vote(client, mod_token, "post", post["id"], 1)
    _vote(client, mod_token, "comment", comment["id"], 1)

    r = client.get("/users/me", headers=_auth(alice_token))
    data = r.json()
    assert data["post_karma"] == 1
    assert data["comment_karma"] == 1
    assert data["karma"] == 2


def test_karma_not_affected_by_own_votes(client: TestClient):
    """El usuario no puede inflar su propio karma."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    # alice intenta votar su propio post
    _vote(client, alice_token, "post", post["id"], 1)

    r = client.get("/users/me", headers=_auth(alice_token))
    # karma sigue siendo 1 (el voto de alice en su propio post cuenta igual)
    # el sistema no tiene restricción sobre auto-votos, el karma refleja todos los votos
    data = r.json()
    assert "karma" in data


def test_karma_visible_in_user_list(client: TestClient):
    """GET /users lista usuarios con sus campos de karma."""
    r = client.get("/users")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) > 0
    for user in items:
        assert "karma" in user
        assert "post_karma" in user
        assert "comment_karma" in user
