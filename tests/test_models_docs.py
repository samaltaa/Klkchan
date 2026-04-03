# tests/test_models_docs.py
"""Tests para GET /docs/models (app/routers/models_docs.py)."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app_v1.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestModelsDocs:
    def test_returns_200(self, client: TestClient):
        r = client.get("/docs/models")
        assert r.status_code == 200

    def test_returns_html_content_type(self, client: TestClient):
        r = client.get("/docs/models")
        assert "text/html" in r.headers["content-type"]

    def test_body_contains_html_structure(self, client: TestClient):
        r = client.get("/docs/models")
        assert "<html" in r.text
        assert "<pre" in r.text

    def test_body_contains_klkchan_content(self, client: TestClient):
        r = client.get("/docs/models")
        assert "KLKCHAN" in r.text

    def test_missing_file_returns_404(self, client: TestClient, monkeypatch):
        monkeypatch.setattr(Path, "exists", lambda self: False)
        r = client.get("/docs/models")
        assert r.status_code == 404
