# tests/test_cascade_delete.py
"""Cascade delete tests: verify that votes are removed when their target is deleted."""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app
import app_v1.services as services


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def _add_vote(client, token: str, target_type: str, target_id: int, value: int = 1):
    r = client.post(
        "/interactions/votes",
        json={"target_type": target_type, "target_id": target_id, "value": value},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, f"vote failed: {r.text}"


def _get_votes(filter_type: str = None, filter_id: int = None) -> list:
    data = services.load_data()
    votes = data.get("votes", [])
    if filter_type:
        votes = [v for v in votes if v.get("target_type") == filter_type]
    if filter_id is not None:
        votes = [v for v in votes if v.get("target_id") == filter_id]
    return votes


class TestCascadeDeletePost:
    def test_votes_on_post_removed_when_post_deleted(self, client, temp_data_path):
        # admin votes on post 1; alice (owner) deletes it
        admin_token = _login(client, "admin@example.com")
        alice_token = _login(client, "alice@example.com")
        _add_vote(client, admin_token, "post", 1)
        assert len(_get_votes("post", 1)) == 1, "vote should exist"

        # alice owns post 1 in the seed
        r = client.delete("/posts/1", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 204

        assert len(_get_votes("post", 1)) == 0, "vote should be removed with post"

    def test_votes_on_comments_removed_when_post_deleted(self, client, temp_data_path):
        admin_token = _login(client, "admin@example.com")
        alice_token = _login(client, "alice@example.com")
        # Create a comment on post 1
        r = client.post(
            "/comments",
            json={"post_id": 1, "body": "test comment"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 201
        comment_id = r.json()["id"]

        # Vote on that comment
        _add_vote(client, admin_token, "comment", comment_id)
        assert len(_get_votes("comment", comment_id)) == 1

        # alice (owner) deletes the parent post — should cascade to comment votes
        r = client.delete("/posts/1", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 204

        assert len(_get_votes("comment", comment_id)) == 0, "comment vote should be removed with post"


class TestCascadeDeleteComment:
    def test_votes_on_comment_removed_when_comment_deleted(self, client, temp_data_path):
        token = _login(client, "admin@example.com")
        # Create comment
        r = client.post(
            "/comments",
            json={"post_id": 1, "body": "deletable comment"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        comment_id = r.json()["id"]

        # Add two votes
        token2 = _login(client, "alice@example.com")
        _add_vote(client, token, "comment", comment_id, 1)
        _add_vote(client, token2, "comment", comment_id, -1)
        assert len(_get_votes("comment", comment_id)) == 2

        # Delete the comment
        r = client.delete(f"/comments/{comment_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204

        assert len(_get_votes("comment", comment_id)) == 0, "votes should be removed with comment"


class TestCascadeDeleteUser:
    def test_votes_by_user_removed_when_user_deleted(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        # alice votes on post 1
        _add_vote(client, token, "post", 1)
        alice_id = 3  # seed user id

        data = services.load_data()
        alice_votes_before = [v for v in data.get("votes", []) if v.get("user_id") == alice_id]
        assert len(alice_votes_before) == 1

        # alice deletes herself
        r = client.delete("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 204

        data = services.load_data()
        alice_votes_after = [v for v in data.get("votes", []) if v.get("user_id") == alice_id]
        assert len(alice_votes_after) == 0, "votes cast by deleted user should be removed"

    def test_votes_on_user_posts_removed_when_user_deleted(self, client, temp_data_path):
        # admin votes on alice's post 1
        admin_token = _login(client, "admin@example.com")
        _add_vote(client, admin_token, "post", 1)
        assert len(_get_votes("post", 1)) == 1

        # alice deletes herself (post 1 is hers, seed user_id=3)
        alice_token = _login(client, "alice@example.com")
        r = client.delete("/users/me", headers={"Authorization": f"Bearer {alice_token}"})
        assert r.status_code == 204

        # Post 1 is gone, its votes should be gone too
        assert len(_get_votes("post", 1)) == 0, "votes on deleted user's posts should be removed"


class TestCascadeDeleteBoard:
    def test_votes_on_board_posts_removed_when_board_deleted(self, client, temp_data_path):
        admin_token = _login(client, "admin@example.com")
        # Vote on post 1 (which is on board 1)
        _add_vote(client, admin_token, "post", 1)
        assert len(_get_votes("post", 1)) == 1

        # Delete board 1 — admin required
        r = client.delete("/boards/1", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 204

        assert len(_get_votes("post", 1)) == 0, "votes on board posts should be removed with board"
