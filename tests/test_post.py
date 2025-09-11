# tests/test_post.py
import uuid

def _unique_user():
    suf = uuid.uuid4().hex[:6]
    return {
        "username": f"poster_{suf}",
        "email": f"poster_{suf}@example.com",
        "password": "Aa123456!",
    }

def _register_and_login(client):
    user = _unique_user()
    # registro: tu endpoint real
    r_reg = client.post("/auth/register", json=user)
    assert r_reg.status_code == 201, r_reg.text

    # login: OAuth2PasswordRequestForm -> "username" = EMAIL (según tu auth.py)
    r_log = client.post("/auth/login", data={
        "username": user["email"],
        "password": user["password"],
    })
    assert r_log.status_code == 200, r_log.text
    token = r_log.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_post_ok(client):
    headers = _register_and_login(client)
    r = client.post("/posts", json={
        "title": "Título válido",
        "body": "Contenido válido",
        "board_id": 1
    }, headers=headers)
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["title"] == "Título válido"
    assert "id" in data

def test_create_post_minimal_payload(client):
    headers = _register_and_login(client)
    # como no tienes validaciones de longitud hoy, este debe pasar
    r = client.post("/posts", json={
        "title": "Hi",
        "body": "ok",
        "board_id": 1
    }, headers=headers)
    assert r.status_code in (200, 201), r.text
