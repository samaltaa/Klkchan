"""
admin.py — Endpoints de administración de KLKCHAN.

Panel de control exclusivo para administradores. Permite gestionar
usuarios, asignar roles y consultar estadísticas globales del sistema.

Diferencia entre roles:
  - mod:   puede moderar contenido (queue, actions, reports).
  - admin: puede moderar contenido + gestionar usuarios y roles
           + ver stats globales + eliminar cualquier usuario.

Todos los endpoints de este router requieren rol admin. El check
se aplica a nivel de router mediante dependencies=[Depends(require_role(Role.admin))].
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app_v1.deps import get_current_user, require_role
from app_v1.schemas import ErrorResponse, RoleUpdate, RoleUpdateResponse, User, UserListResponse
from app_v1.services import delete_user, get_post, get_user, get_users, load_data, lock_post, shadowban_user, sticky_post, update_user_roles
from app_v1.utils.roles import Role

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(Role.admin))],
)


def _sanitize(user: dict) -> dict:
    """
    Elimina campos sensibles del dict de usuario antes de retornarlo.

    Remueve la clave 'password' (hash bcrypt) para que no aparezca
    en las respuestas de la API de administración.

    Args:
        user: Dict del usuario tal como viene de get_users().

    Returns:
        Copia del dict sin la clave 'password'.
    """
    clean = {**user}
    clean.pop("password", None)
    return clean


@router.get(
    "/users",
    response_model=UserListResponse,
    responses={status.HTTP_403_FORBIDDEN: {"model": ErrorResponse}},
)
def list_users_admin(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[int] = Query(default=None, description="Resume from user id greater than this value."),
) -> UserListResponse:
    """
    Lista todos los usuarios del sistema con paginación cursor-based.

    Retorna usuarios ordenados por ID ascendente. El campo password se omite
    de todos los registros. A diferencia de GET /users (público), este endpoint
    muestra datos completos incluyendo roles. Solo accesible para administradores.

    Args:
        limit: Número máximo de usuarios a retornar (1-200, default 50).
        cursor: ID del último usuario visto. Si se omite, retorna desde el inicio.

    Returns:
        UserListResponse con items (lista de User sin password), limit y next_cursor.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
    """
    users = sorted(get_users(), key=lambda u: u.get("id", 0))
    if cursor is not None:
        users = [u for u in users if u.get("id", 0) > cursor]
    sliced = users[:limit]
    has_more = len(users) > limit
    next_cursor = sliced[-1]["id"] if sliced and has_more else None
    items = [_sanitize(u) for u in sliced]
    return UserListResponse(items=items, limit=limit, next_cursor=next_cursor)


@router.patch(
    "/users/{user_id}/role",
    response_model=RoleUpdateResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    current_user: dict = Depends(get_current_user),
) -> RoleUpdateResponse:
    """
    Añade o elimina un rol de un usuario. Solo admin.

    El rol base 'user' no puede ser removido. El admin no puede quitarse
    a sí mismo el rol 'admin'. El rol 'user' se garantiza siempre presente
    en el conjunto final de roles, independientemente de la acción.

    Roles asignables: user, mod, admin.
    Acciones disponibles: add, remove (ver RoleAction en schemas).

    Args:
        user_id: ID del usuario a modificar.
        payload: Datos con role (UserRole) y action (add|remove).
        current_user: Admin autenticado (inyectado por get_current_user).

    Returns:
        RoleUpdateResponse con user_id, username, roles (lista actualizada)
        y message confirmando la acción realizada.

    Raises:
        HTTPException 400: Si se intenta remover el rol base 'user'.
        HTTPException 400: Si el admin intenta quitarse a sí mismo el rol admin.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
        HTTPException 404: Si el usuario objetivo no existe.
        HTTPException 500: Si la actualización falla inesperadamente.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevenir que el admin se quite a sí mismo el rol admin
    if user_id == current_user["id"] and payload.role.value == "admin" and payload.action.value == "remove":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin role from yourself",
        )

    # No permitir remover el rol base 'user'
    if payload.role.value == "user" and payload.action.value == "remove":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove 'user' role (it's the base role)",
        )

    current_roles = set(user.get("roles", ["user"]))
    if payload.action.value == "add":
        current_roles.add(payload.role.value)
        message = f"Role '{payload.role.value}' added successfully"
    else:
        current_roles.discard(payload.role.value)
        message = f"Role '{payload.role.value}' removed successfully"

    # Garantizar que siempre tenga el rol base
    current_roles.add("user")

    updated = update_user_roles(user_id, list(current_roles))
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update roles")

    return RoleUpdateResponse(
        user_id=updated["id"],
        username=updated["username"],
        roles=updated["roles"],
        message=message,
    )


@router.get(
    "/stats",
    responses={status.HTTP_403_FORBIDDEN: {"model": ErrorResponse}},
)
def admin_stats() -> dict:
    """
    Retorna estadísticas globales del sistema. Solo admin.

    Lee directamente de la capa de datos sin filtros ni cache.
    Las métricas se calculan al vuelo en cada petición.

    Returns:
        Dict con dos secciones:
        - users:   total, admins, moderators, regular (solo rol 'user').
        - content: boards, posts, comments, votes.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
    """
    data = load_data()
    users = data.get("users", [])
    return {
        "users": {
            "total": len(users),
            "admins": sum(1 for u in users if "admin" in u.get("roles", [])),
            "moderators": sum(1 for u in users if "mod" in u.get("roles", [])),
            "regular": sum(1 for u in users if u.get("roles", ["user"]) == ["user"]),
        },
        "content": {
            "boards": len(data.get("boards", [])),
            "posts": len(data.get("posts", [])),
            "comments": len(data.get("comments", [])),
            "votes": len(data.get("votes", [])),
        },
    }


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def delete_user_admin(
    user_id: int,
    current_user: dict = Depends(get_current_user),
) -> Response:
    """
    Elimina un usuario por su ID. Solo admin.

    El cascade delete elimina todos los posts, comentarios y votos del usuario
    eliminado (igual que DELETE /users/me). El admin no puede eliminarse a sí
    mismo via este endpoint; debe usar DELETE /users/me para eso.

    Args:
        user_id: ID del usuario a eliminar.
        current_user: Admin autenticado (inyectado por get_current_user).

    Returns:
        Respuesta vacía 204 No Content.

    Raises:
        HTTPException 400: Si el admin intenta eliminarse a sí mismo.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
        HTTPException 404: Si el usuario no existe.

    Notas:
        A diferencia de DELETE /users/me, este endpoint no revoca el token
        del usuario eliminado. Si el usuario tenía sesiones activas, sus tokens
        seguirán siendo válidos hasta su expiración natural.
    """
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    if not delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/posts/{post_id}/lock",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
def lock_post_admin(post_id: int) -> dict:
    """
    Bloquea un post impidiendo nuevos comentarios. Solo admin.

    Idempotente: bloquear un post ya bloqueado retorna 200 sin error.

    Args:
        post_id: ID del post a bloquear.

    Returns:
        Dict con post_id, locked (True), sticky y detail.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
        HTTPException 404: Si el post no existe.
    """
    post = get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    updated = lock_post(post_id)
    return {
        "post_id": post_id,
        "locked": updated.get("locked", True),
        "sticky": updated.get("sticky", False),
        "detail": "Post locked",
    }


@router.post(
    "/posts/{post_id}/sticky",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
def sticky_post_admin(post_id: int) -> dict:
    """
    Fija un post en la parte superior de su board. Solo admin.

    Idempotente: fijar un post ya fijado retorna 200 sin error.
    Un post puede estar locked y sticky simultáneamente.

    Args:
        post_id: ID del post a fijar.

    Returns:
        Dict con post_id, locked, sticky (True) y detail.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
        HTTPException 404: Si el post no existe.
    """
    post = get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    updated = sticky_post(post_id)
    return {
        "post_id": post_id,
        "locked": updated.get("locked", False),
        "sticky": updated.get("sticky", True),
        "detail": "Post marked as sticky",
    }


@router.post(
    "/users/{user_id}/shadowban",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    },
)
def shadowban_user_admin(
    user_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Aplica un shadowban a un usuario. Solo admin.

    El usuario shadowbaneado no recibe notificación; su contenido queda
    oculto para el resto de usuarios pero él lo sigue viendo con normalidad.
    Idempotente.

    Args:
        user_id: ID del usuario a shadowbanear.
        current_user: Admin autenticado (inyectado por get_current_user).

    Returns:
        Dict con user_id, username, shadowbanned (True) y detail.

    Raises:
        HTTPException 400: Si el admin intenta shadowbanearse a sí mismo.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol admin.
        HTTPException 404: Si el usuario no existe.
    """
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot shadowban yourself",
        )
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = shadowban_user(user_id)
    return {
        "user_id": user_id,
        "username": updated.get("username", ""),
        "shadowbanned": updated.get("shadowbanned", True),
        "detail": "User shadowbanned",
    }
