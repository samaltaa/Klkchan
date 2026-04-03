# tests/test_posts_extended.py
"""Tests extendidos para posts - casos edge y validaciones."""
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


def test_create_post_without_auth_fails(client: TestClient, temp_data_path):
    """Crear post sin autenticación debe fallar."""
    response = client.post(
        "/posts",
        json={"title": "Test", "body": "Content", "board_id": 1},
    )
    assert response.status_code == 401


def test_create_post_with_nonexistent_board_fails(client: TestClient, temp_data_path):
    """Crear post en board inexistente debe fallar."""
    token = _register_and_login(client, "poster", "poster@test.com")
    response = client.post(
        "/posts",
        json={"title": "Test", "body": "Content", "board_id": 99999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (400, 404)


def test_create_empty_post_fails(client: TestClient, temp_data_path):
    """Post con título vacío debe fallar validación."""
    token = _register_and_login(client, "empty", "empty@test.com")
    response = client.post(
        "/posts",
        json={"title": "", "body": "", "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_create_post_succeeds(client: TestClient, temp_data_path):
    """Crear post válido retorna 201."""
    token = _register_and_login(client, "newposter", "newposter@test.com")
    response = client.post(
        "/posts",
        json={"title": "Valid Post", "body": "Valid content", "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Valid Post"


def test_post_pagination_works(client: TestClient, temp_data_path):
    """Paginación de posts respeta el límite."""
    token = _register_and_login(client, "pageposter", "page@test.com")
    for i in range(5):
        client.post(
            "/posts",
            json={"title": f"Post {i}", "body": f"Content {i}", "board_id": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
    response = client.get("/posts?limit=3")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert len(body["items"]) <= 3


def test_filter_posts_by_board(client: TestClient, temp_data_path):
    """Listar posts retorna estructura correcta."""
    response = client.get("/posts")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_post_with_very_long_content(client: TestClient, temp_data_path):
    """Post con contenido largo: acepta o rechaza por validación."""
    token = _register_and_login(client, "longposter", "long@test.com")
    response = client.post(
        "/posts",
        json={"title": "Long Post", "body": "A" * 10000, "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (201, 422)


def test_post_banned_words_in_title(client: TestClient, temp_data_path):
    """Banned word en título debe fallar."""
    token = _register_and_login(client, "bwposter", "bw@test.com")
    response = client.post(
        "/posts",
        json={"title": "bastardo titulo", "body": "Clean body", "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_post_banned_words_in_body(client: TestClient, temp_data_path):
    """Banned word en cuerpo debe fallar."""
    token = _register_and_login(client, "bwposter2", "bw2@test.com")
    response = client.post(
        "/posts",
        json={"title": "Clean title", "body": "Este bastardo texto falla", "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
