from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas import Board, BoardCreate, BoardListResponse, BoardUpdate, ErrorResponse
from app.services import create_board, delete_board, get_board, list_boards, update_board
from app.utils.banned_words import has_banned_words

router = APIRouter(prefix="/boards", tags=["Boards"])


def _enforce_clean_text(*texts: Optional[str]) -> None:
    for text in texts:
        if text and has_banned_words(text, lang_hint="es"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text contains banned words.",
            )


@router.get(
    "",
    response_model=BoardListResponse,
)
def list_all_boards(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[int] = Query(default=None, description="Resume from board id greater than this value."),
) -> BoardListResponse:
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
    _enforce_clean_text(payload.name, payload.description)
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
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    _enforce_clean_text(updates.get("name"), updates.get("description"))
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
    if not delete_board(board_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
