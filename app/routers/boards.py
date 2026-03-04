"""
boards.py — Endpoints de gestión de boards de KLKCHAN.

Un board es el equivalente a un subreddit: un espacio temático
donde los usuarios publican posts. Cada board tiene un nombre
único y un contador de posts calculado al vuelo.

Cascade delete: eliminar un board elimina en cascada todos sus
posts, los comentarios de esos posts y los votos asociados.

Nota de seguridad: actualmente ningún endpoint de escritura
(POST, PUT, DELETE) requiere autenticación. En producción
deberían requerir rol admin o mod.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas import Board, BoardCreate, BoardListResponse, BoardUpdate, ErrorResponse
from app.services import create_board, delete_board, get_board, list_boards, update_board
from app.utils.content import enforce_clean_text

router = APIRouter(prefix="/boards", tags=["Boards"])


@router.get(
    "",
    response_model=BoardListResponse,
)
def list_all_boards(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[int] = Query(default=None, description="Resume from board id greater than this value."),
) -> BoardListResponse:
    """
    Lista todos los boards con paginación cursor-based.

    Los boards se ordenan por ID ascendente. Cada board incluye
    post_count (cantidad de posts publicados en ese board),
    calculado al vuelo.
    Endpoint público (no requiere autenticación).

    Args:
        limit: Número máximo de boards a retornar (1-200, default 50).
        cursor: ID del último board visto. Si se omite, retorna desde el inicio.

    Returns:
        BoardListResponse con items (lista de Board), limit y next_cursor
        (ID del último item si hay más páginas, null si es la última página).
    """
    boards = list_boards()
    if cursor is not None:
        boards = [board for board in boards if board.get("id") > cursor]
    sliced = boards[:limit]
    has_more = len(boards) > limit
    next_cursor = sliced[-1]["id"] if sliced and has_more else None
    return BoardListResponse(items=sliced, limit=limit, next_cursor=next_cursor)


@router.get(
    "/{board_id}",
    response_model=Board,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def retrieve_board(board_id: int) -> Board:
    """
    Retorna un board por su ID.

    Incluye post_count calculado al vuelo. Endpoint público.

    Args:
        board_id: ID entero del board a buscar.

    Returns:
        Board con id, name, description, slug, created_at,
        updated_at y post_count.

    Raises:
        HTTPException 404: Si el board no existe.
    """
    board = get_board(board_id)
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


@router.post(
    "",
    response_model=Board,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
def create_new_board(payload: BoardCreate) -> Board:
    """
    Crea un nuevo board.

    Los campos name y description pasan por enforce_clean_text
    para filtrar lenguaje prohibido. El ID se asigna automáticamente.

    Nota: este endpoint no requiere autenticación (ver docstring de módulo).

    Args:
        payload: Datos del board con name (3-64 chars) y description opcional.

    Returns:
        Board creado con id, name, description, created_at y post_count=0.

    Raises:
        HTTPException 400: Si name o description contienen palabras prohibidas.
        HTTPException 422: Si name no cumple el mínimo de longitud.
    """
    enforce_clean_text(payload.name, payload.description)
    board_dict = payload.model_dump()
    created = create_board(board_dict)
    return created


@router.put(
    "/{board_id}",
    response_model=Board,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def update_existing_board(board_id: int, payload: BoardUpdate) -> Board:
    """
    Actualiza el nombre y/o descripción de un board.

    Solo se permiten los campos name y description; otros son ignorados.
    Ambos campos pasan por enforce_clean_text para filtrar contenido
    prohibido. Si el payload no contiene ningún campo válido retorna 400.

    Nota: este endpoint no requiere autenticación (ver docstring de módulo).

    Args:
        board_id: ID del board a actualizar.
        payload: Campos a actualizar. Todos opcionales (BoardUpdate).

    Returns:
        Board actualizado con los campos modificados y updated_at renovado.

    Raises:
        HTTPException 400: Si no se provee ningún campo para actualizar.
        HTTPException 400: Si el contenido contiene palabras prohibidas.
        HTTPException 404: Si el board no existe.
    """
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    enforce_clean_text(updates.get("name"), updates.get("description"))
    updated = update_board(board_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return updated


@router.delete(
    "/{board_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def delete_existing_board(board_id: int) -> Response:
    """
    Elimina un board y todo su contenido en cascada.

    La eliminación en cascada incluye, en orden:
    1. El board.
    2. Todos los posts del board.
    3. Todos los comentarios de esos posts.
    4. Todos los votos sobre esos posts y comentarios.

    Esta operación es irreversible.
    Nota: este endpoint no requiere autenticación (ver docstring de módulo).

    Args:
        board_id: ID del board a eliminar.

    Returns:
        Respuesta vacía 204 No Content.

    Raises:
        HTTPException 404: Si el board no existe.
    """
    if not delete_board(board_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
