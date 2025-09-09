# app/services.py
from app.schemas import User, UserCreate, UserUpdate, Post, PostCreate, PostUpdate
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.utils.helpers import normalize_email  # 👈 normalización de correo

# ---------- Rutas y IO robusto ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "data.json"

def _ensure_data_file():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(
            json.dumps(
                {"users": [], "posts": [], "boards": [], "comments": [], "replies": []},
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
        )

def load_data():
    _ensure_data_file()
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))

def save_data(data):
    _ensure_data_file()
    # .tmp en el MISMO directorio (compatible con Windows)
    tmp = DATA_PATH.with_name(DATA_PATH.stem + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    tmp.replace(DATA_PATH)

# ---------- USERS SERVICES ----------
def get_users():
    data = load_data()
    return data["users"]

def get_user(user_id: int):
    data = load_data()
    for u in data["users"]:
        if u["id"] == user_id:
            return u
    return None

# Alias explícito (útil para imports desde deps/auth)
get_user_by_id = get_user

def get_user_by_email(email: str) -> Optional[dict]:
    """Búsqueda insensible a mayúsculas/espacios."""
    data = load_data()
    target = normalize_email(email)
    for u in data["users"]:
        if normalize_email(u.get("email", "")) == target:
            return u
    return None

def get_user_by_username(username: str) -> Optional[dict]:
    data = load_data()
    for u in data["users"]:
        if u.get("username") == username:
            return u
    return None

def create_user(user: dict):
    """
    Crea usuario asumiendo que 'password' ya es un HASH.
    Normaliza 'email' y asegura 'posts'.
    """
    data = load_data()

    if "email" in user and user["email"] is not None:
        user["email"] = normalize_email(user["email"])

    # ✅ ID incremental seguro
    next_id = max([u["id"] for u in data["users"]], default=0) + 1
    user["id"] = next_id
    user.setdefault("posts", [])

    data["users"].append(user)
    save_data(data)
    return user

def update_user(user_id: int, updates: dict):
    """
    Solo permite actualizar campos de perfil públicos: username, email, etc.
    Si cambia 'email', se normaliza y se valida unicidad.
    """
    data = load_data()
    allowed = {"username", "email"}  # agrega más si los necesitas

    for u in data["users"]:
        if u["id"] == user_id:
            safe_updates = {k: v for k, v in updates.items() if v is not None and k in allowed}

            # Manejo especial de email: normaliza + unicidad
            if "email" in safe_updates:
                new_email = normalize_email(safe_updates["email"])
                if normalize_email(u.get("email", "")) != new_email:
                    for other in data["users"]:
                        if other["id"] != user_id and normalize_email(other.get("email", "")) == new_email:
                            raise ValueError("Email ya está en uso por otro usuario")
                    safe_updates["email"] = new_email

            u.update(safe_updates)
            save_data(data)
            return u
    return None

def update_user_password(user_id: int, new_hashed: str) -> bool:
    """
    Actualiza SOLO el hash de contraseña del usuario (campo 'password').
    Retorna True si encontró y guardó; False si no encontró.
    """
    data = load_data()
    for u in data["users"]:
        if u["id"] == user_id:
            u["password"] = new_hashed  # el hash ya viene desde auth
            save_data(data)
            return True
    return False

def delete_user(user_id: int):
    data = load_data()
    data["users"] = [u for u in data["users"] if u["id"] != user_id]
    # (Opcional) también podrías limpiar posts/comentarios del usuario aquí.
    save_data(data)
    return True

# ---------- POSTS SERVICES ----------
def get_posts():
    data = load_data()
    return data["posts"]

def get_post(post_id: int):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            return p
    return None

def create_post(post: dict):
    data = load_data()
    # ✅ ID incremental seguro
    next_id = max([p["id"] for p in data["posts"]], default=0) + 1
    post["id"] = next_id
    post["created_at"] = datetime.utcnow().isoformat()  # ISO-8601 UTC
    post.setdefault("votes", 0)
    post.setdefault("comments", [])

    data["posts"].append(post)

    # Vincular al usuario
    for u in data["users"]:
        if u["id"] == post["user_id"]:
            u.setdefault("posts", []).append(post["id"])
            break

    save_data(data)
    return post

def update_post(post_id: int, updates: dict):
    data = load_data()
    allowed = {"title", "body", "board_id"}  # protege campos inmutables
    for p in data["posts"]:
        if p["id"] == post_id:
            safe_updates = {k: v for k, v in updates.items() if v is not None and k in allowed}
            p.update(safe_updates)
            save_data(data)
            return p
    return None

def delete_post(post_id: int):
    data = load_data()
    data["posts"] = [p for p in data["posts"] if p["id"] != post_id]

    # Quitar referencia en el usuario
    for u in data["users"]:
        if "posts" in u and post_id in u["posts"]:
            u["posts"].remove(post_id)

    save_data(data)
    return True
