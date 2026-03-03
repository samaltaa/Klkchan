# tests/test_pagination.py
"""Tests para paginación cursor-based."""
import pytest
from fastapi.testclient import TestClient

from app.app import app


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


def test_pagination_first_page(client: TestClient, temp_data_path):
    """Primera página sin cursor retorna 200 y estructura correcta."""
    response = client.get("/posts?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "limit" in body
    assert "next_cursor" in body


def test_pagination_respects_limit(client: TestClient, temp_data_path):
    """El límite solicitado se respeta en la respuesta."""
    response = client.get("/posts?limit=1")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) <= 1


def test_pagination_empty_results(client: TestClient, temp_data_path):
    """Paginación con cursor más allá de los datos retorna lista vacía."""
    response = client.get("/posts?cursor=999999")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"], list)
    assert len(body["items"]) == 0


def test_pagination_consistent_ordering(client: TestClient, temp_data_path):
    """Posts están ordenados por ID ascendente."""
    token = _register_and_login(client, "orderpager", "orderpager@test.com")
    created_ids = []
    for i in range(3):
        r = client.post(
            "/posts",
            json={"title": f"Order Post {i}", "body": "content", "board_id": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        created_ids.append(r.json()["id"])

    response = client.get("/posts")
    all_ids = [p["id"] for p in response.json()["items"]]
    filtered = [pid for pid in all_ids if pid in created_ids]
    assert filtered == sorted(filtered)


def test_boards_pagination(client: TestClient, temp_data_path):
    """Paginación de boards funciona con estructura correcta."""
    response = client.get("/boards?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert len(body["items"]) <= 10
