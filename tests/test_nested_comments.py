# tests/test_nested_comments.py
"""
Tests para comentarios anidados (parent_id + árbol de respuestas).
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


def _create_post(client: TestClient, token: str) -> dict:
    r = client.post(
        "/posts",
        json={"title": "Post para anidados", "body": "Cuerpo", "board_id": 1},
        headers=_auth(token),
    )
    assert r.status_code == 201
    return r.json()


def _create_comment(client: TestClient, token: str, post_id: int, parent_id: int = None) -> dict:
    payload = {"body": "Comentario de prueba", "post_id": post_id}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    r = client.post("/comments", json=payload, headers=_auth(token))
    return r


# ---------------------------------------------------------------------------
# Tests — estructura anidada
# ---------------------------------------------------------------------------

def test_root_comment_has_empty_replies(client: TestClient):
    """Un comentario raíz tiene replies=[] y depth=0."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    r = _create_comment(client, alice_token, post["id"])
    assert r.status_code == 201
    data = r.json()
    assert data["parent_id"] is None
    assert data["depth"] == 0
    assert data["replies"] == []


def test_reply_appears_nested_under_parent(client: TestClient):
    """Un reply aparece en replies del comentario padre en GET /posts/{id}/comments."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    # Crear comentario raíz
    root_r = _create_comment(client, alice_token, post["id"])
    assert root_r.status_code == 201
    root_id = root_r.json()["id"]

    # Crear reply
    reply_r = _create_comment(client, alice_token, post["id"], parent_id=root_id)
    assert reply_r.status_code == 201
    reply_id = reply_r.json()["id"]

    # Verificar árbol en GET /posts/{id}/comments
    r = client.get(f"/posts/{post['id']}/comments")
    assert r.status_code == 200
    items = r.json()["items"]

    # El comentario raíz debe estar en items
    root_in_tree = next((c for c in items if c["id"] == root_id), None)
    assert root_in_tree is not None, "Comentario raíz no encontrado en items"

    # El reply debe estar en replies del raíz
    reply_ids = [c["id"] for c in root_in_tree["replies"]]
    assert reply_id in reply_ids, f"Reply {reply_id} no encontrado en replies del raíz"

    # El reply NO debe ser un item de nivel raíz
    root_level_ids = [c["id"] for c in items]
    assert reply_id not in root_level_ids, "Reply no debe aparecer a nivel raíz"


def test_reply_has_correct_depth(client: TestClient):
    """Un reply directo tiene depth=1."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    root_r = _create_comment(client, alice_token, post["id"])
    root_id = root_r.json()["id"]

    reply_r = _create_comment(client, alice_token, post["id"], parent_id=root_id)
    assert reply_r.status_code == 201
    assert reply_r.json()["depth"] == 0  # La respuesta del create no tiene depth calculado aún

    # Verificar depth en el árbol
    r = client.get(f"/posts/{post['id']}/comments")
    items = r.json()["items"]
    root_in_tree = next(c for c in items if c["id"] == root_id)
    reply_in_tree = root_in_tree["replies"][0]
    assert reply_in_tree["depth"] == 1


def test_three_levels_of_nesting(client: TestClient):
    """El árbol se construye correctamente con 3 niveles."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    # nivel 0: raíz
    lvl0 = _create_comment(client, alice_token, post["id"])
    assert lvl0.status_code == 201
    id0 = lvl0.json()["id"]

    # nivel 1: reply al raíz
    lvl1 = _create_comment(client, alice_token, post["id"], parent_id=id0)
    assert lvl1.status_code == 201
    id1 = lvl1.json()["id"]

    # nivel 2: reply al level 1
    lvl2 = _create_comment(client, alice_token, post["id"], parent_id=id1)
    assert lvl2.status_code == 201
    id2 = lvl2.json()["id"]

    r = client.get(f"/posts/{post['id']}/comments")
    assert r.status_code == 200
    items = r.json()["items"]

    node0 = next(c for c in items if c["id"] == id0)
    assert node0["depth"] == 0
    assert len(node0["replies"]) == 1

    node1 = node0["replies"][0]
    assert node1["id"] == id1
    assert node1["depth"] == 1
    assert len(node1["replies"]) == 1

    node2 = node1["replies"][0]
    assert node2["id"] == id2
    assert node2["depth"] == 2


def test_get_post_includes_nested_comments(client: TestClient):
    """GET /posts/{id} incluye comentarios anidados en el campo comments."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    root_r = _create_comment(client, alice_token, post["id"])
    root_id = root_r.json()["id"]
    _create_comment(client, alice_token, post["id"], parent_id=root_id)

    r = client.get(f"/posts/{post['id']}")
    assert r.status_code == 200
    comments = r.json()["comments"]

    # El reply no debe estar a nivel raíz
    root_level_ids = [c["id"] for c in comments]
    assert root_id in root_level_ids
    assert len(comments) == 1  # solo el root a nivel raíz

    root_in_post = next(c for c in comments if c["id"] == root_id)
    assert len(root_in_post["replies"]) == 1


# ---------------------------------------------------------------------------
# Tests — validaciones de parent_id
# ---------------------------------------------------------------------------

def test_reply_nonexistent_parent_returns_404(client: TestClient):
    """parent_id que no existe retorna 404."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    r = _create_comment(client, alice_token, post["id"], parent_id=99999)
    assert r.status_code == 404


def test_reply_parent_from_different_post_returns_400(client: TestClient):
    """parent_id de otro post retorna 400."""
    alice_token = _login(client, "alice@example.com")

    post_a = _create_post(client, alice_token)
    post_b = _create_post(client, alice_token)

    # Comentario en post A
    comment_a = _create_comment(client, alice_token, post_a["id"])
    assert comment_a.status_code == 201
    comment_a_id = comment_a.json()["id"]

    # Intentar responder en post B con parent del post A
    r = client.post(
        "/comments",
        json={"body": "Reply cross-post", "post_id": post_b["id"], "parent_id": comment_a_id},
        headers=_auth(alice_token),
    )
    assert r.status_code == 400


def test_get_comments_endpoint_returns_tree(client: TestClient):
    """GET /comments?post_id=X también retorna árbol."""
    alice_token = _login(client, "alice@example.com")
    post = _create_post(client, alice_token)

    root_r = _create_comment(client, alice_token, post["id"])
    root_id = root_r.json()["id"]
    _create_comment(client, alice_token, post["id"], parent_id=root_id)

    r = client.get(f"/comments?post_id={post['id']}")
    assert r.status_code == 200
    items = r.json()["items"]

    # Solo el root a nivel raíz
    assert len(items) == 1
    assert items[0]["id"] == root_id
    assert len(items[0]["replies"]) == 1
