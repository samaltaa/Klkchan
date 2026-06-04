# tests/test_schemas.py
"""Tests de validación de schemas Pydantic."""
import pytest
from pydantic import ValidationError

from app_v1.schemas import UserCreate, PostCreate, CommentCreate, ChangePasswordRequest, ResetPasswordRequest


def test_user_create_valid():
    """UserCreate con datos válidos construye correctamente."""
    user = UserCreate(
        username="testuser",
        email="test@example.com",
        password="Testpass1",
    )
    assert user.username == "testuser"
    assert str(user.email) == "test@example.com"


def test_user_create_invalid_email_fails():
    """UserCreate con email inválido lanza ValidationError."""
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="not-an-email", password="Testpass1")


def test_user_create_short_username_fails():
    """Username menor a 3 caracteres lanza ValidationError."""
    with pytest.raises(ValidationError):
        UserCreate(username="ab", email="test@test.com", password="Testpass1")


def test_user_create_short_password_fails():
    """Password menor a 8 caracteres lanza ValidationError."""
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="test@test.com", password="Ab1")


def test_user_create_no_uppercase_fails():
    """Password sin mayúscula lanza ValidationError."""
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="test@test.com", password="alllower1")


def test_post_create_valid():
    """PostCreate con datos válidos construye correctamente."""
    post = PostCreate(title="Test Post", body="Test content", board_id=1)
    assert post.title == "Test Post"
    assert post.body == "Test content"
    assert post.board_id == 1


def test_comment_create_valid():
    """CommentCreate con datos válidos construye correctamente."""
    comment = CommentCreate(body="Test comment", post_id=1)
    assert comment.body == "Test comment"
    assert comment.post_id == 1


# ---------------------------------------------------------------------------
# Límite de 72 bytes bcrypt — UserCreate
# ---------------------------------------------------------------------------

def test_user_create_password_at_72_bytes_passes():
    """UserCreate: password de exactamente 72 bytes ASCII pasa la validación."""
    # 64 'A' + 8 chars mixtos = 72 bytes ASCII; tiene mayúscula y dígito
    password = "A" * 64 + "bcdefg1B"
    user = UserCreate(username="testuser", email="test@example.com", password=password)
    assert len(user.password.encode("utf-8")) == 72


def test_user_create_password_73_bytes_fails():
    """UserCreate: password de 73 bytes ASCII lanza ValidationError."""
    password = "A" * 65 + "bcdefg1B"  # 73 bytes
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="test@example.com", password=password)


def test_user_create_password_multibyte_unicode_fails():
    """UserCreate: password con emoji que supera 72 bytes lanza ValidationError."""
    # "A1" = 2 bytes; 18 emojis × 4 bytes = 72 bytes; total = 74 bytes > 72
    password = "A1" + "🔑" * 18
    with pytest.raises(ValidationError):
        UserCreate(username="testuser", email="test@example.com", password=password)


# ---------------------------------------------------------------------------
# Límite de 72 bytes bcrypt — ChangePasswordRequest
# ---------------------------------------------------------------------------

def test_change_password_new_password_at_72_bytes_passes():
    """ChangePasswordRequest: new_password de 72 bytes pasa la validación."""
    password = "A" * 64 + "bcdefg1B"  # 72 bytes
    req = ChangePasswordRequest(old_password="OldPass1", new_password=password)
    assert len(req.new_password.encode("utf-8")) == 72


def test_change_password_new_password_73_bytes_fails():
    """ChangePasswordRequest: new_password de 73 bytes lanza ValidationError."""
    password = "A" * 65 + "bcdefg1B"  # 73 bytes
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="OldPass1", new_password=password)


def test_change_password_new_password_multibyte_unicode_fails():
    """ChangePasswordRequest: new_password con emoji > 72 bytes lanza ValidationError."""
    # "Pass1234" = 8 bytes; 17 emojis × 4 bytes = 68 bytes; total = 76 bytes > 72
    password = "Pass1234" + "🔑" * 17
    with pytest.raises(ValidationError):
        ChangePasswordRequest(old_password="OldPass1", new_password=password)


# ---------------------------------------------------------------------------
# Límite de 72 bytes bcrypt — ResetPasswordRequest
# ---------------------------------------------------------------------------

def test_reset_password_new_password_at_72_bytes_passes():
    """ResetPasswordRequest: new_password de 72 bytes pasa la validación."""
    # min_length=12 para reset; 64 'A' + 8 chars = 72 bytes ≥ 12 chars
    password = "A" * 64 + "bcdefg1B"  # 72 bytes
    req = ResetPasswordRequest(token="a" * 16, new_password=password)
    assert len(req.new_password.encode("utf-8")) == 72


def test_reset_password_new_password_73_bytes_fails():
    """ResetPasswordRequest: new_password de 73 bytes lanza ValidationError."""
    password = "A" * 65 + "bcdefg1B"  # 73 bytes
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="a" * 16, new_password=password)


def test_reset_password_new_password_multibyte_unicode_fails():
    """ResetPasswordRequest: new_password con emoji > 72 bytes lanza ValidationError."""
    # "Password123!" = 12 bytes; 16 emojis × 4 bytes = 64 bytes; total = 76 bytes > 72
    password = "Password123!" + "🔑" * 16
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="a" * 16, new_password=password)
