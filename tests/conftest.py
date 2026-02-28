# tests/conftest.py
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.app import app
import app.services as services
from app.utils.security import hash_password
from app.utils.limiter import limiter


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limits():
    """Disable SlowAPI rate limiting for the entire test session."""
    limiter.enabled = False
    yield
    limiter.enabled = True


# 1) Limpia/crea tests/_tmp por ejecución de pytest
@pytest.fixture(scope="session", autouse=True)
def _ensure_tmp_dir_session():
    tmp_dir = Path(__file__).parent / "_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    print(f"[tests] Carpeta temporal creada: {tmp_dir}")


# 2) Redirige DATA_PATH y resetea estructura base por test
@pytest.fixture(scope="function", autouse=True)
def temp_data_path(monkeypatch):
    tmp_dir = Path(__file__).parent / "_tmp"
    data_file = tmp_dir / "test_data.json"

    monkeypatch.setattr(services, "DATA_PATH", data_file, raising=False)

    # estructura base vacía
    base = {
        "users": [],
        "posts": [],
        "comments": [],
        "boards": [],
        "replies": [],
    }
    data_file.write_text(json.dumps(base, ensure_ascii=False, indent=4), encoding="utf-8")

    # Forzar a services a “ver” ese archivo y directorio (crea parent si hiciera falta)
    services.load_data()

    # ---- seed por test ----
    _seed_minimal_fixture()

    yield data_file
    # no borramos para que puedas inspeccionarlo post-test


def _seed_minimal_fixture():
    """Inserta datos de ejemplo suficientes para probar endpoints cómodamente."""
    now = datetime.now(timezone.utc).isoformat()

    users = [
        {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "password": hash_password("Aa123456!"),
            "posts": [],
        },
        {
            "id": 2,
            "username": "mod",
            "email": "mod@example.com",
            "password": hash_password("Aa123456!"),
            "posts": [],
        },
        {
            "id": 3,
            "username": "alice",
            "email": "alice@example.com",
            "password": hash_password("Aa123456!"),
            "posts": [],
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


# 3) Cliente FastAPI
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
