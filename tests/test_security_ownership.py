# tests/test_security_ownership.py
"""
Tests de seguridad: verifican que ownership checks funcionan correctamente.
Un usuario NO puede editar/borrar contenido ajeno.
Un usuario SÍ puede editar/borrar su propio contenido.
Un moderador/admin SÍ puede editar/borrar cualquier contenido.
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, username: str, email: str, password: str = "Testpass1") -> str:
    """Registra un usuario y retorna su access_token."""
    r = client.post("/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, f"register failed: {r.text}"
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, f"login failed: {login.text}"
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_board(client: TestClient, name: str = "test-board") -> int:
    r = client.post("/boards", json={"name": name, "description": "board for tests"})
    assert r.status_code == 201, f"create board failed: {r.text}"
    return r.json()["id"]


def _create_post(client: TestClient, token: str, board_id: int, title: str = "Test Post") -> int:
    r = client.post(
        "/posts",
        json={"title": title, "body": "some content", "board_id": board_id},
        headers=_auth(token),
    )
    assert r.status_code == 201, f"create post failed: {r.text}"
    return r.json()["id"]


def _create_comment(client: TestClient, token: str, post_id: int, body: str = "A comment") -> int:
    r = client.post(
        "/comments",
        json={"body": body, "post_id": post_id},
        headers=_auth(token),
    )
    assert r.status_code == 201, f"create comment failed: {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Post ownership — edit
# ---------------------------------------------------------------------------

def test_user_cannot_edit_others_post(client: TestClient):
    """Bob no puede editar el post de Alice → 403."""
    alice_token = _register_and_login(client, "alice_ow1", "alice_ow1@test.com")
    bob_token = _register_and_login(client, "bob_ow1", "bob_ow1@test.com")

    board_id = _create_board(client, "board-ow1")
    post_id = _create_post(client, alice_token, board_id)

    r = client.put(f"/posts/{post_id}", json={"title": "Hacked by Bob"}, headers=_auth(bob_token))
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


def test_owner_can_edit_own_post(client: TestClient):
    """Alice puede editar su propio post → 200."""
    alice_token = _register_and_login(client, "alice_ow2", "alice_ow2@test.com")

    board_id = _create_board(client, "board-ow2")
    post_id = _create_post(client, alice_token, board_id, title="Original")

    r = client.put(f"/posts/{post_id}", json={"title": "Updated by Alice"}, headers=_auth(alice_token))
    assert r.status_code == 200
    assert r.json()["title"] == "Updated by Alice"


# ---------------------------------------------------------------------------
# Post ownership — delete
# ---------------------------------------------------------------------------

def test_user_cannot_delete_others_post(client: TestClient):
    """Bob no puede borrar el post de Alice → 403."""
    alice_token = _register_and_login(client, "alice_ow3", "alice_ow3@test.com")
    bob_token = _register_and_login(client, "bob_ow3", "bob_ow3@test.com")

    board_id = _create_board(client, "board-ow3")
    post_id = _create_post(client, alice_token, board_id)

    r = client.delete(f"/posts/{post_id}", headers=_auth(bob_token))
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


def test_owner_can_delete_own_post(client: TestClient):
    """Alice puede borrar su propio post → 204."""
    alice_token = _register_and_login(client, "alice_ow4", "alice_ow4@test.com")

    board_id = _create_board(client, "board-ow4")
    post_id = _create_post(client, alice_token, board_id)

    r = client.delete(f"/posts/{post_id}", headers=_auth(alice_token))
    assert r.status_code == 204

    # Verificar que ya no existe
    r2 = client.get(f"/posts/{post_id}")
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# Comment ownership — delete
# ---------------------------------------------------------------------------

def test_user_cannot_delete_others_comment(client: TestClient):
    """Bob no puede borrar el comentario de Alice → 403."""
    alice_token = _register_and_login(client, "alice_ow5", "alice_ow5@test.com")
    bob_token = _register_and_login(client, "bob_ow5", "bob_ow5@test.com")

    board_id = _create_board(client, "board-ow5")
    post_id = _create_post(client, alice_token, board_id)
    comment_id = _create_comment(client, alice_token, post_id)

    r = client.delete(f"/comments/{comment_id}", headers=_auth(bob_token))
    assert r.status_code == 403
    assert "Not authorized" in r.json()["detail"]


def test_owner_can_delete_own_comment(client: TestClient):
    """Alice puede borrar su propio comentario → 204."""
    alice_token = _register_and_login(client, "alice_ow6", "alice_ow6@test.com")

    board_id = _create_board(client, "board-ow6")
    post_id = _create_post(client, alice_token, board_id)
    comment_id = _create_comment(client, alice_token, post_id)

    r = client.delete(f"/comments/{comment_id}", headers=_auth(alice_token))
    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Unauthenticated access to protected endpoints
# ---------------------------------------------------------------------------

def test_unauthenticated_cannot_edit_post(client: TestClient):
    """Sin token no se puede editar un post → 401."""
    alice_token = _register_and_login(client, "alice_ow7", "alice_ow7@test.com")
    board_id = _create_board(client, "board-ow7")
    post_id = _create_post(client, alice_token, board_id)

    r = client.put(f"/posts/{post_id}", json={"title": "No token"})
    assert r.status_code == 401


def test_unauthenticated_cannot_delete_comment(client: TestClient):
    """Sin token no se puede borrar un comentario → 401."""
    alice_token = _register_and_login(client, "alice_ow8", "alice_ow8@test.com")
    board_id = _create_board(client, "board-ow8")
    post_id = _create_post(client, alice_token, board_id)
    comment_id = _create_comment(client, alice_token, post_id)

    r = client.delete(f"/comments/{comment_id}")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# User profile ownership — edit (FIX 1)
# ---------------------------------------------------------------------------

def test_user_cannot_edit_others_profile(client: TestClient):
    """Bob no puede editar el perfil de Alice → 403."""
    r_alice = client.post(
        "/auth/register",
        json={"username": "alice_ow9", "email": "alice_ow9@test.com", "password": "Testpass1"},
    )
    assert r_alice.status_code == 201
    alice_id = r_alice.json()["id"]

    bob_token = _register_and_login(client, "bob_ow9", "bob_ow9@test.com")

    r = client.put(
        f"/users/{alice_id}",
        json={"bio": "hackeado por Bob"},
        headers=_auth(bob_token),
    )
    assert r.status_code == 403
    assert "permiso" in r.json()["detail"].lower()


def test_owner_can_edit_own_profile(client: TestClient):
    """Alice puede editar su propio perfil → 200."""
    r_alice = client.post(
        "/auth/register",
        json={"username": "alice_ow10", "email": "alice_ow10@test.com", "password": "Testpass1"},
    )
    assert r_alice.status_code == 201
    alice_id = r_alice.json()["id"]
    alice_login = client.post("/auth/login", data={"username": "alice_ow10@test.com", "password": "Testpass1"})
    alice_token = alice_login.json()["access_token"]

    r = client.put(
        f"/users/{alice_id}",
        json={"bio": "mi nueva bio"},
        headers=_auth(alice_token),
    )
    assert r.status_code == 200
    assert r.json()["bio"] == "mi nueva bio"


def test_unauthenticated_cannot_edit_profile(client: TestClient):
    """Sin token no se puede editar un perfil → 401."""
    r_alice = client.post(
        "/auth/register",
        json={"username": "alice_ow11", "email": "alice_ow11@test.com", "password": "Testpass1"},
    )
    alice_id = r_alice.json()["id"]

    r = client.put(f"/users/{alice_id}", json={"bio": "sin token"})
    assert r.status_code == 401
