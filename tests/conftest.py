import pytest
from fastapi.testclient import TestClient
from app.app import app

@pytest.fixture(scope="module")
def client():
    """
    Fixture que devuelve un TestClient de FastAPI.
    Se comparte entre todos los tests del mismo módulo.
    """
    with TestClient(app) as c:
        yield c
