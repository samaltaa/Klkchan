# tests/test_security_utils.py
"""Tests de utilidades de seguridad (JWT, hashing)."""
import pytest
from jose import JWTError

from app_v1.utils.security import (
    ISSUER,
    hash_password,
    verify_password,
    validate_password_bytes,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_hash_password_creates_unique_hashes():
    """hash_password genera hashes distintos (bcrypt con salt único)."""
    h1 = hash_password("password123")
    h2 = hash_password("password123")
    assert h1 != h2


def test_verify_password_correct():
    """verify_password valida la contraseña correcta."""
    password = "MySecurePass123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """verify_password rechaza la contraseña incorrecta."""
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token_has_required_claims():
    """create_access_token incluye jti, iss, exp, sub."""
    token = create_access_token({"sub": "123", "roles": ["user"]})
    payload = decode_access_token(token)
    assert payload["sub"] == "123"
    assert "exp" in payload
    assert "jti" in payload
    assert "iss" in payload


def test_create_refresh_token_has_type():
    """create_refresh_token genera token con typ='refresh'."""
    token, jti, exp_ts = create_refresh_token(user_id=123)
    payload = decode_refresh_token(token)
    assert payload.get("typ") == "refresh"
    assert payload["sub"] == "123"
    assert payload["jti"] == jti


def test_jti_is_unique():
    """Cada access token generado tiene un JTI único."""
    t1 = create_access_token({"sub": "123"})
    t2 = create_access_token({"sub": "123"})
    p1 = decode_access_token(t1)
    p2 = decode_access_token(t2)
    assert p1["jti"] != p2["jti"]


def test_decode_invalid_token_fails():
    """decode_access_token con token inválido lanza excepción."""
    with pytest.raises(Exception):
        decode_access_token("invalid.token.here")


def test_token_contains_correct_issuer():
    """Token incluye el issuer configurado."""
    token = create_access_token({"sub": "123"})
    payload = decode_access_token(token)
    assert payload["iss"] == ISSUER


# ---------------------------------------------------------------------------
# validate_password_bytes
# ---------------------------------------------------------------------------

def test_validate_password_bytes_at_limit_passes():
    """Password de exactamente 72 bytes ASCII está dentro del límite de bcrypt."""
    ok, msg = validate_password_bytes("A" * 72)
    assert ok is True
    assert msg is None


def test_validate_password_bytes_exceeds_limit_fails():
    """Password de 73 bytes ASCII supera el límite de bcrypt."""
    ok, msg = validate_password_bytes("A" * 73)
    assert ok is False
    assert msg is not None
    assert "72 bytes" in msg


def test_validate_password_bytes_multibyte_unicode_fails():
    """Password con emoji (4 bytes UTF-8 cada uno) que supera 72 bytes falla."""
    # 🔑 = 4 bytes; 19 emojis = 76 bytes > 72
    ok, msg = validate_password_bytes("🔑" * 19)
    assert ok is False
    assert msg is not None
    assert "72 bytes" in msg


def test_validate_password_bytes_short_unicode_passes():
    """Password con unicode (ñ = 2 bytes) que no supera 72 bytes pasa."""
    ok, msg = validate_password_bytes("Contraseña1")
    assert ok is True
    assert msg is None
