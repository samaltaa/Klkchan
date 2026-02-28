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
    create_post,
    delete_post,
    get_board,
    get_comments_for_post,
    get_post,
    get_posts,
    update_post,
)
from app.utils.content import enforce_clean_text

router = APIRouter(prefix="/posts", tags=["Posts"])


def _check_post_ownership(post: dict, current_user: dict) -> None:
    """Verifica que el usuario sea dueño del post o tenga rol mod/admin."""
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
) -> PostListResponse:
    posts = get_posts()
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
