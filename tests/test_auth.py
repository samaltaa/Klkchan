# tests/test_auth.py
import uuid

REGISTER_ENDPOINT = "/auth/register"          # ✔ según tu auth.py
LOGIN_ENDPOINT     = "/auth/login"            # ✔ OAuth2PasswordRequestForm (form-data)
CHANGE_PWD_ENDPOINT= "/auth/change-password"  # ✔ PATCH, 204
FORGOT_PWD_ENDPOINT= "/auth/forgot-password"  # ✔ 204 No Content
LOGOUT_ENDPOINT    = "/auth/logout"           # ✔ requiere token

def _unique_user():
    suf = uuid.uuid4().hex[:8]
    return {
        "username": f"user_{suf}",
        "email": f"user_{suf}@example.com",
        "password": "Aa123456!",
    }

def _register(client, payload):
    # Tu registro espera JSON con username, email, password
    r = client.post(REGISTER_ENDPOINT, json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert "id" in data
    return data

def _login(client, email, password):
    # Tu login usa OAuth2PasswordRequestForm → form-data con "username"=email
    r = client.post(LOGIN_ENDPOINT, data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert body.get("token_type") == "bearer"
    return body["access_token"]

def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}

# ------------------------ TESTS ------------------------

def test_register_and_login_success(client):
    user = _unique_user()
    _register(client, user)
    token = _login(client, user["email"], user["password"])
    assert isinstance(token, str) and len(token) > 10

def test_login_wrong_password(client):
    user = _unique_user()
    _register(client, user)
    r = client.post(LOGIN_ENDPOINT, data={"username": user["email"], "password": "WrongPass1!"})
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "Credenciales inválidas"

def test_login_nonexistent_user(client):
    r = client.post(LOGIN_ENDPOINT, data={"username": "no@existe.com", "password": "Aa123456!"})
    # Tu login devuelve 401 para credenciales inválidas
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "Credenciales inválidas"

def test_protected_endpoint_requires_token(client):
    # Crear post sin token debe fallar (tu /posts requiere get_current_user)
    payload = {"title": "Post sin token", "body": "contenido", "board_id": 1}
    r = client.post("/posts", json=payload)
    assert r.status_code in (401, 403), r.text

def test_protected_endpoint_with_token(client):
    user = _unique_user()
    _register(client, user)
    token = _login(client, user["email"], user["password"])

    payload = {"title": "Título válido", "body": "Contenido válido", "board_id": 1}
    r = client.post("/posts", json=payload, headers=_auth_headers(token))
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["title"] == "Título válido"

def test_change_password_flow(client):
    user = _unique_user()
    _register(client, user)
    token = _login(client, user["email"], user["password"])

    # Cambiar contraseña (204 No Content)
    body = {"old_password": user["password"], "new_password": "Bb987654!"}
    r = client.patch(CHANGE_PWD_ENDPOINT, json=body, headers=_auth_headers(token))
    assert r.status_code == 204, r.text

    # Vieja contraseña ya NO debe servir
    r_old = client.post(LOGIN_ENDPOINT, data={"username": user["email"], "password": user["password"]})
    assert r_old.status_code == 401, r_old.text

    # Nueva sí
    r_new = client.post(LOGIN_ENDPOINT, data={"username": user["email"], "password": "Bb987654!"})
    assert r_new.status_code == 200, r_new.text

def test_forgot_password_returns_204(client):
    # Por seguridad, siempre 204 No Content
    r = client.post(FORGOT_PWD_ENDPOINT, json={"email": "alguien@quizas.no"})
    assert r.status_code == 204, r.text

def test_logout_requires_token_and_returns_message(client):
    user = _unique_user()
    _register(client, user)
    token = _login(client, user["email"], user["password"])
    r = client.post(LOGOUT_ENDPOINT, headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    body = r.json()
    # Por tu schema LogoutResponse, el detalle por defecto es "Logged out"
    assert body.get("detail") == "Logged out"
