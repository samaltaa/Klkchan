"""
comments.py — Endpoints de gestión de comentarios de KLKCHAN.

Los comentarios soportan anidación mediante el campo parent_id.
La respuesta siempre es un árbol con replies anidados hasta
un máximo de 6 niveles de profundidad.

Reglas de anidación:
  - parent_id=null → comentario raíz (depth=0).
  - parent_id=<id> → reply al comentario con ese ID.
  - El padre debe pertenecer al mismo post: 400 si pertenece a otro.
  - El padre debe existir: 404 si no existe.

Cascade delete: eliminar un comentario raíz NO elimina sus replies.
Los replies quedan huérfanos y son promovidos a nivel raíz por
build_comment_tree() en las respuestas de lectura.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.deps import get_current_user
from app.schemas import Comment, CommentCreate, CommentListResponse, CommentUpdate, ErrorResponse
from app.services import build_comment_tree, create_comment, delete_comment, get_comment, get_comments, get_comments_for_post, get_post, update_comment
from app.utils.content import enforce_clean_text

router = APIRouter(prefix="/comments", tags=["Comments"])


def _check_comment_ownership(comment: dict, current_user: dict) -> None:
    """
    Verifica que el usuario sea dueño del comentario o tenga rol mod/admin.

    Los moderadores y administradores pueden eliminar cualquier comentario.
    El propietario puede eliminar solo su propio comentario. Cualquier otro
    usuario autenticado recibe 403.

    Args:
        comment: Dict del comentario con campo user_id.
        current_user: Dict del usuario autenticado con campos id y roles.

    Raises:
        HTTPException 403: Si el usuario no es owner ni mod/admin.
    """
    roles = {str(r).lower() for r in current_user.get("roles", [])}
    is_owner = comment.get("user_id") == current_user["id"]
    is_privileged = bool(roles & {"mod", "admin"})
    if not (is_owner or is_privileged):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this comment",
        )


@router.post(
    "",
    response_model=Comment,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def create_new_comment(
    payload: CommentCreate,
    current_user: dict = Depends(get_current_user),
) -> Comment:
    """
    Crea un comentario en un post, opcionalmente como reply de otro comentario.

    Si se omite parent_id se crea un comentario raíz (depth=0).
    Si se provee parent_id se crea un reply anidado bajo ese comentario.

    La respuesta del create devuelve depth=0 y replies=[] siempre,
    independientemente de la posición en el árbol — el depth real se
    calcula al consultar el árbol via GET /posts/{id}/comments.

    Args:
        payload: Datos del comentario: body, post_id y parent_id opcional.
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Comment creado con id, body, post_id, user_id, created_at,
        votes=0, depth=0 y replies=[].

    Raises:
        HTTPException 400: Si body contiene palabras prohibidas.
        HTTPException 400: Si parent_id pertenece a un post diferente.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 404: Si el post (post_id) no existe.
        HTTPException 404: Si parent_id no existe.
    """
    if not get_post(payload.post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    enforce_clean_text(payload.body)
    comment_dict = payload.model_dump()
    comment_dict["user_id"] = current_user["id"]
    try:
        created = create_comment(comment_dict)
    except ValueError as exc:
        err = str(exc)
        if err == "parent_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")
        if err == "parent_wrong_post":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent comment belongs to a different post")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return created


@router.get(
    "/{comment_id}",
    response_model=Comment,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def retrieve_comment(comment_id: int) -> Comment:
    """
    Obtiene un comentario individual por su ID.

    Endpoint público — no requiere autenticación. Retorna el comentario
    con replies=[] y depth=0; el árbol real se obtiene vía
    GET /posts/{id}/comments o GET /comments?post_id={id}.

    Args:
        comment_id: ID del comentario a recuperar.

    Returns:
        Comment con id, body, post_id, user_id, created_at, votes,
        depth=0 y replies=[].

    Raises:
        HTTPException 404: Si el comentario no existe.
    """
    comment = get_comment(comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


@router.patch(
    "/{comment_id}",
    response_model=Comment,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def update_existing_comment(
    comment_id: int,
    payload: CommentUpdate,
    current_user: dict = Depends(get_current_user),
) -> Comment:
    """
    Actualiza el body de un comentario existente.

    Solo el autor del comentario o un mod/admin pueden editarlo.
    El body pasa por enforce_clean_text() para rechazar palabras prohibidas.
    Requiere al menos un campo en el payload; un body vacío retorna 400.

    Args:
        comment_id: ID del comentario a actualizar.
        payload: CommentUpdate con el campo body (opcional).
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Comment actualizado con updated_at refrescado.

    Raises:
        HTTPException 400: Si el payload no contiene ningún campo.
        HTTPException 400: Si body contiene palabras prohibidas.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no es owner ni mod/admin.
        HTTPException 404: Si el comentario no existe.
    """
    comment = get_comment(comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    _check_comment_ownership(comment, current_user)

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "body" in updates:
        enforce_clean_text(updates["body"])

    updated = update_comment(comment_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return updated


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def delete_existing_comment(comment_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    """
    Elimina un comentario por ID. Solo el autor o un mod/admin pueden eliminarlo.

    Nota sobre replies huérfanos: los comentarios hijo (replies) NO se
    eliminan en cascada. Quedan en la base de datos con un parent_id que
    ya no existe y son promovidos a nivel raíz automáticamente por
    build_comment_tree() en las respuestas de lectura.

    Args:
        comment_id: ID del comentario a eliminar.
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        Respuesta vacía 204 No Content.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no es owner ni mod/admin.
        HTTPException 404: Si el comentario no existe.
    """
    comment = next((c for c in get_comments() if c.get("id") == comment_id), None)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    _check_comment_ownership(comment, current_user)
    if not delete_comment(comment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "",
    response_model=CommentListResponse,
)
def list_comments(
    post_id: int = Query(..., ge=1, description="Filter comments by post id."),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[int] = Query(default=None, description="Resume from root comment id greater than this value."),
) -> CommentListResponse:
    """
    Lista los comentarios de un post como árbol anidado con paginación.

    Equivalente a GET /posts/{post_id}/comments pero con post_id como
    query parameter. Retorna el mismo árbol. Puede ser conveniente cuando
    el frontend ya tiene el post_id en estado y no quiere construir la URL
    con path parameter.

    La paginación actúa sobre comentarios raíz: el cursor filtra
    raíces con id > cursor. Los replies se incluyen completos para
    cada raíz retornada.

    Endpoint público (no requiere autenticación).

    Args:
        post_id: ID del post cuyos comentarios se quieren listar (requerido).
        limit: Número máximo de comentarios raíz a retornar (1-200, default 50).
        cursor: ID del último comentario raíz visto para continuar la paginación.

    Returns:
        CommentListResponse con items (árbol de comentarios raíz con replies
        anidados), limit y next_cursor.

    Raises:
        HTTPException 404: Si el post no existe.
        HTTPException 422: Si post_id se omite o es menor a 1.
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
