"""
users.py — Endpoints de gestión de usuarios de KLKCHAN.

Expone operaciones CRUD sobre usuarios con control de acceso:
- Lectura pública: cualquiera puede ver perfiles y listas.
- Escritura propia: el usuario autenticado edita su propio perfil
  (PUT /{user_id} y DELETE /me).
- Escritura admin: los administradores pueden eliminar cualquier usuario
  (DELETE /{user_id}).

Todos los endpoints de perfil incluyen karma calculado al vuelo
(post_karma + comment_karma + karma total) vía calculate_user_karma().
La contraseña nunca se expone en ninguna respuesta (_sanitize_user).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Security, status

from app.deps import get_current_payload, get_current_user, oauth2_scheme
from app.utils.token_blacklist import revoke as revoke_token
from app.schemas import ErrorResponse, UserListResponse, UserResponse, UserUpdate
from app.services import (
    calculate_user_karma,
    delete_user as service_delete_user,
    get_posts,
    get_user,
    get_users,
    update_user as service_update_user,
)
from app.utils.content import enforce_clean_text

router = APIRouter(prefix="/users", tags=["Users"])



def _sanitize_user(user: dict) -> dict:
    """
    Elimina el campo password de un dict de usuario antes de exponerlo en la API.

    Args:
        user: Dict de usuario tal como está en data.json (incluye password hash).

    Returns:
        Copia del dict sin el campo password. Todos los demás campos intactos.
    """
    clean = {**user}
    clean.pop("password", None)
    return clean


def _attach_posts(user: dict) -> dict:
    """
    Enriquece un usuario sanitizado con sus posts y karma calculado.

    Combina tres operaciones en una:
    1. Sanitiza (elimina password via _sanitize_user).
    2. Calcula la lista de IDs de posts del usuario.
    3. Añade karma, post_karma y comment_karma al vuelo.

    Se usa como paso final en todos los endpoints GET de usuario
    antes de retornar la respuesta.

    Args:
        user: Dict de usuario tal como está en data.json.

    Returns:
        Dict del usuario con password eliminado, campo posts (lista de IDs),
        y campos karma, post_karma, comment_karma calculados.
    """
    clean = _sanitize_user(user)
    posts = get_posts()
    clean["posts"] = [post["id"] for post in posts if post.get("user_id") == clean.get("id")]
    clean.update(calculate_user_karma(clean["id"]))
    return clean


@router.get(
    "",
    response_model=UserListResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
def list_users(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[int] = Query(default=None, description="Resume from user id greater than this value."),
) -> UserListResponse:
    """
    Lista todos los usuarios con paginación cursor-based.

    Los usuarios se ordenan por ID ascendente. El cursor indica el último
    ID visto; la siguiente página retorna IDs mayores al cursor.
    Cada usuario incluye karma calculado al vuelo y lista de IDs de posts.
    Endpoint público (no requiere autenticación).

    Args:
        limit: Número máximo de usuarios a retornar (1-200, default 50).
        cursor: ID del último usuario visto. Si se omite, retorna desde el inicio.

    Returns:
        UserListResponse con items (lista de UserResponse), limit y next_cursor
        (ID del último item si hay más páginas, null si es la última).

    Raises:
        HTTPException 422: Si limit está fuera del rango permitido.
    """
    users = sorted(get_users(), key=lambda u: u.get("id", 0))
    if cursor is not None:
        users = [user for user in users if user.get("id") > cursor]
    sliced = users[:limit]
    has_more = len(users) > limit
    next_cursor = sliced[-1]["id"] if sliced and has_more else None
    items = [_attach_posts(user) for user in sliced]
    return UserListResponse(items=items, limit=limit, next_cursor=next_cursor)


@router.get(
    "/me",
    response_model=UserResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def read_me(
    token: str = Security(oauth2_scheme),
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """
    Retorna el perfil del usuario actualmente autenticado.

    Requiere un access token válido. Incluye karma calculado al vuelo
    y lista de IDs de posts del usuario autenticado.

    Args:
        token: Bearer token del header Authorization (extraído por oauth2_scheme).
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        UserResponse del usuario autenticado con posts, karma, post_karma
        y comment_karma.

    Raises:
        HTTPException 401: Si el token no se provee, es inválido o está revocado.
    """
    _ = token
    return _attach_posts(current_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def retrieve_user(user_id: int) -> UserResponse:
    """
    Retorna el perfil público de un usuario por su ID.

    Endpoint público (no requiere autenticación). Incluye karma calculado
    al vuelo y lista de IDs de posts del usuario.

    Args:
        user_id: ID entero del usuario a buscar.

    Returns:
        UserResponse del usuario con posts, karma, post_karma y comment_karma.

    Raises:
        HTTPException 404: Si el usuario no existe.
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _attach_posts(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def update_existing_user(
    user_id: int,
    payload: UserUpdate,
    current_user: dict = Depends(get_current_user),
) -> UserResponse:
    """
    Actualiza el perfil de un usuario existente.

    Solo el propio usuario o un administrador pueden modificar el perfil.
    Campos actualizables: username, email, display_name, bio.
    El campo password NO es modificable por este endpoint — usar
    PATCH /auth/change-password que verifica la contraseña anterior.
    Los campos de contenido (username, display_name, bio) pasan por
    enforce_clean_text para filtrar lenguaje prohibido.

    Args:
        user_id: ID del usuario a actualizar.
        payload: Campos a actualizar (todos opcionales via UserUpdate).
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        UserResponse del usuario actualizado con karma y posts recalculados.

    Raises:
        HTTPException 400: Si no se provee ningún campo para actualizar.
        HTTPException 400: Si el contenido contiene palabras prohibidas.
        HTTPException 401: Si el token no es válido.
        HTTPException 403: Si el usuario no es el propietario ni admin.
        HTTPException 404: Si el usuario no existe.
        HTTPException 409: Si el nuevo email ya está en uso.
    """
    roles = {str(r).lower() for r in current_user.get("roles", [])}
    if current_user["id"] != user_id and "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar este perfil",
        )
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    enforce_clean_text(
        updates.get("username"),
        updates.get("display_name"),
        updates.get("bio"),
    )
    updated = service_update_user(user_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _attach_posts(updated)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def delete_self(
    current_user: dict = Depends(get_current_user),
    token_payload: dict = Depends(get_current_payload),
) -> Response:
    """
    Elimina la cuenta del usuario autenticado (auto-eliminación).

    Elimina en cascada todos los posts, comentarios y votos del usuario
    (via service_delete_user). Además revoca el access token activo
    añadiéndolo a la blacklist, por lo que cualquier request posterior
    con ese token recibirá 401 inmediatamente.

    Args:
        current_user: Usuario autenticado (inyectado por get_current_user).
        token_payload: Claims del JWT activo (inyectado por get_current_payload).

    Returns:
        Respuesta vacía 204 No Content.

    Raises:
        HTTPException 401: Si el token no es válido.
        HTTPException 404: Si el usuario ya no existe (caso de borde).
    """
    if not service_delete_user(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    jti = token_payload.get("jti")
    exp = token_payload.get("exp", 0)
    if jti:
        revoke_token(jti, float(exp))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def delete_existing_user(user_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    """
    Elimina un usuario por ID. Requiere ser el propio usuario o admin.

    Control de acceso:
    - El propio usuario puede eliminarse (equivalente a DELETE /me).
    - Un admin puede eliminar cualquier usuario.
    - Cualquier otro intento recibe 403.

    Elimina en cascada todos los posts, comentarios y votos del usuario.

    Args:
        user_id: ID del usuario a eliminar.
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Respuesta vacía 204 No Content.

    Raises:
        HTTPException 401: Si el token no es válido.
        HTTPException 403: Si el usuario no es el propietario ni admin.
        HTTPException 404: Si el usuario a eliminar no existe.
    """
    roles = {str(role).lower() for role in current_user.get("roles", [])}
    if current_user["id"] != user_id and "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if not service_delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
