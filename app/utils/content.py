"""
content.py — Validación y limpieza de contenido — KLKCHAN.

Centraliza la lógica de sanitización de texto para posts, comments,
boards y usuarios. Filtra palabras prohibidas usando los diccionarios
LDNOOBW (List of Dirty, Naughty, Obscene, and Otherwise Bad Words)
en español e inglés con normalización de leet-speak.

Uso típico en un endpoint:
    from app.utils.content import enforce_clean_text

    enforce_clean_text(payload.title, payload.body)  # lanza 400 si hay banned words
"""
from typing import Optional

from fastapi import HTTPException, status

from app.utils.banned_words import has_banned_words


def enforce_clean_text(*texts: Optional[str], lang_hint: str = "es") -> None:
    """
    Valida que ninguno de los textos contenga palabras prohibidas.

    Args:
        *texts: Textos a validar (los None se ignoran).
        lang_hint: Idioma para el filtro ('es', 'en', o ambos).

    Raises:
        HTTPException 400: Si algún texto contiene contenido prohibido.
    """
    for text in texts:
        if text and has_banned_words(text, lang_hint=lang_hint):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text contains banned words.",
            )
