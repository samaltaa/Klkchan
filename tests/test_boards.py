# tests/test_boards.py
"""Board CRUD tests — GET/POST/PUT/DELETE /boards"""
import pytest
from fastapi.testclient import TestClient

from app.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


_BOARD_PAYLOAD = {"name": "TestBoard", "description": "A test board"}


def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestBoardCreate:
    def test_create_board(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = client.post("/boards", json=_BOARD_PAYLOAD, headers=_auth(token))
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "TestBoard"
        assert body["description"] == "A test board"
        assert "id" in body

    def test_create_board_with_banned_word_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = client.post("/boards", json={"name": "bastardo board", "description": "test"}, headers=_auth(token))
        assert r.status_code == 400

    def test_create_board_missing_name_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = client.post("/boards", json={"description": "no name"}, headers=_auth(token))
        assert r.status_code == 422


class TestBoardList:
    def test_list_boards(self, client, temp_data_path):
        r = client.get("/boards")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert isinstance(body["items"], list)
        # Seed has 2 boards
        assert len(body["items"]) >= 2

    def test_list_boards_pagination(self, client, temp_data_path):
        r = client.get("/boards?limit=1")
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1
        assert body["limit"] == 1

    def test_list_boards_cursor(self, client, temp_data_path):
        """Cursor filters out boards with id <= cursor value."""
        # Seed has boards with ids 1 and 2
        r = client.get("/boards?cursor=1")
        assert r.status_code == 200
        items = r.json()["items"]
        for board in items:
            assert board["id"] > 1


class TestBoardGet:
    def test_get_single_board(self, client, temp_data_path):
        r = client.get("/boards/1")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == 1
        assert body["name"] == "General"

    def test_get_nonexistent_board_returns_404(self, client, temp_data_path):
        r = client.get("/boards/9999")
        assert r.status_code == 404


class TestBoardUpdate:
    def test_update_board_name(self, client, temp_data_path):
        token = _login(client, "admin@example.com")
        r = client.put("/boards/1", json={"name": "Updated General"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["name"] == "Updated General"

    def test_update_board_with_banned_word_fails(self, client, temp_data_path):
        token = _login(client, "admin@example.com")
        r = client.put("/boards/1", json={"description": "bastardo content"}, headers=_auth(token))
        assert r.status_code == 400

    def test_update_nonexistent_board_returns_404(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = client.put("/boards/9999", json={"name": "Ghost"}, headers=_auth(token))
        assert r.status_code == 404
