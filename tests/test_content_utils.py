# tests/test_content_utils.py
"""Tests de utilidades de contenido (enforce_clean_text)."""
import pytest
from fastapi import HTTPException

from app_v1.utils.content import enforce_clean_text


def test_enforce_clean_text_with_clean_content():
    """Contenido limpio no lanza excepción."""
    enforce_clean_text("Hola mundo, ¿cómo estás?")
    enforce_clean_text("Another clean string here")


def test_enforce_clean_text_with_banned_word_raises():
    """Texto con palabra prohibida lanza HTTPException 400."""
    with pytest.raises(HTTPException) as exc_info:
        enforce_clean_text("Este bastardo texto está prohibido")
    assert exc_info.value.status_code == 400
    assert "banned" in exc_info.value.detail.lower()


def test_enforce_clean_text_with_none():
    """None se ignora sin lanzar excepción."""
    enforce_clean_text(None)
    enforce_clean_text("Clean", None, "Also clean")


def test_enforce_clean_text_multiple_texts():
    """Valida múltiples textos; falla si alguno tiene banned word."""
    # Todos limpios
    enforce_clean_text("Clean title", "Clean body", "Clean description")

    # Uno con banned word
    with pytest.raises(HTTPException):
        enforce_clean_text("Clean title", "Este bastardo cuerpo", "Clean desc")


def test_enforce_clean_text_case_insensitive():
    """La detección es case insensitive."""
    with pytest.raises(HTTPException):
        enforce_clean_text("BASTARDO en mayúsculas")

    with pytest.raises(HTTPException):
        enforce_clean_text("Bastardo en mixed case")


def test_enforce_clean_text_empty_string():
    """Strings vacíos o solo espacios no lanzan excepción."""
    enforce_clean_text("")
    enforce_clean_text("   ")
