# tests/test_posts_sorting.py
"""
Tests para el parámetro sort en GET /posts.
Modos: new (default), top, hot.
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


def _create_post(client: TestClient, token: str, title: str = "Post", board_id: int = 1) -> dict:
    r = client.post(
        "/posts",
        json={"title": title, "body": "Contenido del post", "board_id": board_id},
        headers=_auth(token),
    )
    assert r.status_code == 201
    return r.json()


def _vote(client: TestClient, token: str, post_id: int, value: int):
    return client.post(
        "/interactions/votes",
        json={"target_type": "post", "target_id": post_id, "value": value},
        headers=_auth(token),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sort_new_is_default(client: TestClient):
    """Sin parámetro sort, GET /posts retorna 200 con items."""
    r = client.get("/posts")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body


def test_sort_new_explicit(client: TestClient):
    """sort=new es aceptado y retorna 200."""
    r = client.get("/posts?sort=new")
    assert r.status_code == 200
    assert "items" in r.json()


def test_sort_top_accepted(client: TestClient):
    """sort=top retorna 200."""
    r = client.get("/posts?sort=top")
    assert r.status_code == 200
    assert "items" in r.json()


def test_sort_hot_accepted(client: TestClient):
    """sort=hot retorna 200."""
    r = client.get("/posts?sort=hot")
    assert r.status_code == 200
    assert "items" in r.json()


def test_sort_invalid_returns_422(client: TestClient):
    """Un sort inválido retorna 422."""
    r = client.get("/posts?sort=invalid")
    assert r.status_code == 422


def test_sort_top_orders_by_votes_desc(client: TestClient):
    """sort=top ordena posts por votos de mayor a menor."""
    alice_token = _login(client, "alice@example.com")
    mod_token = _login(client, "mod@example.com")
    admin_token = _login(client, "admin@example.com")

    # Crear tres posts
    p_low = _create_post(client, alice_token, title="Post con pocos votos")
    p_high = _create_post(client, alice_token, title="Post con muchos votos")
    p_mid = _create_post(client, alice_token, title="Post con votos medios")

    # Dar votos: high=2, mid=1, low=0
    _vote(client, mod_token, p_high["id"], 1)
    _vote(client, admin_token, p_high["id"], 1)
    _vote(client, mod_token, p_mid["id"], 1)

    r = client.get("/posts?sort=top")
    assert r.status_code == 200
    items = r.json()["items"]

    # Encontrar las posiciones de los tres posts por id
    ids = [item["id"] for item in items]
    pos_high = ids.index(p_high["id"])
    pos_mid = ids.index(p_mid["id"])
    pos_low = ids.index(p_low["id"])

    # p_high debe aparecer antes que p_mid, y p_mid antes que p_low
    assert pos_high < pos_mid < pos_low, (
        f"sort=top incorrecto: pos_high={pos_high}, pos_mid={pos_mid}, pos_low={pos_low}"
    )


def test_sort_hot_returns_all_posts(client: TestClient):
    """sort=hot retorna todos los posts (mismo total que sort=new)."""
    r_new = client.get("/posts?sort=new&limit=100")
    r_hot = client.get("/posts?sort=hot&limit=100")
    assert r_new.status_code == 200
    assert r_hot.status_code == 200
    ids_new = {item["id"] for item in r_new.json()["items"]}
    ids_hot = {item["id"] for item in r_hot.json()["items"]}
    assert ids_new == ids_hot, "sort=hot y sort=new deben retornar los mismos posts"


def test_sort_new_newest_first(client: TestClient):
    """sort=new retorna posts en orden created_at descendente."""
    alice_token = _login(client, "alice@example.com")

    # Crear dos posts; el segundo es más reciente
    p_old = _create_post(client, alice_token, title="Post antiguo")
    p_new = _create_post(client, alice_token, title="Post nuevo")

    r = client.get("/posts?sort=new&limit=100")
    assert r.status_code == 200
    items = r.json()["items"]
    ids = [item["id"] for item in items]
    pos_new = ids.index(p_new["id"])
    pos_old = ids.index(p_old["id"])

    # El post más reciente debe aparecer antes
    assert pos_new < pos_old, (
        f"sort=new: post nuevo (id={p_new['id']}) debe aparecer antes que post viejo (id={p_old['id']})"
    )
