import re
import unicodedata
import uuid
from typing import Any

# 🔹 Normaliza un string (ej: username)
def normalize_text(text: str) -> str:
    """
    Convierte el texto a minúsculas, sin tildes ni caracteres raros.
    Ejemplo: "José Pérez" -> "jose perez"
    """
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", text)  # quita espacios múltiples


# 🔹 Genera un slug único para posts/títulos
def generate_slug(title: str) -> str:
    """
    Crea un slug URL-friendly a partir de un título.
    Ejemplo: "Hola Mundo!!!" -> "hola-mundo-abc123"
    """
    title = normalize_text(title)
    slug = re.sub(r"[^a-z0-9]+", "-", title).strip("-")
    unique_id = uuid.uuid4().hex[:6]  # sufijo único corto
    return f"{slug}-{unique_id}"


# 🔹 Limpieza básica de HTML (contra XSS)
def sanitize_html(text: str) -> str:
    """
    Elimina etiquetas HTML peligrosas.
    Útil si dejas que los usuarios manden texto con HTML.
    """
    clean = re.sub(r"<.*?>", "", text)
    return clean.strip()


# 🔹 Paginación simple para listas
def paginate_list(items: list[Any], page: int = 1, limit: int = 10) -> dict:
    """
    Aplica paginación a una lista en memoria.
    Retorna un dict con items paginados y metadata.
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


# 🔹 Normaliza emails a lowercase (evita duplicados por mayúsculas o espacios)
def normalize_email(email: str) -> str:
    """
    Convierte un email a minúsculas y quita espacios.
    Ejemplo: "  MelVin@KLKCHAN.Dev  " -> "melvin@klkchan.dev"
    """
    return email.strip().lower()
