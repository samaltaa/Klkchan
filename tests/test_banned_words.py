# tests/test_banned_words.py
"""
Banned-word filter tests.
Uses real words from the LDNOOBW dictionaries:
  - Spanish (es.txt): "bastardo", "cabrón" / "cabron"
  - English  (en.txt): "anus", "arsehole"
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app
from app_v1.utils.banned_words import has_banned_words


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _create_post(client, token: str, title: str, body: str):
    return client.post(
        "/posts",
        json={"title": title, "body": body, "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_comment(client, token: str, body: str, post_id: int = 1):
    return client.post(
        "/comments",
        json={"post_id": post_id, "body": body},
        headers={"Authorization": f"Bearer {token}"},
    )


class TestBannedWordsUnit:
    """Direct unit tests for has_banned_words() utility."""

    def test_clean_text_passes(self):
        assert not has_banned_words("Hola, ¿cómo estás?", lang_hint="es")

    def test_spanish_banned_word_detected(self):
        assert has_banned_words("bastardo", lang_hint="es")

    def test_english_banned_word_detected(self):
        assert has_banned_words("anus", lang_hint="en")

    def test_banned_word_case_insensitive(self):
        assert has_banned_words("BASTARDO", lang_hint="es")
        assert has_banned_words("Bastardo", lang_hint="es")

    def test_leet_speak_bypass_blocked(self):
        # "b4st4rdo" normalizes to "bastardo"
        result = has_banned_words("b4st4rdo", lang_hint="es")
        assert result, "Leet speak bypass should be blocked"

    def test_empty_text_is_clean(self):
        assert not has_banned_words("", lang_hint="es")
        assert not has_banned_words("   ", lang_hint="es")


class TestBannedWordsAPI:
    """Integration tests: banned words block post/comment creation via API."""

    def test_post_with_clean_content_succeeds(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _create_post(client, token, "Bienvenidos", "Contenido completamente normal.")
        assert r.status_code == 201

    def test_post_with_banned_word_in_body_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _create_post(client, token, "Titulo normal", "Este bastardo texto debería fallar.")
        assert r.status_code == 400

    def test_post_with_banned_word_in_title_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _create_post(client, token, "bastardo titulo", "Cuerpo limpio.")
        assert r.status_code == 400

    def test_comment_with_banned_word_fails(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _create_comment(client, token, "cabrón comentario", post_id=1)
        assert r.status_code == 400

    def test_banned_word_case_insensitive_api(self, client, temp_data_path):
        token = _login(client, "alice@example.com")
        r = _create_post(client, token, "BASTARDO title", "Clean body.")
        assert r.status_code == 400
