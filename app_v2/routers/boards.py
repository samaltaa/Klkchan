from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app_v2.schemas import BoardV2, BoardListResponseV2
from app_v1.services import list_boards, get_board

router = APIRouter(prefix="/boards", tags=["Boards"])

@router.get("", response_model=BoardListResponseV2)
def list_boards_v2(limit: int = Query(50, ge=1, le=200), cursor: Optional[int] = None):
    boards = list_boards()
    if cursor:
        boards = [b for b in boards if b["id"] > cursor]
    boards = boards[:limit]
    items = [BoardV2(id=b["id"], name=b["name"], description=b.get("description"), post_count=len(b.get("posts", [])) if isinstance(b.get("posts"), list) else 0) for b in boards]
    return BoardListResponseV2(items=items, total=len(items))

@router.get("/{board_id}", response_model=BoardV2)
def get_board_v2(board_id: int):
    b = get_board(board_id)
    if not b:
        raise HTTPException(status_code=404, detail="Board no encontrado")
    return BoardV2(id=b["id"], name=b["name"], description=b.get("description"), post_count=len(b.get("posts", [])) if isinstance(b.get("posts"), list) else 0)
