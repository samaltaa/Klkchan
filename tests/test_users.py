# tests/test_users.py
"""
Tests de robustez del campo posts en respuestas de usuario.

Cubre tres escenarios de datos corruptos en data.json:
  1. posts: null  -> response devuelve posts: []
  2. posts: [1,2] -> se recalcula al vuelo desde la coleccion de posts
  3. clave posts ausente -> response devuelve posts: []

Tambien verifica directamente el field_validator(mode="before") del schema User,
que es el ultimo guard antes de serializar la respuesta.
"""
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app_v1.app import app
import app_v1.services as services


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Schema unit tests — validan el field_validator directamente
# ---------------------------------------------------------------------------

def test_user_schema_posts_null_coerced_to_empty_list():
    """User schema: posts=None debe coaccionarse a [] por el field_validator(mode='before')."""
    from app_v1.schemas import User
    u = User(id=1, username="testuser", email="t@t.com", posts=None)
    assert u.posts == []


def test_user_schema_posts_list_preserved():
    """User schema: posts=[1,2,3] se conserva intacto."""
    from app_v1.schemas import User
    u = User(id=1, username="testuser", email="t@t.com", posts=[1, 2, 3])
    assert u.posts == [1, 2, 3]


def test_user_schema_posts_absent_gives_empty_list():
    """User schema: clave posts ausente activa default_factory y devuelve []."""
    from app_v1.schemas import User
    u = User(id=1, username="testuser", email="t@t.com")
    assert u.posts == []


def test_user_schema_model_validate_posts_null():
    """User.model_validate con posts: null debe devolver posts: []."""
    from app_v1.schemas import User
    u = User.model_validate({"id": 1, "username": "usr", "email": "usr@test.com", "posts": None})
    assert u.posts == []


# ---------------------------------------------------------------------------
# Endpoint integration tests — datos corruptos en data.json
# ---------------------------------------------------------------------------

def test_get_user_posts_null_in_db_returns_empty_list(client: TestClient, temp_data_path):
    """GET /users/1 con posts: null en data.json devuelve posts: []."""
    data = services.load_data()
    for u in data["users"]:
        if u.get("id") == 1:  # admin, sin posts en la coleccion
            u["posts"] = None
    services.save_data(data)

    r = client.get("/users/1")
    assert r.status_code == 200
    assert r.json()["posts"] == []


def test_get_user_posts_key_absent_returns_empty_list(client: TestClient, temp_data_path):
    """GET /users/2 con clave posts ausente en data.json devuelve posts: []."""
    data = services.load_data()
    for u in data["users"]:
        if u.get("id") == 2:  # mod, sin posts en la coleccion
            u.pop("posts", None)
    services.save_data(data)

    r = client.get("/users/2")
    assert r.status_code == 200
    assert r.json()["posts"] == []


def test_get_user_posts_recalculated_from_collection(client: TestClient, temp_data_path):
    """GET /users/3 devuelve los IDs de posts calculados desde la coleccion (seed tiene 2 posts de alice)."""
    r = client.get("/users/3")  # alice tiene posts id=1 e id=2 en el seed
    assert r.status_code == 200
    assert sorted(r.json()["posts"]) == [1, 2]
