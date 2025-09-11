# app/services.py
from app.schemas.schemas import User, UserCreate, UserUpdate, Post, PostCreate, PostUpdate
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from app.utils.helpers import normalize_email  # 👈 normalización de correo

# ---------- Rutas y IO robusto ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "data.json"

# Estructura base para inicializar o recuperar en caso de corrupción de JSON
EMPTY_STRUCTURE = {
    "users": [],
    "posts": [],
    "boards": [],
    "comments": [],
    "replies": [],
    "moderation": {
    "reports": [],   # reportes abiertos por usuarios
    "actions": []    # log de acciones aplicadas por moderadores
}
}

def _ensure_data_file():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(
            json.dumps(EMPTY_STRUCTURE, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

def load_data():
    """
    Carga el JSON. Si está vacío o corrupto, resetea a estructura base y continúa.
    """
    _ensure_data_file()
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Recuperación: reescribir con estructura base
        DATA_PATH.write_text(
            json.dumps(EMPTY_STRUCTURE, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        # Devolver una copia para evitar mutaciones compartidas
        return json.loads(json.dumps(EMPTY_STRUCTURE))

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
    Valida campos obligatorios: username, email, password.
    """
    # ✅ Validación mínima (hará verde el test que hoy marcaste xfail)
    for key in ("username", "email", "password"):
        if not user.get(key):
            raise ValueError(f"Missing field: {key}")

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
    post["created_at"] = datetime.now(timezone.utc).isoformat()
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


# ---------- MODERATION SERVICES ----------

from typing import Optional  # ya lo tienes arriba

def _ensure_moderation_root(data: dict) -> None:
    data.setdefault("moderation", {})
    data["moderation"].setdefault("reports", [])
    data["moderation"].setdefault("actions", [])


def _next_id(seq, key="id") -> int:
    return max([x.get(key, 0) for x in seq], default=0) + 1


def _get_entity(data: dict, target_type: str, target_id: int) -> Optional[dict]:
    """
    Devuelve el dict del recurso según tipo e id.
    target_type: 'user' | 'post' | 'comment'
    """
    tt = str(target_type).lower()
    if tt == "user":
        return next((u for u in data["users"] if u.get("id") == target_id), None)
    if tt == "post":
        return next((p for p in data["posts"] if p.get("id") == target_id), None)
    if tt == "comment":
        return next((c for c in data["comments"] if c.get("id") == target_id), None)
    return None


def moderation_report_create(
    reporter_id: int,
    target_type: str,
    target_id: int,
    reason: str = ""
) -> dict:
    """
    Crea un reporte con estado 'pending'. Si el objetivo no existe,
    marca 'invalid_target=True' para que el mod lo cierre.
    """
    data = load_data()
    _ensure_moderation_root(data)

    report = {
        "id": _next_id(data["moderation"]["reports"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reporter_id": reporter_id,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason or "",
        "status": "pending",  # pending | closed
        "invalid_target": _get_entity(data, target_type, target_id) is None,
    }
    data["moderation"]["reports"].append(report)
    save_data(data)
    return report


def moderation_queue_list(status: Optional[str] = "pending") -> list[dict]:
    """
    Lista la cola de moderación (por defecto solo 'pending').
    """
    data = load_data()
    _ensure_moderation_root(data)
    reports = data["moderation"]["reports"]
    if status:
        return [r for r in reports if r.get("status") == status]
    return reports


def moderation_action_apply(
    moderator_id: int,
    target_type: str,
    target_id: int,
    action: str,
    reason: str = "",
    report_id: Optional[int] = None,
) -> dict:
    """
    Acciones soportadas:
      - remove: marca removed=True (si es post, también locked=True)
      - approve: cierra el reporte (no toca la entidad)
      - lock: post.locked=True
      - sticky: post.sticky=True
      - ban_user: user.banned=True
      - shadowban: user.shadowbanned=True
    Devuelve {'applied': True} o {'applied': False, 'error': '...'}
    """
    act = str(action).lower()
    data = load_data()
    _ensure_moderation_root(data)

    entity = _get_entity(data, target_type, target_id)

    # Validaciones base
    if act not in {"remove", "approve", "lock", "sticky", "ban_user", "shadowban"}:
        result = {"applied": False, "error": "unknown_action"}
    elif act != "approve" and entity is None:
        # Acciones que mutan entidad requieren que exista
        result = {"applied": False, "error": "target_not_found"}
    else:
        # Ejecutar
        if act == "remove":
            entity["removed"] = True
            if target_type == "post":
                entity["locked"] = True

        elif act == "approve":
            pass  # solo cerrar reporte si corresponde

        elif act == "lock":
            if target_type != "post":
                result = {"applied": False, "error": "lock_only_for_posts"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["locked"] = True

        elif act == "sticky":
            if target_type != "post":
                result = {"applied": False, "error": "sticky_only_for_posts"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["sticky"] = True

        elif act == "ban_user":
            if target_type != "user":
                result = {"applied": False, "error": "ban_only_for_users"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["banned"] = True

        elif act == "shadowban":
            if target_type != "user":
                result = {"applied": False, "error": "shadowban_only_for_users"}
                _log_moderation_action(data, moderator_id, target_type, target_id, act, reason, False, result["error"], report_id)
                save_data(data)
                return result
            entity["shadowbanned"] = True

        # aplicado OK
        result = {"applied": True}

        # Si vino report_id, cerramos el reporte
        if report_id is not None:
            for r in data["moderation"]["reports"]:
                if r.get("id") == report_id:
                    r["status"] = "closed"
                    r["closed_at"] = datetime.now(timezone.utc).isoformat()
                    r["closed_by"] = moderator_id
                    r["resolution"] = act
                    break

    # Log persistente del intento (éxito o error)
    _log_moderation_action(
        data,
        moderator_id,
        target_type,
        target_id,
        act,
        reason,
        result.get("applied", False),
        result.get("error"),
        report_id,
    )
    save_data(data)
    return result


def _log_moderation_action(
    data: dict,
    moderator_id: int,
    target_type: str,
    target_id: int,
    action: str,
    reason: str,
    applied: bool,
    error: Optional[str],
    report_id: Optional[int],
) -> None:
    entry = {
        "id": _next_id(data["moderation"]["actions"]),
        "ts": datetime.now(timezone.utc).isoformat(),
        "moderator_id": moderator_id,
        "target_type": target_type,
        "target_id": target_id,
        "action": action,
        "reason": reason or "",
        "applied": applied,
        "error": error,
        "report_id": report_id,
    }
    data["moderation"]["actions"].append(entry)

