"""
Utilidades compartidas para validación de contenido.
Centraliza la lógica de banned words para evitar duplicación en routers.
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
