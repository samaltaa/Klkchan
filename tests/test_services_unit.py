# tests/test_services_unit.py
"""Tests unitarios para el services layer (sin HTTP).
Prueba funciones individuales de services.py directamente.
El fixture temp_data_path (autouse) redirige DATA_PATH al archivo de test.
"""
import pytest
from app.services import (
    _next_id,
    load_data,
    get_user,
    get_users,
    create_user,
    update_user,
    delete_user,
)


def test_next_id_generates_sequential_id(temp_data_path):
    """_next_id retorna max(id) + 1."""
    sequence = [{"id": 1}, {"id": 2}, {"id": 5}]
    assert _next_id(sequence) == 6


def test_next_id_empty_sequence(temp_data_path):
    """_next_id con secuencia vacía retorna 1."""
    assert _next_id([]) == 1


def test_load_data_returns_dict(temp_data_path):
    """load_data retorna un dict con las claves esperadas."""
    data = load_data()
    assert isinstance(data, dict)
    for key in ("users", "posts", "boards", "comments"):
        assert key in data


def test_get_user_existing(temp_data_path):
    """get_user retorna el usuario cuando existe (id=1 está en seed)."""
    user = get_user(1)
    assert user is not None
    assert user["id"] == 1
    assert user["username"] == "admin"


def test_get_user_nonexistent(temp_data_path):
    """get_user con ID inexistente retorna None."""
    assert get_user(999999) is None


def test_get_users_returns_list(temp_data_path):
    """get_users retorna lista de usuarios (seed tiene 3)."""
    users = get_users()
    assert isinstance(users, list)
    assert len(users) == 3


def test_create_user_adds_to_data(temp_data_path):
    """create_user añade el usuario al almacenamiento."""
    initial_count = len(get_users())
    new_user = {
        "username": "serviceuser",
        "email": "svc@example.com",
        "password": "hashed",
        "roles": ["user"],
    }
    created = create_user(new_user)
    assert "id" in created
    assert created["username"] == "serviceuser"
    assert len(get_users()) == initial_count + 1
