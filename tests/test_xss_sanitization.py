# tests/test_xss_sanitization.py
"""
Tests de sanitización XSS para posts y comentarios.

Verifica que sanitize_html() se aplica correctamente antes de persistir
el body (y title) de posts y comentarios, eliminando tags peligrosos
con su contenido y conservando el texto de tags benignos.
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.utils.helpers import sanitize_html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str = "alice@example.com", password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login falló: {r.text}"
    return r.json()["access_token"]


def _create_post(client: TestClient, token: str, body: str, title: str = "Test XSS") -> dict:
    r = client.post(
        "/posts",
        json={"title": title, "body": body, "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"create_post falló: {r.text}"
    return r.json()


def _create_comment(client: TestClient, token: str, body: str, post_id: int = 1) -> dict:
    r = client.post(
        "/comments",
        json={"body": body, "post_id": post_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"create_comment falló: {r.text}"
    return r.json()


# ---------------------------------------------------------------------------
# Tests de endpoints — POST /posts
# ---------------------------------------------------------------------------

def test_post_body_script_tag_is_removed(client: TestClient):
    """POST /posts con body=<script>xss()</script> → body guardado = ''."""
    token = _login(client)
    post = _create_post(client, token, body="<script>xss()</script>")
    assert post["body"] == ""


def test_post_body_benign_tag_preserves_text(client: TestClient):
    """POST /posts con body=<b>hola</b> mundo → body = 'hola mundo'."""
    token = _login(client)
    post = _create_post(client, token, body="<b>hola</b> mundo")
    assert post["body"] == "hola mundo"


def test_post_body_style_tag_removes_content(client: TestClient):
    """POST /posts con style tag → contenido del style se elimina, texto circundante se conserva."""
    token = _login(client)
    post = _create_post(client, token, body="texto <style>body{}</style> limpio")
    assert post["body"] == "texto  limpio"


def test_post_body_no_html_unchanged(client: TestClient):
    """POST /posts con body sin HTML → no se modifica el texto."""
    token = _login(client)
    cuerpo = "Este es un cuerpo de post totalmente normal sin etiquetas"
    post = _create_post(client, token, body=cuerpo)
    assert post["body"] == cuerpo


# ---------------------------------------------------------------------------
# Tests de endpoints — POST /comments
# ---------------------------------------------------------------------------

def test_comment_body_iframe_tag_is_removed(client: TestClient):
    """POST /comments con body=<iframe src='x'> → body guardado = ''."""
    token = _login(client)
    comment = _create_comment(client, token, body="<iframe src='x'>")
    assert comment["body"] == ""


# ---------------------------------------------------------------------------
# Tests unitarios — sanitize_html()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tag", ["script", "style", "iframe", "object", "embed", "form", "noscript"])
def test_sanitize_html_removes_dangerous_tag_and_content(tag: str):
    """Cada tag peligroso: el tag Y su contenido interior se eliminan."""
    payload = f"<{tag}>contenido peligroso</{tag}>"
    resultado = sanitize_html(payload)
    assert resultado == "", f"Tag <{tag}> no fue eliminado: '{resultado}'"


def test_sanitize_html_dangerous_tag_unclosed():
    """Tag peligroso sin cerrar (ej: <iframe src='x'>) queda vacío."""
    assert sanitize_html("<iframe src='evil.com'>") == ""


def test_sanitize_html_benign_tags_preserve_text():
    """Tags benignos como <b>, <em>, <p> conservan el texto interior."""
    assert sanitize_html("<b>negrita</b>") == "negrita"
    assert sanitize_html("<em>énfasis</em>") == "énfasis"
    assert sanitize_html("<p>párrafo</p>") == "párrafo"


def test_sanitize_html_mixed_content():
    """Mezcla de tags peligrosos y benignos: solo peligrosos pierden contenido."""
    resultado = sanitize_html("<b>texto</b><script>alert(1)</script>")
    assert resultado == "texto"


def test_sanitize_html_case_insensitive():
    """La sanitización es case-insensitive para los tags peligrosos."""
    assert sanitize_html("<SCRIPT>evil()</SCRIPT>") == ""
    assert sanitize_html("<Script>evil()</Script>") == ""
