# tests/test_sprint2_admin_moderation.py
"""
Tests para los endpoints de moderación administrativa de Sprint 2:
  POST /admin/posts/{id}/lock
  POST /admin/posts/{id}/sticky
  POST /admin/users/{id}/shadowban

Cada endpoint tiene:
  - Happy path (200)
  - 404 target not found
  - 403 usuario sin rol admin
  - 401 sin token
  - 400 casos de negocio (shadowban self)
  - Idempotencia
"""
import pytest
from fastapi.testclient import TestClient

from app.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client: TestClient, email: str, password: str = "Aa123456!") -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_post(client: TestClient, token: str, board_id: int = 1) -> int:
    r = client.post(
        "/posts",
        json={"title": "Test post for admin", "body": "Body content", "board_id": board_id},
        headers=_auth(token),
    )
    assert r.status_code == 201, f"create_post failed: {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# POST /admin/posts/{id}/lock
# ---------------------------------------------------------------------------

class TestAdminLockPost:
    def test_lock_post_200(self, client: TestClient, temp_data_path):
        """Admin puede lockear un post → 200 con locked=True."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r = client.post(f"/admin/posts/{post_id}/lock", headers=_auth(admin_token))

        assert r.status_code == 200
        data = r.json()
        assert data["post_id"] == post_id
        assert data["locked"] is True
        assert "detail" in data

    def test_lock_post_404(self, client: TestClient, temp_data_path):
        """Lockear post inexistente → 404."""
        admin_token = _login(client, "admin@example.com")

        r = client.post("/admin/posts/99999/lock", headers=_auth(admin_token))

        assert r.status_code == 404
        assert r.json()["detail"] == "Post not found"

    def test_lock_post_403_regular_user(self, client: TestClient, temp_data_path):
        """Usuario sin rol admin no puede lockear → 403."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)

        r = client.post(f"/admin/posts/{post_id}/lock", headers=_auth(alice_token))

        assert r.status_code == 403

    def test_lock_post_401_no_token(self, client: TestClient, temp_data_path):
        """Sin token → 401."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r = client.post(f"/admin/posts/{post_id}/lock")

        assert r.status_code == 401

    def test_lock_post_idempotent(self, client: TestClient, temp_data_path):
        """Lockear un post ya lockeado retorna 200 sin error."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r1 = client.post(f"/admin/posts/{post_id}/lock", headers=_auth(admin_token))
        r2 = client.post(f"/admin/posts/{post_id}/lock", headers=_auth(admin_token))

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["locked"] is True

    def test_lock_post_mod_cannot_lock(self, client: TestClient, temp_data_path):
        """Mod no puede usar este endpoint de admin → 403."""
        mod_token = _login(client, "mod@example.com")
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r = client.post(f"/admin/posts/{post_id}/lock", headers=_auth(mod_token))

        assert r.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/posts/{id}/sticky
# ---------------------------------------------------------------------------

class TestAdminStickyPost:
    def test_sticky_post_200(self, client: TestClient, temp_data_path):
        """Admin puede marcar un post como sticky → 200 con sticky=True."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r = client.post(f"/admin/posts/{post_id}/sticky", headers=_auth(admin_token))

        assert r.status_code == 200
        data = r.json()
        assert data["post_id"] == post_id
        assert data["sticky"] is True
        assert "detail" in data

    def test_sticky_post_404(self, client: TestClient, temp_data_path):
        """Sticky en post inexistente → 404."""
        admin_token = _login(client, "admin@example.com")

        r = client.post("/admin/posts/99999/sticky", headers=_auth(admin_token))

        assert r.status_code == 404
        assert r.json()["detail"] == "Post not found"

    def test_sticky_post_403_regular_user(self, client: TestClient, temp_data_path):
        """Usuario regular no puede hacer sticky → 403."""
        alice_token = _login(client, "alice@example.com")
        post_id = _create_post(client, alice_token)

        r = client.post(f"/admin/posts/{post_id}/sticky", headers=_auth(alice_token))

        assert r.status_code == 403

    def test_sticky_post_401_no_token(self, client: TestClient, temp_data_path):
        """Sin token → 401."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r = client.post(f"/admin/posts/{post_id}/sticky")

        assert r.status_code == 401

    def test_sticky_post_idempotent(self, client: TestClient, temp_data_path):
        """Marcar sticky dos veces retorna 200 sin error."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        r1 = client.post(f"/admin/posts/{post_id}/sticky", headers=_auth(admin_token))
        r2 = client.post(f"/admin/posts/{post_id}/sticky", headers=_auth(admin_token))

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["sticky"] is True

    def test_lock_and_sticky_are_independent(self, client: TestClient, temp_data_path):
        """Un post puede estar locked Y sticky a la vez."""
        admin_token = _login(client, "admin@example.com")
        post_id = _create_post(client, admin_token)

        client.post(f"/admin/posts/{post_id}/lock", headers=_auth(admin_token))
        r = client.post(f"/admin/posts/{post_id}/sticky", headers=_auth(admin_token))

        assert r.status_code == 200
        data = r.json()
        assert data["locked"] is True
        assert data["sticky"] is True


# ---------------------------------------------------------------------------
# POST /admin/users/{id}/shadowban
# ---------------------------------------------------------------------------

class TestAdminShadowban:
    def test_shadowban_200(self, client: TestClient, temp_data_path):
        """Admin puede shadowbanear a otro usuario → 200."""
        admin_token = _login(client, "admin@example.com")
        alice_id = 3  # seed: alice tiene id=3

        r = client.post(f"/admin/users/{alice_id}/shadowban", headers=_auth(admin_token))

        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == alice_id
        assert data["shadowbanned"] is True
        assert data["username"] == "alice"
        assert "detail" in data

    def test_shadowban_404_user_not_found(self, client: TestClient, temp_data_path):
        """Shadowban en usuario inexistente → 404."""
        admin_token = _login(client, "admin@example.com")

        r = client.post("/admin/users/99999/shadowban", headers=_auth(admin_token))

        assert r.status_code == 404
        assert r.json()["detail"] == "User not found"

    def test_shadowban_400_cannot_shadowban_self(self, client: TestClient, temp_data_path):
        """Admin no puede shadowbanearse a sí mismo → 400."""
        admin_token = _login(client, "admin@example.com")
        admin_id = 1  # seed: admin tiene id=1

        r = client.post(f"/admin/users/{admin_id}/shadowban", headers=_auth(admin_token))

        assert r.status_code == 400
        assert r.json()["detail"] == "Cannot shadowban yourself"

    def test_shadowban_403_regular_user(self, client: TestClient, temp_data_path):
        """Usuario regular no puede shadowbanear → 403."""
        alice_token = _login(client, "alice@example.com")
        mod_id = 2  # seed: mod tiene id=2

        r = client.post(f"/admin/users/{mod_id}/shadowban", headers=_auth(alice_token))

        assert r.status_code == 403

    def test_shadowban_401_no_token(self, client: TestClient, temp_data_path):
        """Sin token → 401."""
        r = client.post("/admin/users/3/shadowban")

        assert r.status_code == 401

    def test_shadowban_idempotent(self, client: TestClient, temp_data_path):
        """Shadowbanear dos veces retorna 200 sin error."""
        admin_token = _login(client, "admin@example.com")
        alice_id = 3

        r1 = client.post(f"/admin/users/{alice_id}/shadowban", headers=_auth(admin_token))
        r2 = client.post(f"/admin/users/{alice_id}/shadowban", headers=_auth(admin_token))

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["shadowbanned"] is True

    def test_shadowban_mod_cannot_use_admin_endpoint(self, client: TestClient, temp_data_path):
        """Mod no puede usar este endpoint de admin → 403."""
        mod_token = _login(client, "mod@example.com")
        alice_id = 3

        r = client.post(f"/admin/users/{alice_id}/shadowban", headers=_auth(mod_token))

        assert r.status_code == 403
