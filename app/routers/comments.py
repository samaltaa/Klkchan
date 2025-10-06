from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.deps import get_current_user
from app.schemas import Comment, CommentCreate, CommentListResponse, ErrorResponse
from app.services import create_comment, delete_comment, get_comments_for_post, get_post
from app.utils.banned_words import has_banned_words

router = APIRouter(prefix="/comments", tags=["Comments"])


def _enforce_clean_text(text: Optional[str]) -> None:
    if text and has_banned_words(text, lang_hint="es"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text contains banned words.",
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
    if not get_post(payload.post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    _enforce_clean_text(payload.body)
    comment_dict = payload.model_dump()
    comment_dict["user_id"] = current_user["id"]
    created = create_comment(comment_dict)
    return created


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def delete_existing_comment(comment_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    _ = current_user  # Placeholder for ownership/role enforcement
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
    cursor: Optional[int] = Query(default=None, description="Resume from comment id greater than this value."),
) -> CommentListResponse:
    if not get_post(post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    comments = get_comments_for_post(post_id)
    if cursor is not None:
        comments = [comment for comment in comments if comment.get("id") > cursor]
    sliced = comments[:limit]
    has_more = len(comments) > limit
    next_cursor = sliced[-1]["id"] if sliced and has_more else None
    return CommentListResponse(items=sliced, limit=limit, next_cursor=next_cursor)
