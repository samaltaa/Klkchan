# tests/test_roles.py
"""
Tests del sistema de roles:
- _assign_initial_roles asigna roles correctamente según env vars
- Endpoints /admin/* requieren rol admin
- PATCH /admin/users/{id}/role añade/remueve roles
- Admin no puede auto-eliminarse ni quitarse su propio rol admin
- Moderador puede acceder a /moderation/queue
"""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client: TestClient, username: str, email: str, password: str = "Testpass1") -> dict:
    """Registra un usuario y retorna {token, id}."""
    r = client.post("/auth/register", json={"username": username, "email": email, "password": password})
    assert r.status_code == 201, f"register failed ({r.status_code}): {r.text}"
    user_id = r.json()["id"]
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, f"login failed: {login.text}"
    return {"token": login.json()["access_token"], "id": user_id}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Unit: _assign_initial_roles
# ---------------------------------------------------------------------------

def test_unknown_email_gets_user_role_only(monkeypatch):
    """Email desconocido → solo rol 'user'."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin@x.com")
    monkeypatch.setenv("MOD_EMAILS", "mod@x.com")
    from app_v1.routers.auth import _assign_initial_roles
    assert _assign_initial_roles("nobody@x.com") == ["user"]


def test_admin_email_gets_admin_role(monkeypatch):
    """Email en ADMIN_EMAILS → ['user', 'admin']."""
    monkeypatch.setenv("ADMIN_EMAILS", "boss@x.com,cto@x.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    from app_v1.routers.auth import _assign_initial_roles
    roles = _assign_initial_roles("boss@x.com")
    assert "admin" in roles
    assert "user" in roles
    assert "mod" not in roles


def test_mod_email_gets_mod_role(monkeypatch):
    """Email en MOD_EMAILS → ['user', 'mod'], sin admin."""
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("MOD_EMAILS", "cop@x.com")
    from app_v1.routers.auth import _assign_initial_roles
    roles = _assign_initial_roles("cop@x.com")
    assert "mod" in roles
    assert "user" in roles
    assert "admin" not in roles


def test_admin_email_not_also_mod(monkeypatch):
    """Si el email está en ADMIN_EMAILS no debe recibir también 'mod'."""
    monkeypatch.setenv("ADMIN_EMAILS", "dual@x.com")
    monkeypatch.setenv("MOD_EMAILS", "dual@x.com")
    from app_v1.routers.auth import _assign_initial_roles
    roles = _assign_initial_roles("dual@x.com")
    assert "admin" in roles
    assert "mod" not in roles  # admin tiene prioridad (elif)


def test_email_matching_is_case_insensitive(monkeypatch):
    """Los emails en env vars se comparan sin distinción de mayúsculas."""
    monkeypatch.setenv("ADMIN_EMAILS", "Admin@X.COM")
    monkeypatch.setenv("MOD_EMAILS", "")
    from app_v1.routers.auth import _assign_initial_roles
    roles = _assign_initial_roles("admin@x.com")
    assert "admin" in roles


# ---------------------------------------------------------------------------
# Integration: register + login con roles asignados
# ---------------------------------------------------------------------------

def test_register_assigns_admin_role_via_env(client: TestClient, monkeypatch):
    """Registrar con email en ADMIN_EMAILS → token contiene rol admin."""
    monkeypatch.setenv("ADMIN_EMAILS", "superadmin@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    info = _register_and_login(client, "superadmin_r", "superadmin@test.com")
    # Verificar que puede acceder a endpoint admin-only
    r = client.get("/admin/stats", headers=_auth(info["token"]))
    assert r.status_code == 200


def test_register_assigns_mod_role_via_env(client: TestClient, monkeypatch):
    """Registrar con email en MOD_EMAILS → puede acceder a /moderation/queue."""
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("MOD_EMAILS", "supermod@test.com")
    info = _register_and_login(client, "supermod_r", "supermod@test.com")
    r = client.get("/moderation/queue", headers=_auth(info["token"]))
    assert r.status_code == 200


def test_regular_user_cannot_access_admin_stats(client: TestClient, monkeypatch):
    """Usuario normal no puede acceder a /admin/stats → 403."""
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("MOD_EMAILS", "")
    info = _register_and_login(client, "plain_r", "plain_r@test.com")
    r = client.get("/admin/stats", headers=_auth(info["token"]))
    assert r.status_code == 403


def test_regular_user_cannot_access_admin_users(client: TestClient, monkeypatch):
    """Usuario normal no puede listar usuarios via /admin/users → 403."""
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("MOD_EMAILS", "")
    info = _register_and_login(client, "plain_r2", "plain_r2@test.com")
    r = client.get("/admin/users", headers=_auth(info["token"]))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Integration: PATCH /admin/users/{id}/role
# ---------------------------------------------------------------------------

def test_admin_can_grant_mod_role(client: TestClient, monkeypatch):
    """Admin puede dar rol mod a otro usuario."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_grant@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    admin = _register_and_login(client, "admin_grant", "admin_grant@test.com")
    target = _register_and_login(client, "target_grant", "target_grant@test.com")

    r = client.patch(
        f"/admin/users/{target['id']}/role",
        json={"role": "mod", "action": "add"},
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 200
    data = r.json()
    assert "mod" in data["roles"]
    assert "user" in data["roles"]  # rol base siempre presente


def test_admin_can_remove_mod_role(client: TestClient, monkeypatch):
    """Admin puede quitar rol mod a un usuario."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_rem@test.com")
    monkeypatch.setenv("MOD_EMAILS", "mod_rem@test.com")
    admin = _register_and_login(client, "admin_rem", "admin_rem@test.com")
    mod_user = _register_and_login(client, "mod_rem", "mod_rem@test.com")

    # Quitar el rol mod
    r = client.patch(
        f"/admin/users/{mod_user['id']}/role",
        json={"role": "mod", "action": "remove"},
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 200
    assert "mod" not in r.json()["roles"]
    assert "user" in r.json()["roles"]


def test_admin_cannot_remove_own_admin_role(client: TestClient, monkeypatch):
    """Admin no puede quitarse a sí mismo el rol admin → 400."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_self@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    admin = _register_and_login(client, "admin_self", "admin_self@test.com")

    r = client.patch(
        f"/admin/users/{admin['id']}/role",
        json={"role": "admin", "action": "remove"},
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 400
    assert "Cannot remove admin role from yourself" in r.json()["detail"]


def test_cannot_remove_base_user_role(client: TestClient, monkeypatch):
    """No se puede quitar el rol 'user' (rol base) → 400."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_base@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    admin = _register_and_login(client, "admin_base", "admin_base@test.com")
    target = _register_and_login(client, "target_base", "target_base@test.com")

    r = client.patch(
        f"/admin/users/{target['id']}/role",
        json={"role": "user", "action": "remove"},
        headers=_auth(admin["token"]),
    )
    assert r.status_code == 400
    assert "base role" in r.json()["detail"]


def test_regular_user_cannot_patch_roles(client: TestClient, monkeypatch):
    """Usuario normal no puede modificar roles → 403."""
    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setenv("MOD_EMAILS", "")
    attacker = _register_and_login(client, "attacker_r", "attacker_r@test.com")
    target = _register_and_login(client, "victim_r", "victim_r@test.com")

    r = client.patch(
        f"/admin/users/{target['id']}/role",
        json={"role": "admin", "action": "add"},
        headers=_auth(attacker["token"]),
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Integration: DELETE /admin/users/{id}
# ---------------------------------------------------------------------------

def test_admin_can_delete_other_user(client: TestClient, monkeypatch):
    """Admin puede eliminar otro usuario → 204."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_del@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    admin = _register_and_login(client, "admin_del", "admin_del@test.com")
    victim = _register_and_login(client, "victim_del", "victim_del@test.com")

    r = client.delete(f"/admin/users/{victim['id']}", headers=_auth(admin["token"]))
    assert r.status_code == 204


def test_admin_cannot_delete_self(client: TestClient, monkeypatch):
    """Admin no puede eliminarse a sí mismo → 400."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_nodel@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    admin = _register_and_login(client, "admin_nodel", "admin_nodel@test.com")

    r = client.delete(f"/admin/users/{admin['id']}", headers=_auth(admin["token"]))
    assert r.status_code == 400
    assert "Cannot delete your own account" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Integration: GET /admin/stats
# ---------------------------------------------------------------------------

def test_admin_stats_returns_correct_structure(client: TestClient, monkeypatch):
    """GET /admin/stats retorna estructura con users y content."""
    monkeypatch.setenv("ADMIN_EMAILS", "admin_stats@test.com")
    monkeypatch.setenv("MOD_EMAILS", "")
    admin = _register_and_login(client, "admin_stats", "admin_stats@test.com")

    r = client.get("/admin/stats", headers=_auth(admin["token"]))
    assert r.status_code == 200
    data = r.json()
    assert "users" in data
    assert "content" in data
    assert "total" in data["users"]
    assert "posts" in data["content"]
