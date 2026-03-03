# tests/test_rate_limiting.py
"""
Tests para rate limiting global con SlowAPI.
"""
import pytest
from fastapi.testclient import TestClient

from app.utils.limiter import limiter


def test_limiter_has_default_limits():
    """El limiter debe tener default_limits configurados."""
    assert limiter._default_limits, "Limiter debe tener default_limits configurados (e.g. 60/minute)"


def test_rate_limit_returns_429(client: TestClient):
    """Al exceder el límite de 60 req/min, el servidor responde con 429."""
    # Limpiar contadores y habilitar el limiter temporalmente
    try:
        limiter._storage.reset()
    except AttributeError:
        pass  # algunos backends no requieren reset explícito

    limiter.enabled = True
    try:
        # 65 peticiones superan el límite de 60/minuto
        statuses = [client.get("/boards").status_code for _ in range(65)]
        assert 429 in statuses, (
            f"Se esperaba al menos un 429. Códigos obtenidos: {set(statuses)}"
        )
    finally:
        limiter.enabled = False
        try:
            limiter._storage.reset()
        except AttributeError:
            pass
