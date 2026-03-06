# tests/test_schemas.py
"""Tests de validación de schemas Pydantic."""
import pytest
from pydantic import ValidationError

from app.schemas import UserCreate, PostCreate, CommentCreate


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


def test_post_create_body_at_max_length_ok():
    """PostCreate con body de exactamente 40000 chars → válido."""
    post = PostCreate(title="Title", body="x" * 40000, board_id=1)
    assert len(post.body) == 40000


def test_post_create_body_exceeds_max_length_fails():
    """PostCreate con body de 40001 chars → ValidationError."""
    with pytest.raises(ValidationError):
        PostCreate(title="Title", body="x" * 40001, board_id=1)


def test_post_create_tags_at_max_length_ok():
    """PostCreate con 10 tags → válido."""
    tags = [f"tag{i}" for i in range(10)]
    post = PostCreate(title="Title", body="Body", board_id=1, tags=tags)
    assert len(post.tags) == 10


def test_post_create_tags_exceeds_max_length_fails():
    """PostCreate con 11 tags → ValidationError."""
    tags = [f"tag{i}" for i in range(11)]
    with pytest.raises(ValidationError):
        PostCreate(title="Title", body="Body", board_id=1, tags=tags)
