# tests/test_edge_cases.py
"""Tests de casos extremos y edge cases."""
import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.services import _next_id


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


def test_unicode_content_handling(client: TestClient, temp_data_path):
    """Sistema maneja contenido Unicode (emojis, caracteres especiales) correctamente."""
    token = _register_and_login(client, "unicodeuser", "unicode@test.com")
    response = client.post(
        "/posts",
        json={
            "title": "Test Unicode 中文 العربية",
            "body": "Contenido con caracteres especiales: émojis 😀 spëcial çhars",
            "board_id": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_empty_strings_vs_none(client: TestClient, temp_data_path):
    """String vacío en campo requerido falla validación."""
    token = _register_and_login(client, "emptystr", "emptystr@test.com")
    response = client.post(
        "/posts",
        json={"title": "", "body": "Content", "board_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_very_large_id_numbers():
    """_next_id maneja IDs muy grandes correctamente."""
    sequence = [{"id": 999999999}]
    assert _next_id(sequence) == 1000000000


def test_special_characters_in_username(client: TestClient, temp_data_path):
    """Username con caracteres especiales: válido o rechazado."""
    response = client.post(
        "/auth/register",
        json={
            "username": "user_valid-name",
            "email": "special@test.com",
            "password": "Testpass1",
        },
    )
    # Guiones y guiones bajos suelen ser aceptados
    assert response.status_code in (201, 422)


def test_duplicate_email_case_insensitive(client: TestClient, temp_data_path):
    """Emails duplicados con distinto case son rechazados."""
    client.post(
        "/auth/register",
        json={"username": "dupuser1", "email": "dup@example.com", "password": "Testpass1"},
    )
    response = client.post(
        "/auth/register",
        json={"username": "dupuser2", "email": "DUP@EXAMPLE.COM", "password": "Testpass1"},
    )
    assert response.status_code == 400


def test_whitespace_in_username(client: TestClient, temp_data_path):
    """Username con espacios debe ser rechazado."""
    response = client.post(
        "/auth/register",
        json={"username": "user name", "email": "ws@test.com", "password": "Testpass1"},
    )
    assert response.status_code in (400, 422)


def test_sql_injection_attempt_in_content(client: TestClient, temp_data_path):
    """SQL injection en contenido es inofensivo (almacenamiento JSON)."""
    token = _register_and_login(client, "sqlinject", "sqlinject@test.com")
    response = client.post(
        "/posts",
        json={
            "title": "'; DROP TABLE users; --",
            "body": "Content",
            "board_id": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # JSON storage: no SQL, se almacena como texto
    assert response.status_code in (201, 400)


def test_xss_attempt_in_content(client: TestClient, temp_data_path):
    """XSS en contenido es almacenado como texto (sanitización en frontend)."""
    token = _register_and_login(client, "xssuser", "xss@test.com")
    response = client.post(
        "/posts",
        json={
            "title": "Test XSS",
            "body": "<script>alert('XSS')</script>",
            "board_id": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201


def test_next_id_with_empty_sequence():
    """_next_id con lista vacía retorna 1."""
    assert _next_id([]) == 1
