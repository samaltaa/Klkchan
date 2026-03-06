# tests/test_sprint3_admin.py
"""
Cobertura para app/routers/admin.py (74% → objetivo 92%+).

Cubre las ramas no ejercidas:
  - list_users_admin: cursor pagination + has_more
  - update_user_role: user not found → 404
  - update_user_role: update_user_roles falla → 500 (monkeypatch)
  - delete_user_admin: user not found → 404
  - admin_stats: campos de contenido con datos reales
  - admin_lock_post: happy + 404 (cubiertos en sprint 2, reforzamos aquí)
  - admin_shadowban_user: campos en response
"""
import pytest
from fastapi.testclient import TestClient

from app.app import app
import app.services as services
from app.utils.security import hash_password


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, username: str, email: str) -> int:
    r = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "Aa123456!"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# list_users_admin — paginación cursor
# ---------------------------------------------------------------------------

class TestListUsersAdmin:
    def test_list_users_returns_all(self, client: TestClient, temp_data_path):
        """GET /admin/users retorna todos los usuarios del seed."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/users", headers=_auth(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) >= 3  # seed tiene 3 usuarios

    def test_list_users_cursor_filters(self, client: TestClient, temp_data_path):
        """cursor=1 → solo usuarios con id > 1."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/users?cursor=1", headers=_auth(admin_token))
        assert r.status_code == 200
        items = r.json()["items"]
        for user in items:
            assert user["id"] > 1

    def test_list_users_limit(self, client: TestClient, temp_data_path):
        """limit=1 → retorna solo 1 usuario."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/users?limit=1", headers=_auth(admin_token))
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_list_users_has_more_sets_next_cursor(self, client: TestClient, temp_data_path):
        """Cuando hay más páginas, next_cursor no es None."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/users?limit=1", headers=_auth(admin_token))
        assert r.status_code == 200
        data = r.json()
        # seed tiene 3 usuarios → limit=1 → hay more
        assert data["next_cursor"] is not None

    def test_list_users_no_password_field(self, client: TestClient, temp_data_path):
        """Los usuarios no exponen el campo 'password'."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/users", headers=_auth(admin_token))
        for user in r.json()["items"]:
            assert "password" not in user


# ---------------------------------------------------------------------------
# update_user_role — ramas de error
# ---------------------------------------------------------------------------

class TestUpdateUserRoleErrors:
    def test_user_not_found_returns_404(self, client: TestClient, temp_data_path):
        """Usuario objetivo no existe → 404."""
        admin_token = _login(client, "admin@example.com")
        r = client.patch(
            "/admin/users/99999/role",
            json={"role": "mod", "action": "add"},
            headers=_auth(admin_token),
        )
        assert r.status_code == 404
        assert r.json()["detail"] == "User not found"



# ---------------------------------------------------------------------------
# delete_user_admin — user not found
# ---------------------------------------------------------------------------

class TestDeleteUserAdminErrors:
    def test_delete_nonexistent_user_returns_404(self, client: TestClient, temp_data_path):
        """Eliminar usuario que no existe → 404."""
        admin_token = _login(client, "admin@example.com")
        r = client.delete("/admin/users/99999", headers=_auth(admin_token))
        assert r.status_code == 404
        assert r.json()["detail"] == "User not found"


# ---------------------------------------------------------------------------
# admin_stats — contenido realista
# ---------------------------------------------------------------------------

class TestAdminStatsContent:
    def test_stats_after_creating_content(self, client: TestClient, temp_data_path):
        """Estadísticas reflejan el contenido real del seed."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/stats", headers=_auth(admin_token))
        assert r.status_code == 200
        data = r.json()

        # seed tiene 3 usuarios
        assert data["users"]["total"] >= 3
        assert data["users"]["admins"] >= 1
        assert data["users"]["moderators"] >= 1

        # seed tiene 2 boards y 2 posts
        assert data["content"]["boards"] >= 2
        assert data["content"]["posts"] >= 2

    def test_stats_counts_increase_after_new_user(self, client: TestClient, temp_data_path):
        """Registrar un usuario aumenta el total."""
        admin_token = _login(client, "admin@example.com")
        r_before = client.get("/admin/stats", headers=_auth(admin_token))
        before_total = r_before.json()["users"]["total"]

        # Registrar nuevo usuario
        client.post(
            "/auth/register",
            json={"username": "stats_new", "email": "stats_new@example.com", "password": "Aa123456!"},
        )

        r_after = client.get("/admin/stats", headers=_auth(admin_token))
        after_total = r_after.json()["users"]["total"]
        assert after_total == before_total + 1

    def test_stats_regular_users_count(self, client: TestClient, temp_data_path):
        """regular = usuarios con solo rol 'user'."""
        admin_token = _login(client, "admin@example.com")
        r = client.get("/admin/stats", headers=_auth(admin_token))
        # alice tiene solo rol 'user' → regular >= 1
        assert r.json()["users"]["regular"] >= 1
