from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Security, status

from app.deps import get_current_user, oauth2_scheme
from app.schemas import ErrorResponse, User, UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services import (
    create_user as service_create_user,
    delete_user as service_delete_user,
    get_posts,
    get_user,
    get_user_by_email,
    get_user_by_username,
    get_users,
    update_user as service_update_user,
)
from app.utils.content import enforce_clean_text
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])



def _sanitize_user(user: dict) -> dict:
    clean = {**user}
    clean.pop("password", None)
    return clean


def _attach_posts(user: dict) -> dict:
    clean = _sanitize_user(user)
    posts = get_posts()
    clean["posts"] = [post["id"] for post in posts if post.get("user_id") == clean.get("id")]
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
    _ = token
    return _attach_posts(current_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def retrieve_user(user_id: int) -> UserResponse:
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _attach_posts(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
def create_new_user(payload: UserCreate) -> UserResponse:
    from app.utils.helpers import normalize_email
    enforce_clean_text(payload.username, payload.display_name, payload.bio)
    if get_user_by_email(normalize_email(payload.email)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    if get_user_by_username(payload.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    user_dict = payload.model_dump()
    user_dict["password"] = hash_password(payload.password)
    user_dict.setdefault("posts", [])
    created = service_create_user(user_dict)
    return _attach_posts(created)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def update_existing_user(user_id: int, payload: UserUpdate) -> UserResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    enforce_clean_text(
        updates.get("username"),
        updates.get("display_name"),
        updates.get("bio"),
    )
    if "password" in updates and updates["password"] is not None:
        updates["password"] = hash_password(updates["password"])
    updated = service_update_user(user_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _attach_posts(updated)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def delete_self(current_user: dict = Depends(get_current_user)) -> Response:
    if not service_delete_user(current_user["id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
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
    roles = {str(role).lower() for role in current_user.get("roles", [])}
    if current_user["id"] != user_id and "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if not service_delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
