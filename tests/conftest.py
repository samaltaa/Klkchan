# tests/conftest.py
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app_v1.app import app
import app_v1.services as services
from app_v1.utils.security import hash_password
from app_v1.utils.limiter import limiter


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limits():
    """Disable SlowAPI rate limiting for the entire test session."""
    limiter.enabled = False
    yield
    limiter.enabled = True


# Redirige DATA_PATH a un directorio exclusivo por test (tmp_path de pytest).
# Cada test obtiene su propio test_data.json y test_data.tmp, eliminando la
# condicion de carrera de Windows donde el worker thread de anyio (client
# module-scoped) mantenia un handle sobre test_data.tmp mientras el setUp
# del siguiente test intentaba escribir sobre el mismo path.
@pytest.fixture(scope="function", autouse=True)
def temp_data_path(monkeypatch, tmp_path):
    data_file = tmp_path / "test_data.json"

    monkeypatch.setattr(services, "DATA_PATH", data_file, raising=False)

    # estructura base vacia
    base = {
        "users": [],
        "posts": [],
        "comments": [],
        "boards": [],
        "replies": [],
    }
    data_file.write_text(json.dumps(base, ensure_ascii=False, indent=4), encoding="utf-8")

    # Forzar a services a "ver" ese archivo y directorio (crea parent si hiciera falta)
    services.load_data()

    # ---- seed por test ----
    _seed_minimal_fixture()

    yield data_file
    # pytest retiene los ultimos 3 runs en tmp_path para inspeccion post-test


def _seed_minimal_fixture():
    """Inserta datos de ejemplo suficientes para probar endpoints comodamente."""
    now = datetime.now(timezone.utc).isoformat()

    users = [
        {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "password": hash_password("Aa123456!"),
            "posts": [],
            "roles": ["user", "admin"],
        },
        {
            "id": 2,
            "username": "mod",
            "email": "mod@example.com",
            "password": hash_password("Aa123456!"),
            "posts": [],
            "roles": ["user", "mod"],
        },
        {
            "id": 3,
            "username": "alice",
            "email": "alice@example.com",
            "password": hash_password("Aa123456!"),
            "posts": [],
            "roles": ["user"],
        },
    ]

    boards = [
        {"id": 1, "name": "General", "description": "Todo vale"},
        {"id": 2, "name": "Tech", "description": "Hardware/Software"},
    ]

    posts = [
        {
            "id": 1,
            "title": "Hola",
            "body": "contenido",
            "board_id": 1,
            "created_at": now,
            "votes": 0,
            "user_id": 3,  # alice
            "comments": [],
        },
        {
            "id": 2,
            "title": "Primer post tech",
            "body": "probando",
            "board_id": 2,
            "created_at": now,
            "votes": 0,
            "user_id": 3,
            "comments": [],
        },
    ]

    # Vincular posts a la usuaria
    users[2]["posts"] = [1, 2]

    data = {
        "users": users,
        "boards": boards,
        "posts": posts,
        "comments": [],
        "replies": [],
    }
    services.save_data(data)
    print("[tests] Seed cargado: 3 usuarios, 2 boards, 2 posts")


# Cliente FastAPI
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
