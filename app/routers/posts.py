"""
posts.py — Endpoints de gestión de posts de KLKCHAN.

Los posts son el contenido principal del sistema. Cada post
pertenece a un board y puede recibir comentarios anidados y votos.

Sorting disponible en GET /posts via ?sort=:
  - new  → más recientes primero por created_at (default).
  - top  → mayor puntuación de votos primero.
  - hot  → algoritmo score = votos / (horas_desde_creación + 2)^1.5,
            decae con el tiempo favoreciendo posts recientes y votados.

Nota: el cursor de paginación es siempre por ID, independientemente
del sort elegido. Mezclar cursor con sort!=new puede producir
páginas incompletas si los IDs no coinciden con el orden de sort.

Cascade delete: eliminar un post elimina todos sus comentarios
y los votos sobre el post y sus comentarios.
"""
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.deps import get_current_user
from app.schemas import (
    CommentListResponse,
    ErrorResponse,
    Post,
    PostCreate,
    PostListResponse,
    PostUpdate,
)
from app.services import (
    build_comment_tree,
    create_post,
    delete_post,
    get_board,
    get_comments_for_post,
    get_post,
    get_posts,
    get_posts_sorted,
    update_post,
)
from app.utils.content import enforce_clean_text

router = APIRouter(prefix="/posts", tags=["Posts"])


class SortMode(str, Enum):
    """Criterios de ordenamiento disponibles para GET /posts."""

    new = "new"
    top = "top"
    hot = "hot"


def _check_post_ownership(post: dict, current_user: dict) -> None:
    """
    Verifica que el usuario sea dueño del post o tenga rol mod/admin.

    Los moderadores y administradores pueden modificar cualquier post.
    El propietario puede modificar solo su propio post. Cualquier otro
    usuario autenticado recibe 403.

    Args:
        post: Dict del post con campo user_id.
        current_user: Dict del usuario autenticado con campos id y roles.

    Raises:
        HTTPException 403: Si el usuario no es owner ni mod/admin.
    """
    roles = {str(r).lower() for r in current_user.get("roles", [])}
    is_owner = post.get("user_id") == current_user["id"]
    is_privileged = bool(roles & {"mod", "admin"})
    if not (is_owner or is_privileged):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this post",
        )


@router.get(
    "",
    response_model=PostListResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def list_posts(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[int] = Query(default=None, description="Resume from post id greater than this value."),
    sort: SortMode = Query(SortMode.new, description="Sort order: new (default), top, hot"),
) -> PostListResponse:
    """
    Lista posts con paginación cursor-based y ordenamiento configurable.

    Cada post incluye su árbol completo de comentarios anidados en el
    campo comments, además de comment_count, votes, score, tags y
    attachments. Endpoint público (no requiere autenticación).

    Criterios de sort:
    - new  → created_at descendente (más recientes primero, default).
    - top  → votes descendente (más votados primero).
    - hot  → score decreciente: votos / (horas + 2)^1.5.

    Nota sobre cursor + sort: el cursor filtra por ID (>cursor),
    no por posición en el sort. Para paginación correcta con sort=top
    o sort=hot, el cliente debe gestionar que el next_cursor sea
    coherente con el ordenamiento elegido.

    Args:
        limit: Número máximo de posts a retornar (1-100, default 20).
        cursor: ID del último post visto. Si se omite, retorna desde el inicio.
        sort: Criterio de ordenamiento (new|top|hot, default new).

    Returns:
        PostListResponse con items (lista de Post con comments anidados),
        limit y next_cursor.

    Raises:
        HTTPException 422: Si sort contiene un valor no válido.
    """
    posts = get_posts_sorted(sort.value)
    if cursor is not None:
        posts = [post for post in posts if post.get("id") > cursor]
    sliced = posts[:limit]
    has_more = len(posts) > limit
    next_cursor = sliced[-1]["id"] if sliced and has_more else None
    return PostListResponse(items=sliced, limit=limit, next_cursor=next_cursor)


@router.get(
    "/{post_id}",
    response_model=Post,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def retrieve_post(post_id: int) -> Post:
    """
    Retorna un post por su ID con todos sus comentarios anidados.

    El campo comments contiene el árbol completo de comentarios
    (máximo 6 niveles de profundidad). Endpoint público.

    Args:
        post_id: ID entero del post a buscar.

    Returns:
        Post con id, title, body, board_id, user_id, created_at,
        votes, score, tags, attachments, comment_count y comments (árbol).

    Raises:
        HTTPException 404: Si el post no existe.
    """
    post = get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.post(
    "",
    response_model=Post,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    },
)
def create_new_post(
    payload: PostCreate,
    current_user: dict = Depends(get_current_user),
) -> Post:
    """
    Crea un nuevo post en el board especificado.

    Verifica que el board exista antes de crear el post. Los campos
    title y body pasan por enforce_clean_text para filtrar lenguaje
    prohibido. El user_id se toma del token autenticado.

    Args:
        payload: Datos del post: title, body, board_id, tags, attachments.
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Post creado con id, user_id, created_at, comments=[] y comment_count=0.

    Raises:
        HTTPException 400: Si title o body contienen palabras prohibidas.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 404: Si el board_id no existe.
        HTTPException 422: Si title o body no cumplen las restricciones de schema.
    """
    if not get_board(payload.board_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    enforce_clean_text(payload.title, payload.body)
    post_data = payload.model_dump()
    post_data["user_id"] = current_user["id"]
    created = create_post(post_data)
    return created


@router.put(
    "/{post_id}",
    response_model=Post,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    },
)
def update_existing_post(
    post_id: int,
    payload: PostUpdate,
    current_user: dict = Depends(get_current_user),
) -> Post:
    """
    Actualiza un post existente. Solo el autor o un mod/admin pueden editarlo.

    Campos actualizables: title, body, board_id, tags. Los campos title y
    body pasan por enforce_clean_text. Si el payload no contiene ningún
    campo retorna 400.

    Args:
        post_id: ID del post a actualizar.
        payload: Campos a actualizar (todos opcionales via PostUpdate).
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Post actualizado con todos los campos enriquecidos y updated_at renovado.

    Raises:
        HTTPException 400: Si no se provee ningún campo para actualizar.
        HTTPException 400: Si title o body contienen palabras prohibidas.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no es owner ni mod/admin.
        HTTPException 404: Si el post no existe.
    """
    post = get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_post_ownership(post, current_user)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    enforce_clean_text(updates.get("title"), updates.get("body"))
    updated = update_post(post_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return updated


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    },
)
def delete_existing_post(post_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    """
    Elimina un post y todo su contenido asociado en cascada.

    Solo el autor o un mod/admin pueden eliminar el post.
    La eliminación en cascada incluye todos los comentarios del post
    y los votos sobre el post y sus comentarios.

    Args:
        post_id: ID del post a eliminar.
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Respuesta vacía 204 No Content.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no es owner ni mod/admin.
        HTTPException 404: Si el post no existe.
    """
    post = get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _check_post_ownership(post, current_user)
    if not delete_post(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{post_id}/comments",
    response_model=CommentListResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def list_comments_for_post(
    post_id: int,
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[int] = Query(default=None, description="Resume from root comment id greater than this value."),
) -> CommentListResponse:
    """
    Lista los comentarios de un post como árbol anidado con paginación.

    Retorna únicamente los comentarios raíz (sin parent_id) en el nivel
    superior; los replies aparecen anidados en el campo replies de su
    padre. El árbol tiene un máximo de 6 niveles de profundidad.

    La paginación actúa sobre los comentarios raíz: el cursor filtra
    raíces con id > cursor. Los replies de cada raíz se incluyen
    completos independientemente de la paginación.

    Endpoint alternativo a GET /comments?post_id=X — ambos retornan
    el mismo árbol.

    Args:
        post_id: ID del post cuyos comentarios se quieren obtener.
        limit: Número máximo de comentarios raíz a retornar (1-200, default 50).
        cursor: ID del último comentario raíz visto para continuar la paginación.

    Returns:
        CommentListResponse con items (árbol de comentarios raíz con replies
        anidados), limit y next_cursor.

    Raises:
        HTTPException 404: Si el post no existe.
    """
    if not get_post(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    all_comments = get_comments_for_post(post_id)
    tree = build_comment_tree(all_comments)
    if cursor is not None:
        tree = [c for c in tree if c.get("id") > cursor]
    sliced = tree[:limit]
    has_more = len(tree) > limit
    next_cursor = sliced[-1]["id"] if sliced and has_more else None
    return CommentListResponse(items=sliced, limit=limit, next_cursor=next_cursor)
