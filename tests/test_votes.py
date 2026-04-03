# tests/test_votes.py
"""Voting system tests — POST /interactions/votes, GET /interactions/votes/{type}/{id}"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def _make_comment(client, token: str, post_id: int = 1, body: str = "test comment") -> int:
    r = client.post(
        "/comments",
        json={"post_id": post_id, "body": body},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"create comment failed: {r.text}"
    return r.json()["id"]


def _vote(client, token: str, target_type: str, target_id: int, value: int):
    return client.post(
        "/interactions/votes",
        json={"target_type": target_type, "target_id": target_id, "value": value},
        headers={"Authorization": f"Bearer {token}"},
    )


class TestVotePost:
    def test_upvote_post(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _vote(client, token, "post", 1, 1)
        assert r.status_code == 200
        body = r.json()
        assert body["target_type"] == "post"
        assert body["target_id"] == 1
        assert body["score"] == 1
        assert body["upvotes"] == 1
        assert body["downvotes"] == 0
        assert body["user_vote"] == 1

    def test_downvote_post(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _vote(client, token, "post", 1, -1)
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == -1
        assert body["upvotes"] == 0
        assert body["downvotes"] == 1
        assert body["user_vote"] == -1

    def test_change_vote_upvote_to_downvote(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        _vote(client, token, "post", 1, 1)  # upvote first
        r = _vote(client, token, "post", 1, -1)  # then downvote
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == -1
        assert body["user_vote"] == -1

    def test_remove_vote(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        _vote(client, token, "post", 1, 1)  # upvote
        r = _vote(client, token, "post", 1, 0)  # remove
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 0
        assert body["upvotes"] == 0
        assert body["downvotes"] == 0

    def test_vote_nonexistent_post_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _vote(client, token, "post", 9999, 1)
        assert r.status_code == 404

    def test_vote_without_auth_fails(self, client, temp_data_path):
        r = client.post(
            "/interactions/votes",
            json={"target_type": "post", "target_id": 1, "value": 1},
        )
        assert r.status_code == 401

    def test_vote_statistics_accurate(self, client, temp_data_path):
        """Three users vote differently; summary totals must be correct."""
        t1 = _login(client, "admin@example.com")
        t2 = _login(client, "mod@example.com")
        t3 = _login(client, "alice@example.com")
        _vote(client, t1, "post", 1, 1)
        _vote(client, t2, "post", 1, 1)
        _vote(client, t3, "post", 1, -1)

        r = client.get("/interactions/votes/post/1")
        assert r.status_code == 200
        body = r.json()
        assert body["upvotes"] == 2
        assert body["downvotes"] == 1
        assert body["score"] == 1

    def test_multiple_users_can_vote_same_post(self, client, temp_data_path):
        t1 = _login(client, "admin@example.com")
        t2 = _login(client, "mod@example.com")
        r1 = _vote(client, t1, "post", 1, 1)
        r2 = _vote(client, t2, "post", 1, 1)
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Summary should reflect both votes
        r = client.get("/interactions/votes/post/1")
        assert r.json()["upvotes"] == 2


class TestVoteComment:
    def test_vote_comment(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        comment_id = _make_comment(client, token, post_id=1)
        r = _vote(client, token, "comment", comment_id, 1)
        assert r.status_code == 200
        body = r.json()
        assert body["target_type"] == "comment"
        assert body["target_id"] == comment_id
        assert body["score"] == 1

    def test_vote_nonexistent_comment_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _vote(client, token, "comment", 9999, 1)
        assert r.status_code == 404
