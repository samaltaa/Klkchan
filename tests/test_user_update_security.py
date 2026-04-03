# tests/test_user_update_security.py
"""
Sprint 2.9: Verificar que PUT /users/{id} no permite cambiar contraseña.

El campo password fue eliminado de UserUpdate. Pydantic v2 ignora
campos desconocidos, por lo que enviar password en el body no produce
error 422 — simplemente se descarta. Si password es el único campo
enviado, el endpoint retorna 400 (no fields to update).
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


_PASSWORD = "Aa123456!"


def _register(client, username: str, email: str) -> int:
    r = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": _PASSWORD},
    )
    assert r.status_code == 201, f"register failed: {r.text}"
    return r.json()["id"]


def _login(client, email: str, password: str = _PASSWORD) -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.text}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestPasswordNotUpdatableViaPut:
    """
    Verifica que PUT /users/{id} no acepta ni procesa el campo password.
    """

    def test_password_field_is_ignored_when_sent_alone(self, client, temp_data_path):
        """
        Enviar solo password en el body → 400 (no fields to update).

        UserUpdate no tiene campo password. Pydantic lo ignora.
        El dict de updates queda vacío → el endpoint lanza 400.
        """
        user_id = _register(client, "alice_pw1", "alice_pw1@test.com")
        token = _login(client, "alice_pw1@test.com")

        r = client.put(
            f"/users/{user_id}",
            json={"password": "NewHackedPass1!"},
            headers=_auth(token),
        )
        assert r.status_code == 400
        assert "No fields to update" in r.json()["detail"]

    def test_password_not_changed_when_sent_with_other_fields(self, client, temp_data_path):
        """
        Enviar password junto a otro campo → 200, password sin cambio.

        El campo bio se actualiza correctamente, pero password
        es ignorado silenciosamente por Pydantic.
        """
        user_id = _register(client, "alice_pw2", "alice_pw2@test.com")
        token = _login(client, "alice_pw2@test.com")

        r = client.put(
            f"/users/{user_id}",
            json={"bio": "nueva bio", "password": "HackedNewPass1!"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["bio"] == "nueva bio"

        # La contraseña original sigue siendo válida
        r = client.post(
            "/auth/login",
            data={"username": "alice_pw2@test.com", "password": _PASSWORD},
        )
        assert r.status_code == 200, "la contraseña original debe seguir funcionando"

        # La contraseña "nueva" (que fue ignorada) no debe funcionar
        r = client.post(
            "/auth/login",
            data={"username": "alice_pw2@test.com", "password": "HackedNewPass1!"},
        )
        assert r.status_code == 401, "la contraseña no debe haberse cambiado"

    def test_original_password_still_valid_after_put_with_password_field(self, client, temp_data_path):
        """
        Tras un PUT con password enviado, el login con la contraseña
        original sigue funcionando correctamente.
        """
        user_id = _register(client, "alice_pw3", "alice_pw3@test.com")
        token = _login(client, "alice_pw3@test.com")

        # Intentar cambiar la contraseña via PUT
        client.put(
            f"/users/{user_id}",
            json={"password": "TotallyNewPass1!", "display_name": "Alice"},
            headers=_auth(token),
        )

        # Login con contraseña original debe funcionar
        r = client.post(
            "/auth/login",
            data={"username": "alice_pw3@test.com", "password": _PASSWORD},
        )
        assert r.status_code == 200

    def test_put_without_password_still_works(self, client, temp_data_path):
        """
        PUT /users/{id} sin campo password sigue funcionando normalmente.

        Verifica que el fix no rompió la funcionalidad de actualización
        de campos legítimos.
        """
        user_id = _register(client, "alice_pw4", "alice_pw4@test.com")
        token = _login(client, "alice_pw4@test.com")

        r = client.put(
            f"/users/{user_id}",
            json={"bio": "mi bio actualizada", "display_name": "Alice Pw4"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["bio"] == "mi bio actualizada"
        assert body["display_name"] == "Alice Pw4"

    def test_change_password_via_correct_endpoint_still_works(self, client, temp_data_path):
        """
        PATCH /auth/change-password sigue funcionando con old_password correcto.

        Verifica que el fix no afectó el flujo legítimo de cambio de contraseña.
        """
        _register(client, "alice_pw5", "alice_pw5@test.com")
        token = _login(client, "alice_pw5@test.com")

        new_password = "NuevaClave1!"
        r = client.patch(
            "/auth/change-password",
            json={"old_password": _PASSWORD, "new_password": new_password},
            headers=_auth(token),
        )
        assert r.status_code == 204

        # Login con contraseña nueva debe funcionar
        r = client.post(
            "/auth/login",
            data={"username": "alice_pw5@test.com", "password": new_password},
        )
        assert r.status_code == 200
