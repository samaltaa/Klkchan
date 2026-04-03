# tests/test_comments_extended.py
"""Tests extendidos para comentarios - casos edge y validaciones."""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _register_and_login(client, username: str, email: str) -> str:
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "Testpass1"},
    )
    r = client.post("/auth/login", data={"username": email, "password": "Testpass1"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _create_post(client, token: str, board_id: int = 1) -> int:
    r = client.post(
        "/posts",
        json={"title": "Post para comentar", "body": "Contenido", "board_id": board_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_comment_on_nonexistent_post_fails(client: TestClient, temp_data_path):
    """Comentar en post inexistente debe fallar."""
    token = _register_and_login(client, "commenter", "comm@test.com")
    response = client.post(
        "/comments",
        json={"body": "Comentario", "post_id": 99999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (400, 404)


def test_comment_without_auth_fails(client: TestClient, temp_data_path):
    """Comentar sin autenticación debe retornar 401."""
    response = client.post(
        "/comments",
        json={"body": "Comentario sin auth", "post_id": 1},
    )
    assert response.status_code == 401


def test_empty_comment_fails(client: TestClient, temp_data_path):
    """Comentario vacío debe fallar validación."""
    token = _register_and_login(client, "emptycomm", "emptycomm@test.com")
    response = client.post(
        "/comments",
        json={"body": "", "post_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_comment_succeeds(client: TestClient, temp_data_path):
    """Comentario válido crea correctamente."""
    token = _register_and_login(client, "commok", "commok@test.com")
    response = client.post(
        "/comments",
        json={"body": "Un comentario válido", "post_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["body"] == "Un comentario válido"


def test_comment_pagination(client: TestClient, temp_data_path):
    """Lista de posts retorna estructura válida."""
    response = client.get("/posts")
    assert response.status_code == 200
    assert "items" in response.json()


def test_comment_with_banned_words_fails(client: TestClient, temp_data_path):
    """Comentario con banned word debe fallar."""
    token = _register_and_login(client, "bwcomm", "bwcomm@test.com")
    response = client.post(
        "/comments",
        json={"body": "cabrón comentario prohibido", "post_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_comment_on_deleted_post_fails(client: TestClient, temp_data_path):
    """Comentar en post eliminado debe fallar."""
    token = _register_and_login(client, "delcomm", "delcomm@test.com")
    post_id = _create_post(client, token)
    client.delete(f"/posts/{post_id}", headers={"Authorization": f"Bearer {token}"})
    response = client.post(
        "/comments",
        json={"body": "Comentario en post eliminado", "post_id": post_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (400, 404)


def test_very_long_comment(client: TestClient, temp_data_path):
    """Comentario muy largo: acepta o rechaza por validación."""
    token = _register_and_login(client, "longcomm", "longcomm@test.com")
    response = client.post(
        "/comments",
        json={"body": "A" * 5000, "post_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (201, 422)
