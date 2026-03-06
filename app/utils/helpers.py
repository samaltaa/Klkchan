"""
helpers.py — Utilidades generales — KLKCHAN.

Funciones de propósito general usadas en múltiples capas:
normalización de texto y email, generación de slugs,
sanitización HTML y paginación offset-based.

Nota: paginate_list() implementa paginación page/limit (offset-based).
Los endpoints usan paginación cursor-based; paginate_list() queda
como utilidad interna sin uso en producción actualmente.
"""
import re
import unicodedata
import uuid
from typing import Any


def normalize_text(text: str) -> str:
    """
    Convierte el texto a minúsculas, elimina tildes y caracteres especiales.

    Aplica NFD decomposition para separar los diacríticos y luego
    los descarta al codificar a ASCII. Colapsa espacios múltiples.

    Args:
        text: Texto a normalizar.

    Returns:
        Texto en minúsculas, sin tildes, sin caracteres non-ASCII,
        con espacios simples.

    Ejemplo:
        "José Pérez" -> "jose perez"
    """
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", text)


def generate_slug(title: str) -> str:
    """
    Crea un slug URL-friendly único a partir de un título.

    Normaliza el título (minúsculas, sin tildes), reemplaza caracteres
    no alfanuméricos por guiones y añade un sufijo de 6 hex chars para
    garantizar unicidad incluso con títulos idénticos.

    Args:
        title: Título original del post o board.

    Returns:
        Slug en formato "palabras-del-titulo-xxxxxx".

    Ejemplo:
        "Hola Mundo!!!" -> "hola-mundo-abc123"
    """
    title = normalize_text(title)
    slug = re.sub(r"[^a-z0-9]+", "-", title).strip("-")
    unique_id = uuid.uuid4().hex[:6]
    return f"{slug}-{unique_id}"


_DANGEROUS_TAGS = re.compile(
    r"<(script|style|iframe|object|embed|form|noscript)[^>]*>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)


def sanitize_html(text: str) -> str:
    """
    Elimina etiquetas HTML del texto para prevenir XSS.

    Para etiquetas peligrosas (script, style, iframe, object, embed,
    form, noscript) elimina tanto el tag como su contenido interior.
    Para el resto de etiquetas (b, i, p, etc.) solo elimina el tag y
    conserva el texto interior.

    Args:
        text: Texto potencialmente con HTML.

    Returns:
        Texto sin etiquetas HTML ni contenido peligroso, con whitespace
        recortado.

    TODO: Aplicar en POST /posts y POST /comments antes de persistir
          el body de los posts y comentarios (pendiente Sprint 3 /
          migración a Supabase). Actualmente no se invoca desde
          ningún endpoint.
    """
    text = _DANGEROUS_TAGS.sub("", text)
    clean = re.sub(r"<[^>]*>", "", text)
    return clean.strip()


def paginate_list(items: list[Any], page: int = 1, limit: int = 10) -> dict:
    """
    Aplica paginación offset-based a una lista en memoria.

    Nota: Los endpoints de la API usan paginación cursor-based
    (limit + next_cursor). Esta función es una utilidad interna
    no usada actualmente en ningún endpoint de producción.

    Args:
        items: Lista completa de elementos a paginar.
        page: Número de página (1-indexed, default 1).
        limit: Elementos por página (default 10).

    Returns:
        Dict con page, limit, total_items, total_pages y data (slice).
    """
    start = (page - 1) * limit
    end = start + limit
    data = items[start:end]
    return {
        "page": page,
        "limit": limit,
        "total_items": len(items),
        "total_pages": (len(items) + limit - 1) // limit,
        "data": data,
    }


def normalize_email(email: str) -> str:
    """
    Convierte un email a minúsculas y elimina espacios externos.

    Siempre llamar antes de comparar o almacenar emails para
    evitar duplicados por variaciones de mayúsculas o espacios.

    Args:
        email: Email crudo (posiblemente con mayúsculas o espacios).

    Returns:
        Email normalizado en minúsculas sin espacios externos.

    Ejemplo:
        "  MelVin@KLKCHAN.Dev  " -> "melvin@klkchan.dev"
    """
    return email.strip().lower()
