# app/services.py
"""
services.py — Capa de repositorio de KLKCHAN.

Centraliza toda la lógica de acceso y manipulación de datos.
Los routers llaman a estas funciones directamente — nunca
acceden al archivo de datos (data.json) por su cuenta.

Estructura de datos: data.json contiene las colecciones
users, boards, posts, comments, votes y moderation.

Persistencia: escritura atómica vía archivo .tmp para evitar
corrupción parcial del JSON ante errores de I/O.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.helpers import normalize_email

# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "data.json"

EMPTY_STRUCTURE: Dict[str, Any] = {
    "users": [],
    "posts": [],
    "boards": [],
    "comments": [],
    "replies": [],
    "votes": [],
    "subscriptions": [],
    "tags": [],
    "attachments": [],
    "moderation": {
        "reports": [],
        "actions": [],
    },
    "terms_and_conditions": [],
    "terms_acceptances": [],
}


def _now_utc_iso() -> str:
    """Retorna la fecha y hora actual en UTC como string ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _normalize_timestamp(value: Optional[str]) -> str:
    """
    Normaliza un timestamp a formato ISO 8601 con zona horaria UTC.

    Acepta strings con sufijo "Z", fechas sin hora y strings ISO incompletos.
    Si el valor es None o vacío, retorna la hora actual en UTC.

    Args:
        value: String de fecha/hora a normalizar, o None.

    Returns:
        String ISO 8601 con zona horaria. Si no se puede parsear, retorna
        el valor original sin modificar.
    """
    if not value:
        return _now_utc_iso()
    if isinstance(value, str):
        candidate = value.strip()
        try:
            # Support "Z" suffix and date-only strings
            cleaned = candidate.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            try:
                dt = datetime.fromisoformat(candidate + "T00:00:00")
            except ValueError:
                return candidate
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return _now_utc_iso()


def _ensure_data_file() -> None:
    """
    Crea el archivo data.json con estructura vacía si no existe.

    También crea los directorios intermedios necesarios.
    """
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(
            json.dumps(EMPTY_STRUCTURE, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )


def load_data() -> Dict[str, Any]:
    """
    Carga y retorna el documento JSON completo desde disco.

    Autosanea el archivo si está corrompido: en caso de error de parseo
    reescribe la estructura vacía y la retorna.

    Returns:
        Diccionario con todas las colecciones: users, posts, boards,
        comments, votes, moderation, etc.
    """
    _ensure_data_file()
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        DATA_PATH.write_text(
            json.dumps(EMPTY_STRUCTURE, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        return json.loads(json.dumps(EMPTY_STRUCTURE))


def save_data(data: Dict[str, Any]) -> None:
    """
    Persiste el documento JSON completo en disco de forma atómica.

    Escribe primero en un archivo .tmp y luego lo renombra sobre el
    definitivo, garantizando que una escritura parcial no corrompa
    los datos existentes.

    Args:
        data: Diccionario completo con todas las colecciones a guardar.
    """
    _ensure_data_file()
    tmp = DATA_PATH.with_name(DATA_PATH.stem + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    tmp.replace(DATA_PATH)


# ---------------------------------------------------------------------------
# User services
# ---------------------------------------------------------------------------
def get_users() -> List[Dict[str, Any]]:
    """
    Retorna la lista completa de usuarios sin ningún filtro.

    Returns:
        Lista de dicts de usuario tal como están en data.json, incluyendo
        el campo password (hash). El router es responsable de sanitizar
        antes de exponer en la API.
    """
    data = load_data()
    return data["users"]


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca y retorna un usuario por su ID numérico.

    Args:
        user_id: ID entero del usuario a buscar.

    Returns:
        Dict del usuario si existe, None si no se encuentra.
    """
    data = load_data()
    return next((u for u in data["users"] if u.get("id") == user_id), None)


get_user_by_id = get_user


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Busca un usuario por email, normalizando ambos lados de la comparación.

    La normalización aplica lowercase y strip para evitar duplicados por
    diferencias de mayúsculas o espacios.

    Args:
        email: Dirección de correo a buscar (se normaliza antes de comparar).

    Returns:
        Dict del usuario si existe, None si no se encuentra.
    """
    data = load_data()
    target = normalize_email(email)
    return next(
        (
            u
            for u in data["users"]
            if normalize_email(u.get("email", "")) == target
        ),
        None,
    )


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Busca un usuario por username (comparación exacta, case-sensitive).

    Args:
        username: Nombre de usuario exacto a buscar.

    Returns:
        Dict del usuario si existe, None si no se encuentra.
    """
    data = load_data()
    return next((u for u in data["users"] if u.get("username") == username), None)


def create_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un nuevo usuario y lo persiste en data.json.

    Asigna automáticamente un ID único, normaliza el email y establece
    valores por defecto para posts, roles, is_active y created_at.
    El campo password debe llegar ya hasheado — esta función no hashea.

    Args:
        user: Dict con los datos del usuario. Campos obligatorios:
              username, email, password (hash bcrypt).

    Returns:
        Dict del usuario creado con todos los campos, incluyendo el ID asignado.

    Raises:
        ValueError: Si falta alguno de los campos obligatorios
                    (username, email, password).
    """
    for key in ("username", "email", "password"):
        if not user.get(key):
            raise ValueError(f"Missing field: {key}")

    data = load_data()
    user_copy = deepcopy(user)
    if user_copy.get("email"):
        user_copy["email"] = normalize_email(user_copy["email"])

    user_copy["id"] = _next_id(data["users"])
    user_copy.setdefault("posts", [])
    user_copy.setdefault("roles", ["user"])
    user_copy.setdefault("is_active", True)
    user_copy.setdefault("created_at", _now_utc_iso())

    data["users"].append(user_copy)
    save_data(data)
    return user_copy


def update_user(user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Actualiza campos de perfil de un usuario existente.

    Solo permite modificar los campos de la lista blanca: username, email,
    display_name, bio. Cualquier otra clave en updates es ignorada
    silenciosamente. Si se cambia el email, valida que no esté en uso
    por otro usuario.

    Args:
        user_id: ID del usuario a actualizar.
        updates: Dict con los campos a actualizar. Claves no permitidas
                 son ignoradas; valores None también son ignorados.

    Returns:
        Dict del usuario actualizado, o None si el usuario no existe.

    Raises:
        ValueError: Si el nuevo email ya está en uso por otro usuario.
    """
    data = load_data()
    allowed = {"username", "email", "display_name", "bio"}

    for user in data["users"]:
        if user.get("id") == user_id:
            safe_updates = {
                key: value
                for key, value in updates.items()
                if value is not None and key in allowed
            }

            if "email" in safe_updates:
                new_email = normalize_email(safe_updates["email"])
                if normalize_email(user.get("email", "")) != new_email:
                    if any(
                        normalize_email(other.get("email", "")) == new_email
                        for other in data["users"]
                        if other.get("id") != user_id
                    ):
                        raise ValueError("Email already in use")
                    safe_updates["email"] = new_email

            user.update(safe_updates)
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return user
    return None


def update_user_roles(user_id: int, roles: List[str]) -> Optional[Dict[str, Any]]:
    """
    Reemplaza la lista de roles de un usuario.

    Filtra los roles recibidos para admitir solo valores válidos
    (user, mod, admin) y siempre garantiza que "user" esté presente
    como rol base.

    Args:
        user_id: ID del usuario cuyo rol se actualiza.
        roles: Lista de roles deseados. Valores inválidos son descartados.

    Returns:
        Dict del usuario actualizado con los nuevos roles, o None si
        el usuario no existe.
    """
    data = load_data()
    safe_roles = list({r for r in roles if r in {"user", "mod", "admin"}} | {"user"})
    for user in data["users"]:
        if user.get("id") == user_id:
            user["roles"] = safe_roles
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return user
    return None


def update_user_password(user_id: int, new_hashed: str) -> bool:
    """
    Actualiza el hash de contraseña de un usuario.

    Recibe el hash ya procesado por bcrypt — no hashea por sí mismo.

    Args:
        user_id: ID del usuario.
        new_hashed: Nuevo hash de contraseña (bcrypt).

    Returns:
        True si la contraseña fue actualizada, False si el usuario
        no existe.
    """
    data = load_data()
    for user in data["users"]:
        if user.get("id") == user_id:
            user["password"] = new_hashed
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return True
    return False


def update_user_iat_cutoff(user_id: int, cutoff_ts: int) -> bool:
    """
    Establece el campo iat_cutoff para invalidar sesiones activas.

    Cualquier access token cuyo campo 'iat' sea menor o igual a cutoff_ts
    será rechazado por get_current_user() en deps.py. Se llama
    automáticamente tras un reset de contraseña exitoso.

    Args:
        user_id: ID del usuario afectado.
        cutoff_ts: Timestamp Unix (entero) a partir del cual los tokens
                   anteriores quedan invalidados.

    Returns:
        True si el campo fue actualizado, False si el usuario no existe.
    """
    data = load_data()
    for user in data["users"]:
        if user.get("id") == user_id:
            user["iat_cutoff"] = cutoff_ts
            user["updated_at"] = _now_utc_iso()
            save_data(data)
            return True
    return False


def delete_user(user_id: int) -> bool:
    """
    Elimina un usuario y todos sus datos asociados en cascada.

    Elimina en orden:
    1. El usuario de la colección users.
    2. Todos sus posts.
    3. Todos sus comentarios.
    4. Todos los votos emitidos por él y todos los votos recibidos
       en su contenido (posts y comentarios eliminados).

    Args:
        user_id: ID del usuario a eliminar.

    Returns:
        True si el usuario fue eliminado, False si no existía.
    """
    data = load_data()
    initial = len(data["users"])
    data["users"] = [u for u in data["users"] if u.get("id") != user_id]
    if len(data["users"]) != initial:
        # Collect IDs before removing
        post_ids = {p.get("id") for p in data["posts"] if p.get("user_id") == user_id}
        comment_ids = {c.get("id") for c in data["comments"] if c.get("user_id") == user_id}
        data["posts"] = [p for p in data["posts"] if p.get("user_id") != user_id]
        data["comments"] = [c for c in data["comments"] if c.get("user_id") != user_id]
        # Cascade: remove votes by the user and votes on their content
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (
                v.get("user_id") == user_id
                or (v.get("target_type") == "post" and v.get("target_id") in post_ids)
                or (v.get("target_type") == "comment" and v.get("target_id") in comment_ids)
            )
        ]
        save_data(data)
        return True
    return False


def ban_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Suspende a un usuario marcando is_banned=True sin eliminar la cuenta.

    El usuario baneado no puede iniciar sesión ni usar tokens activos,
    pero su cuenta y contenido permanecen en el sistema. Para un borrado
    completo usar delete_user().

    Args:
        user_id: ID del usuario a suspender.

    Returns:
        Dict del usuario actualizado, o None si no existe.
    """
    data = load_data()
    for user in data["users"]:
        if user.get("id") == user_id:
            user["is_banned"] = True
            save_data(data)
            return user
    return None


def calculate_user_karma(user_id: int) -> Dict[str, int]:
    """
    Calcula el karma de un usuario a partir de los votos recibidos en su contenido.

    El karma se calcula al vuelo en cada llamada leyendo todos los votos
    del archivo. No se almacena en caché ni en el perfil del usuario.

    - post_karma: suma de valores de votos (+1/-1) en posts del usuario.
    - comment_karma: suma de valores de votos en comentarios del usuario.
    - karma: post_karma + comment_karma.

    Args:
        user_id: ID del usuario cuyo karma se quiere calcular.

    Returns:
        Dict con las claves post_karma, comment_karma y karma (int).
        Retorna ceros si el usuario no tiene contenido o votos.
    """
    data = load_data()
    votes = data.get("votes", [])
    user_post_ids = {
        p["id"] for p in data.get("posts", []) if p.get("user_id") == user_id
    }
    user_comment_ids = {
        c["id"] for c in data.get("comments", []) if c.get("user_id") == user_id
    }
    post_karma = sum(
        v.get("value", 0)
        for v in votes
        if v.get("target_type") == "post" and v.get("target_id") in user_post_ids
    )
    comment_karma = sum(
        v.get("value", 0)
        for v in votes
        if v.get("target_type") == "comment" and v.get("target_id") in user_comment_ids
    )
    return {
        "post_karma": post_karma,
        "comment_karma": comment_karma,
        "karma": post_karma + comment_karma,
    }


# ---------------------------------------------------------------------------
# Board services
# ---------------------------------------------------------------------------
def list_boards() -> List[Dict[str, Any]]:
    """
    Retorna todos los boards ordenados por ID ascendente.

    Enriquece cada board con el campo post_count (cantidad de posts
    publicados en ese board) y normaliza los campos de fecha.

    Returns:
        Lista de dicts de board, cada uno con: id, name, description,
        created_at, updated_at (opcional) y post_count.
    """
    data = load_data()
    boards: List[Dict[str, Any]] = []
    posts = data.get("posts", [])
    for entry in data.get("boards", []):
        board = deepcopy(entry)
        board['created_at'] = _normalize_timestamp(board.get('created_at'))
        if board.get('updated_at'):
            board['updated_at'] = _normalize_timestamp(board.get('updated_at'))
        board.setdefault('description', '')
        board["post_count"] = sum(1 for post in posts if post.get('board_id') == board.get('id'))
        boards.append(board)
    boards.sort(key=lambda b: b.get("id", 0))
    return boards


def get_board(board_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca y retorna un board por su ID.

    Args:
        board_id: ID entero del board a buscar.

    Returns:
        Dict del board enriquecido (con post_count) si existe,
        None si no se encuentra.
    """
    return next((b for b in list_boards() if b.get("id") == board_id), None)


def create_board(board: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un nuevo board y lo persiste en data.json.

    Asigna automáticamente un ID único y establece valores por defecto
    para name, created_at y description.

    Args:
        board: Dict con los datos del board. Campo recomendado: name.

    Returns:
        Dict del board creado con todos los campos, incluyendo el ID asignado.
    """
    data = load_data()
    board_copy = deepcopy(board)
    board_copy["id"] = _next_id(data["boards"])
    board_copy.setdefault("name", "")
    board_copy.setdefault("created_at", _now_utc_iso())
    board_copy.setdefault("description", "")
    data.setdefault("boards", []).append(board_copy)
    save_data(data)
    return board_copy


def update_board(board_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Actualiza los campos name y/o description de un board.

    Solo permite modificar name y description; otras claves son ignoradas.
    Si updates no contiene campos válidos, retorna el board sin modificar.

    Args:
        board_id: ID del board a actualizar.
        updates: Dict con los campos a actualizar (name, description).

    Returns:
        Dict del board actualizado, o None si el board no existe.
    """
    data = load_data()
    allowed = {"name", "description"}
    for board in data.get("boards", []):
        if board.get("id") == board_id:
            safe_updates = {
                key: value
                for key, value in updates.items()
                if value is not None and key in allowed
            }
            if not safe_updates:
                return board
            board.update(safe_updates)
            board["updated_at"] = _now_utc_iso()
            save_data(data)
            return board
    return None


def delete_board(board_id: int) -> bool:
    """
    Elimina un board y todos sus datos asociados en cascada.

    Elimina en orden:
    1. El board de la colección boards.
    2. Todos los posts del board.
    3. Todos los comentarios de esos posts.
    4. Todos los votos sobre esos posts y comentarios.

    Args:
        board_id: ID del board a eliminar.

    Returns:
        True si el board fue eliminado, False si no existía.
    """
    data = load_data()
    before = len(data.get("boards", []))
    data["boards"] = [b for b in data.get("boards", []) if b.get("id") != board_id]
    if len(data["boards"]) != before:
        # Cascade posts and comments for this board
        board_post_ids = {p.get("id") for p in data.get("posts", []) if p.get("board_id") == board_id}
        comment_ids = {c.get("id") for c in data.get("comments", []) if c.get("post_id") in board_post_ids}
        data["posts"] = [p for p in data.get("posts", []) if p.get("board_id") != board_id]
        data["comments"] = [c for c in data.get("comments", []) if c.get("post_id") not in board_post_ids]
        # Cascade: remove votes on board posts and their comments
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (
                (v.get("target_type") == "post" and v.get("target_id") in board_post_ids)
                or (v.get("target_type") == "comment" and v.get("target_id") in comment_ids)
            )
        ]
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Comment helpers
# ---------------------------------------------------------------------------
def _build_comment(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza un comentario crudo del JSON para su uso en respuestas.

    Normaliza los campos de fecha y establece votes=0 si no existe.

    Args:
        raw: Dict de comentario tal como está almacenado en data.json.

    Returns:
        Copia del comentario con fechas normalizadas y votes garantizado.
    """
    comment = deepcopy(raw)
    comment["created_at"] = _normalize_timestamp(comment.get("created_at"))
    if comment.get("updated_at"):
        comment["updated_at"] = _normalize_timestamp(comment.get("updated_at"))
    comment.setdefault("votes", 0)
    return comment


def build_comment_tree(
    comments: List[Dict[str, Any]], max_depth: int = 6
) -> List[Dict[str, Any]]:
    """
    Convierte una lista plana de comentarios en un árbol anidado.

    Procesa los comentarios en orden ascendente de ID (los padres siempre
    tienen ID menor que sus hijos, garantizando que el padre ya esté en
    el mapa cuando se procese el hijo).

    Cada nodo del árbol recibe:
    - depth: nivel de anidación (0 = raíz).
    - replies: lista de comentarios hijo directos.

    Los comentarios cuyo depth superaría max_depth son promovidos al
    nivel raíz en lugar de ser descartados.

    Args:
        comments: Lista plana de dicts de comentario (sin replies ni depth).
        max_depth: Profundidad máxima de anidación permitida. Default: 6
                   (equivalente al límite de Reddit).

    Returns:
        Lista de comentarios raíz, cada uno con su subárbol de replies
        anidado recursivamente.
    """
    nodes: Dict[int, Dict[str, Any]] = {}
    roots: List[Dict[str, Any]] = []

    for c in sorted(comments, key=lambda x: x.get("id", 0)):
        node = {**c, "replies": [], "depth": 0}
        nodes[c["id"]] = node
        parent_id = c.get("parent_id")
        if parent_id and parent_id in nodes:
            parent_node = nodes[parent_id]
            node["depth"] = parent_node["depth"] + 1
            if node["depth"] <= max_depth:
                parent_node["replies"].append(node)
            else:
                roots.append(node)
        else:
            roots.append(node)

    return roots


def get_comments() -> List[Dict[str, Any]]:
    """
    Retorna todos los comentarios del sistema ordenados por ID ascendente.

    Los comentarios se retornan como lista plana (sin anidar). Para obtener
    el árbol jerárquico usar build_comment_tree() sobre el resultado.

    Returns:
        Lista de dicts de comentario normalizados (fechas, votes garantizado).
    """
    data = load_data()
    comments = [_build_comment(c) for c in data.get("comments", [])]
    comments.sort(key=lambda c: c.get("id", 0))
    return comments


def get_comment(comment_id: int) -> Optional[Dict[str, Any]]:
    """
    Retorna un comentario por su ID, o None si no existe.

    Args:
        comment_id: ID del comentario a buscar.

    Returns:
        Dict del comentario normalizado, o None si no existe.
    """
    data = load_data()
    raw = next((c for c in data.get("comments", []) if c.get("id") == comment_id), None)
    return _build_comment(raw) if raw else None


def get_comments_for_post(post_id: int) -> List[Dict[str, Any]]:
    """
    Retorna todos los comentarios de un post específico, como lista plana.

    Para obtener el árbol anidado, pasar el resultado a build_comment_tree().

    Args:
        post_id: ID del post cuyos comentarios se quieren obtener.

    Returns:
        Lista plana de dicts de comentario del post, ordenados por ID.
        Lista vacía si el post no tiene comentarios o no existe.
    """
    return [c for c in get_comments() if c.get("post_id") == post_id]


def create_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un nuevo comentario y lo persiste en data.json.

    Si se provee parent_id, valida que el comentario padre exista y
    pertenezca al mismo post que el comentario nuevo.

    Args:
        comment: Dict con los datos del comentario. Campos obligatorios:
                 user_id, post_id. Campo opcional: parent_id (int).

    Returns:
        Dict del comentario creado con ID asignado y fechas normalizadas.
        No incluye depth ni replies — usar build_comment_tree() para el árbol.

    Raises:
        ValueError "user_id is required": Falta el user_id.
        ValueError "post_id is required": Falta el post_id.
        ValueError "parent_not_found": El parent_id no existe.
        ValueError "parent_wrong_post": El parent_id pertenece a otro post.
    """
    if not comment.get("user_id"):
        raise ValueError("user_id is required")
    if not comment.get("post_id"):
        raise ValueError("post_id is required")

    data = load_data()

    parent_id = comment.get("parent_id")
    if parent_id is not None:
        parent = next(
            (c for c in data.get("comments", []) if c.get("id") == parent_id),
            None,
        )
        if parent is None:
            raise ValueError("parent_not_found")
        if parent.get("post_id") != comment.get("post_id"):
            raise ValueError("parent_wrong_post")

    comment_copy = deepcopy(comment)
    comment_copy["id"] = _next_id(data.get("comments", []))
    comment_copy.setdefault("votes", 0)
    comment_copy["created_at"] = _now_utc_iso()
    data.setdefault("comments", []).append(comment_copy)
    save_data(data)
    return _build_comment(comment_copy)


def delete_comment(comment_id: int) -> bool:
    """
    Elimina un comentario y sus votos asociados en cascada.

    Nota: los comentarios hijo (replies) NO son eliminados automáticamente;
    quedan huérfanos con un parent_id que ya no existe. build_comment_tree()
    los promueve a nivel raíz en ese caso.

    Args:
        comment_id: ID del comentario a eliminar.

    Returns:
        True si el comentario fue eliminado, False si no existía.
    """
    data = load_data()
    before = len(data.get("comments", []))
    data["comments"] = [c for c in data.get("comments", []) if c.get("id") != comment_id]
    if len(data["comments"]) != before:
        # Cascade: remove votes on this comment
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (v.get("target_type") == "comment" and v.get("target_id") == comment_id)
        ]
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Post services
# ---------------------------------------------------------------------------
def _group_comments_by_post(comments: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """
    Agrupa una lista plana de comentarios por post_id.

    Dentro de cada grupo, los comentarios se ordenan por ID ascendente
    para que build_comment_tree() los procese en orden correcto.

    Args:
        comments: Lista plana de dicts de comentario.

    Returns:
        Dict donde la clave es post_id y el valor es la lista de
        comentarios de ese post, ordenados por ID.
    """
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for comment in comments:
        grouped.setdefault(comment.get("post_id"), []).append(comment)
    for bucket in grouped.values():
        bucket.sort(key=lambda c: c.get("id", 0))
    return grouped


def _hot_score(post: Dict[str, Any]) -> float:
    """
    Calcula el hot score de un post con el algoritmo inspirado en Reddit.

    Fórmula: votos / (horas_desde_creación + 2)^1.5

    El sumando +2 en el denominador evita división por cero y suaviza el
    efecto del tiempo para posts muy recientes. Posts con más votos puntúan
    más alto, pero el score decae con el tiempo.

    Args:
        post: Dict del post con campos 'votes' y 'created_at'.

    Returns:
        Float con el hot score. Mayor = más relevante. Puede ser negativo
        si el post tiene más downvotes que upvotes.
    """
    votes = post.get("votes", 0)
    raw = post.get("created_at", "")
    try:
        created_dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        created_dt = datetime.now(timezone.utc)
    hours = max((datetime.now(timezone.utc) - created_dt).total_seconds() / 3600, 0)
    return votes / ((hours + 2) ** 1.5)


def get_posts_sorted(sort: str = "new") -> List[Dict[str, Any]]:
    """
    Retorna todos los posts ordenados según el criterio indicado.

    Criterios disponibles:
    - "new" (default): orden descendente por created_at (más recientes primero).
    - "top": orden descendente por votes (más votados primero).
    - "hot": orden descendente por hot score (ver _hot_score).

    Cualquier valor distinto de "top" y "hot" produce el orden "new".

    Args:
        sort: Criterio de ordenamiento. Default: "new".

    Returns:
        Lista completa de posts enriquecidos (con comments, comment_count,
        votes, etc.) ordenados según el criterio elegido.
    """
    posts = get_posts()
    if sort == "top":
        return sorted(posts, key=lambda p: p.get("votes", 0), reverse=True)
    if sort == "hot":
        return sorted(posts, key=_hot_score, reverse=True)
    # "new": newest first by created_at
    return sorted(posts, key=lambda p: p.get("created_at", ""), reverse=True)


def get_posts() -> List[Dict[str, Any]]:
    """
    Retorna todos los posts del sistema con sus comentarios anidados.

    Enriquece cada post con:
    - Fechas normalizadas (created_at, updated_at).
    - votes, score, tags, attachments con valores por defecto.
    - comment_count: número de comentarios del post.
    - comments: árbol anidado de comentarios (via build_comment_tree).

    Los posts se retornan ordenados por ID ascendente. Para ordenar por
    otros criterios, usar get_posts_sorted().

    Returns:
        Lista de dicts de post enriquecidos, ordenados por ID ascendente.
    """
    data = load_data()
    comments = [_build_comment(c) for c in data.get("comments", [])]
    comments_by_post = _group_comments_by_post(comments)

    posts: List[Dict[str, Any]] = []
    for entry in data.get("posts", []):
        post = deepcopy(entry)
        post["created_at"] = _normalize_timestamp(post.get("created_at"))
        if post.get("updated_at"):
            post["updated_at"] = _normalize_timestamp(post.get("updated_at"))
        post.setdefault("votes", 0)
        post.setdefault("score", post.get("votes", 0))
        post.setdefault("tags", [])
        post.setdefault("attachments", [])
        post_comments = comments_by_post.get(post.get("id"), [])
        post["comment_count"] = len(post_comments)
        post["comments"] = build_comment_tree(post_comments)
        posts.append(post)

    posts.sort(key=lambda p: p.get("id", 0))
    return posts


def get_post(post_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca y retorna un post por su ID, con comentarios anidados incluidos.

    Args:
        post_id: ID entero del post a buscar.

    Returns:
        Dict del post enriquecido (con comments, comment_count, votes, etc.)
        si existe, None si no se encuentra.
    """
    return next((post for post in get_posts() if post.get("id") == post_id), None)


def create_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un nuevo post y lo persiste en data.json.

    Asigna automáticamente un ID único, establece created_at y valores
    por defecto (votes, score, tags, attachments). También añade el ID
    del post a la lista posts del usuario autor.

    El campo comments y comment_count son calculados al vuelo — no se
    almacenan directamente en el JSON.

    Args:
        post: Dict con los datos del post. Campos obligatorios:
              user_id (int), board_id (int). Campos opcionales:
              title, body, tags, attachments.

    Returns:
        Dict del post creado con todos los campos enriquecidos,
        incluyendo comments=[] y comment_count=0.

    Raises:
        ValueError "user_id is required": Falta el campo user_id.
        ValueError "board_id is required": Falta el campo board_id.
    """
    if not post.get("user_id"):
        raise ValueError("user_id is required")
    if not post.get("board_id"):
        raise ValueError("board_id is required")

    data = load_data()
    post_copy = deepcopy(post)
    post_copy["id"] = _next_id(data.get("posts", []))
    post_copy["created_at"] = _now_utc_iso()
    post_copy.setdefault("votes", 0)
    post_copy.setdefault("score", 0)
    post_copy.setdefault("attachments", [])
    post_copy.setdefault("tags", [])
    post_copy.pop("comments", None)
    post_copy.pop("comment_count", None)

    data.setdefault("posts", []).append(post_copy)

    for user in data.get("users", []):
        if user.get("id") == post_copy["user_id"]:
            
            user.setdefault("posts", [])
            if post_copy["id"] not in user["posts"]:
                user["posts"].append(post_copy["id"])
            break

    save_data(data)
    created = get_post(post_copy["id"])
    return created if created else post_copy


def update_post(post_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Actualiza los campos de un post existente.

    Solo permite modificar los campos de la lista blanca: title, body,
    board_id, tags. Otras claves en updates son ignoradas. Valores None
    también son ignorados.

    Args:
        post_id: ID del post a actualizar.
        updates: Dict con los campos a actualizar. Claves no permitidas
                 e valores None son descartados.

    Returns:
        Dict del post actualizado con todos los campos enriquecidos,
        o None si el post no existe.
    """
    data = load_data()
    allowed = {"title", "body", "board_id", "tags"}
    for post in data.get("posts", []):
        if post.get("id") == post_id:
            safe_updates = {
                key: value
                for key, value in updates.items()
                if value is not None and key in allowed
            }
            if not safe_updates:
                return get_post(post_id)
            post.update(safe_updates)
            post["updated_at"] = _now_utc_iso()
            save_data(data)
            return get_post(post_id)
    return None


def delete_post(post_id: int) -> bool:
    """
    Elimina un post y todos sus datos asociados en cascada.

    Elimina en orden:
    1. El post de la colección posts.
    2. Todos los comentarios del post.
    3. Los votos sobre el post y sobre sus comentarios.
    4. La referencia al post en el array posts del usuario autor.

    Args:
        post_id: ID del post a eliminar.

    Returns:
        True si el post fue eliminado, False si no existía.
    """
    data = load_data()
    before = len(data.get("posts", []))
    data["posts"] = [p for p in data.get("posts", []) if p.get("id") != post_id]
    if len(data.get("posts", [])) != before:
        # Collect comment IDs before removing them
        comment_ids = {c.get("id") for c in data.get("comments", []) if c.get("post_id") == post_id}
        data["comments"] = [c for c in data.get("comments", []) if c.get("post_id") != post_id]
        # Cascade: remove votes on the post and its comments
        data["votes"] = [
            v for v in data.get("votes", [])
            if not (
                (v.get("target_type") == "post" and v.get("target_id") == post_id)
                or (v.get("target_type") == "comment" and v.get("target_id") in comment_ids)
            )
        ]
        for user in data.get("users", []):
            if post_id in user.get("posts", []):
                user["posts"].remove(post_id)
        save_data(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Vote services
# ---------------------------------------------------------------------------


def _normalize_vote_target(target_type: str) -> str:
    """
    Normaliza y valida el tipo de target de un voto.

    Args:
        target_type: String con el tipo de target (p. ej. "post", "Post").

    Returns:
        String en minúsculas ("post" o "comment").

    Raises:
        ValueError "unsupported target_type": Si el tipo no es post ni comment.
    """
    value = target_type.lower()
    if value not in {'post', 'comment'}:
        raise ValueError('unsupported target_type')
    return value


def _aggregate_vote_stats(votes: list[dict], target_type: str, target_id: int) -> tuple[int, int, int]:
    """
    Calcula estadísticas de votos para un target específico.

    Args:
        votes: Lista completa de votos del sistema.
        target_type: Tipo de target normalizado ("post" o "comment").
        target_id: ID del post o comentario.

    Returns:
        Tupla (score, upvotes, downvotes) donde:
        - score = upvotes - downvotes
        - upvotes = cantidad de votos con value == 1
        - downvotes = cantidad de votos con value == -1
    """
    filtered = [v for v in votes if v.get('target_type') == target_type and v.get('target_id') == target_id]
    upvotes = sum(1 for v in filtered if v.get('value') == 1)
    downvotes = sum(1 for v in filtered if v.get('value') == -1)
    score = upvotes - downvotes
    return score, upvotes, downvotes


def apply_vote(user_id: int, target_type: str, target_id: int, value: int) -> dict:
    """
    Registra, actualiza o elimina el voto de un usuario sobre un post o comentario.

    Lógica idempotente:
    - value=0: elimina el voto existente (si lo hay). No-op si no había voto.
    - value=1 o -1: crea el voto si no existe, o actualiza si ya existía.
    Tras el cambio, actualiza el campo votes/score del entity votado en data.json.

    Args:
        user_id: ID del usuario que emite el voto.
        target_type: Tipo de target ("post" o "comment", case-insensitive).
        target_id: ID del post o comentario votado.
        value: Valor del voto. Debe ser -1, 0 o 1.

    Returns:
        Dict con target_type, target_id, value, score, upvotes, downvotes
        reflejando el estado actualizado después del voto.

    Raises:
        ValueError "value must be -1, 0, or 1": Valor de voto no válido.
        ValueError "unsupported target_type": Tipo de target no válido.
        ValueError "target_not_found": El post o comentario no existe.
    """
    if value not in (-1, 0, 1):
        raise ValueError('value must be -1, 0, or 1')
    normalized_type = _normalize_vote_target(target_type)

    data = load_data()
    entity = _get_entity(data, normalized_type, target_id)
    if entity is None:
        raise ValueError('target_not_found')

    votes = data.setdefault('votes', [])
    existing = next(
        (
            v
            for v in votes
            if v.get('user_id') == user_id
            and v.get('target_type') == normalized_type
            and v.get('target_id') == target_id
        ),
        None,
    )

    if value == 0:
        if existing:
            votes.remove(existing)
    else:
        timestamp = _now_utc_iso()
        if existing:
            existing['value'] = value
            existing['updated_at'] = timestamp
        else:
            votes.append(
                {
                    'id': _next_id(votes),
                    'user_id': user_id,
                    'target_type': normalized_type,
                    'target_id': target_id,
                    'value': value,
                    'created_at': timestamp,
                    'updated_at': timestamp,
                }
            )

    score, upvotes, downvotes = _aggregate_vote_stats(votes, normalized_type, target_id)
    entity['votes'] = score
    entity['score'] = score
    save_data(data)
    return {
        'target_type': normalized_type,
        'target_id': target_id,
        'value': value,
        'score': score,
        'upvotes': upvotes,
        'downvotes': downvotes,
    }


def get_vote_summary(target_type: str, target_id: int, *, user_id: Optional[int] = None) -> Optional[dict]:
    """
    Retorna el resumen de votos de un post o comentario.

    Si se proporciona user_id, incluye el voto que ese usuario emitió
    sobre el target (None si no votó).

    Args:
        target_type: Tipo de target ("post" o "comment", case-insensitive).
        target_id: ID del post o comentario.
        user_id: (Keyword-only, opcional) ID del usuario para incluir
                 su voto personal en la respuesta.

    Returns:
        Dict con target_type, target_id, score, upvotes, downvotes y
        user_vote (int o None). Retorna None si el target no existe.

    Raises:
        ValueError "unsupported target_type": Tipo de target no válido.
    """
    normalized_type = _normalize_vote_target(target_type)
    data = load_data()
    entity = _get_entity(data, normalized_type, target_id)
    if entity is None:
        return None

    votes = data.get('votes', [])
    score, upvotes, downvotes = _aggregate_vote_stats(votes, normalized_type, target_id)
    user_vote = None
    if user_id is not None:
        match = next(
            (
                v
                for v in votes
                if v.get('user_id') == user_id
                and v.get('target_type') == normalized_type
                and v.get('target_id') == target_id
            ),
            None,
        )
        if match:
            user_vote = match.get('value')

    return {
        'target_type': normalized_type,
        'target_id': target_id,
        'score': score,
        'upvotes': upvotes,
        'downvotes': downvotes,
        'user_vote': user_vote,
    }


# ---------------------------------------------------------------------------
# Moderation helpers (reports, actions)
# ---------------------------------------------------------------------------
def _ensure_moderation_root(data: Dict[str, Any]) -> None:
    """
    Garantiza que la sección moderation exista en el documento de datos.

    Crea las claves moderation, moderation.reports y moderation.actions
    si no están presentes (defensivo para archivos anteriores a esta sección).

    Args:
        data: Documento JSON completo cargado con load_data(). Modificado in-place.
    """
    data.setdefault("moderation", {})
    data["moderation"].setdefault("reports", [])
    data["moderation"].setdefault("actions", [])


def _next_id(sequence: List[Dict[str, Any]], key: str = "id") -> int:
    """
    Genera el siguiente ID disponible para una colección.

    Calcula el máximo ID actual y le suma 1. Si la colección está vacía,
    retorna 1 (primer ID válido).

    Args:
        sequence: Lista de dicts de la colección (users, posts, etc.).
        key: Nombre del campo ID. Default: "id".

    Returns:
        Entero con el siguiente ID a usar.
    """
    return max((item.get(key, 0) for item in sequence), default=0) + 1


def _get_entity(data: Dict[str, Any], target_type: str, target_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca y retorna un entity (user, post o comment) del documento de datos.

    Retorna la referencia directa al dict dentro de data (mutable), lo que
    permite modificarlo in-place (p. ej. entity["removed"] = True).

    Args:
        data: Documento JSON completo cargado con load_data().
        target_type: Tipo de entity a buscar: "user", "post" o "comment".
        target_id: ID numérico del entity.

    Returns:
        Dict del entity si existe, None si no se encuentra o si target_type
        no es uno de los tipos soportados.
    """
    kind = target_type.lower()
    if kind == "user":
        return next((u for u in data.get("users", []) if u.get("id") == target_id), None)
    if kind == "post":
        return next((p for p in data.get("posts", []) if p.get("id") == target_id), None)
    if kind == "comment":
        return next((c for c in data.get("comments", []) if c.get("id") == target_id), None)
    return None


def moderation_report_create(
    reporter_id: int,
    target_type: str,
    target_id: int,
    reason: str = "",
) -> Dict[str, Any]:
    """
    Crea un reporte de moderación sobre un post, comentario o usuario.

    Marca el reporte con invalid_target=True si el entity referenciado
    no existe (target borrado antes de reportar).

    Args:
        reporter_id: ID del usuario que emite el reporte.
        target_type: Tipo de entity reportado ("post", "comment", "user").
        target_id: ID del entity reportado.
        reason: Motivo del reporte (texto libre). Default: "".

    Returns:
        Dict del reporte creado con id, created_at, status="pending" y
        el campo invalid_target indicando si el target existe.
    """
    data = load_data()
    _ensure_moderation_root(data)

    report = {
        "id": _next_id(data["moderation"]["reports"]),
        "created_at": _now_utc_iso(),
        "reporter_id": reporter_id,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason or "",
        "status": "pending",
        "invalid_target": _get_entity(data, target_type, target_id) is None,
    }
    data["moderation"]["reports"].append(report)
    save_data(data)
    return report


def moderation_queue_list(status: Optional[str] = "pending") -> List[Dict[str, Any]]:
    """
    Retorna la lista de reportes de moderación, opcionalmente filtrada por estado.

    Args:
        status: Estado a filtrar ("pending", "closed", etc.). Si se pasa None
                o cadena vacía, retorna todos los reportes sin filtrar.
                Default: "pending".

    Returns:
        Lista de dicts de reporte de moderación que coinciden con el filtro.
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
) -> Dict[str, Any]:
    """
    Aplica una acción de moderación sobre un post, comentario o usuario.

    Acciones soportadas:
    - "remove": marca el entity como removed (y locked si es post).
    - "approve": acción sin efecto en el entity (solo registra el log).
    - "lock": bloquea comentarios en el post (solo posts).
    - "sticky": fija el post en el board (solo posts).
    - "ban_user": marca al usuario como baneado (solo users).
    - "shadowban": marca al usuario como shadowbanned (solo users).

    Registra la acción en moderation.actions via _log_moderation_action.
    Si se proporciona report_id, cierra el reporte asociado.

    Args:
        moderator_id: ID del moderador que ejecuta la acción.
        target_type: Tipo de entity afectado ("post", "comment", "user").
        target_id: ID del entity afectado.
        action: Nombre de la acción a aplicar.
        reason: Motivo de la acción (texto libre). Default: "".
        report_id: ID del reporte a cerrar como consecuencia. Default: None.

    Returns:
        Dict con {"applied": True} si la acción fue exitosa, o
        {"applied": False, "error": "<motivo>"} si falló.
    """
    act = action.lower()
    data = load_data()
    _ensure_moderation_root(data)

    entity = _get_entity(data, target_type, target_id)

    valid_actions = {"remove", "approve", "lock", "sticky", "ban_user", "shadowban"}
    if act not in valid_actions:
        result: Dict[str, Any] = {"applied": False, "error": "unknown_action"}
    elif act != "approve" and entity is None:
        result = {"applied": False, "error": "target_not_found"}
    else:
        if act == "remove":
            entity["removed"] = True
            if target_type == "post":
                entity["locked"] = True
        elif act == "approve":
            pass
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

        result = {"applied": True}

        if report_id is not None:
            for report in data["moderation"]["reports"]:
                if report.get("id") == report_id:
                    report["status"] = "closed"
                    report["closed_at"] = _now_utc_iso()
                    report["closed_by"] = moderator_id
                    report["resolution"] = act
                    break

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
    data: Dict[str, Any],
    moderator_id: int,
    target_type: str,
    target_id: int,
    action: str,
    reason: str,
    applied: bool,
    error: Optional[str],
    report_id: Optional[int],
) -> None:
    """
    Añade una entrada al log de acciones de moderación (moderation.actions).

    Siempre se llama, independientemente de si la acción fue exitosa, para
    mantener un audit trail completo de todas las decisiones de moderación.
    Modifica data in-place; el llamador es responsable de persistir con save_data().

    Args:
        data: Documento JSON completo ya cargado y modificado.
        moderator_id: ID del moderador que ejecutó la acción.
        target_type: Tipo de entity afectado.
        target_id: ID del entity afectado.
        action: Nombre de la acción ejecutada.
        reason: Motivo de la acción.
        applied: True si la acción fue aplicada exitosamente.
        error: String con el código de error si applied=False, None si fue exitoso.
        report_id: ID del reporte relacionado, si aplica.
    """
    entry = {
        "id": _next_id(data["moderation"]["actions"]),
        "ts": _now_utc_iso(),
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


# ---------------------------------------------------------------------------
# Servicios de Términos y Condiciones
# ---------------------------------------------------------------------------

def _ensure_terms_root(data: Dict[str, Any]) -> None:
    """
    Garantiza que las colecciones de T&C existan en el documento de datos.

    Crea las listas terms_and_conditions y terms_acceptances si no están
    presentes. Modifica data in-place; el llamador debe persistir con save_data().

    Args:
        data: Documento JSON completo cargado con load_data().
    """
    data.setdefault("terms_and_conditions", [])
    data.setdefault("terms_acceptances", [])


def get_active_terms() -> Optional[Dict[str, Any]]:
    """
    Retorna los Términos y Condiciones actualmente vigentes, o None si no existen.

    Solo puede haber un registro con is_active=True. Si hubiera más de uno
    (inconsistencia de datos), retorna el primero encontrado.

    Returns:
        Dict con id, version, content_url, is_active y created_at del T&C
        activo, o None si no hay ningún T&C activo en el sistema.
    """
    data = load_data()
    _ensure_terms_root(data)
    return next(
        (t for t in data["terms_and_conditions"] if t.get("is_active")),
        None,
    )


def get_user_acceptance(user_id: int, terms_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca la aceptación de un usuario para una versión específica de los T&C.

    Args:
        user_id: ID del usuario cuya aceptación se busca.
        terms_id: ID de los T&C cuya aceptación se verifica.

    Returns:
        Dict de la aceptación si existe, None si el usuario no ha aceptado
        esa versión de los T&C.
    """
    data = load_data()
    _ensure_terms_root(data)
    return next(
        (
            a
            for a in data["terms_acceptances"]
            if a.get("user_id") == user_id and a.get("terms_id") == terms_id
        ),
        None,
    )


def create_acceptance(user_id: int, terms_id: int, ip_address: str) -> Dict[str, Any]:
    """
    Registra la aceptación de los T&C por parte de un usuario.

    Es idempotente: si el usuario ya aceptó esa versión, no crea un registro
    duplicado y retorna la aceptación existente.

    Args:
        user_id: ID del usuario que acepta los T&C.
        terms_id: ID de la versión de T&C aceptada.
        ip_address: Dirección IP del cliente (IPv4 o IPv6, máx 45 chars).

    Returns:
        Dict de la aceptación existente o recién creada, con id, user_id,
        terms_id, ip_address y accepted_at.
    """
    existing = get_user_acceptance(user_id, terms_id)
    if existing:
        return existing

    data = load_data()
    _ensure_terms_root(data)

    acceptance = {
        "id": _next_id(data["terms_acceptances"]),
        "user_id": user_id,
        "terms_id": terms_id,
        "ip_address": ip_address[:45],
        "accepted_at": _now_utc_iso(),
    }
    data["terms_acceptances"].append(acceptance)
    save_data(data)
    return acceptance


def has_accepted_current_terms(user_id: int) -> bool:
    """
    Verifica si un usuario ha aceptado la versión vigente de los T&C.

    Si no hay T&C activos en el sistema, retorna True (no hay nada que aceptar).

    Args:
        user_id: ID del usuario a verificar.

    Returns:
        True si el usuario aceptó los T&C activos o si no hay T&C activos.
        False si hay T&C activos y el usuario no los ha aceptado aún.
    """
    active = get_active_terms()
    if not active:
        return True
    return get_user_acceptance(user_id, active["id"]) is not None
