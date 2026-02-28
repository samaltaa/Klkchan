from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.deps import get_current_user, require_role
from app.schemas import ErrorResponse, RoleUpdate, RoleUpdateResponse, User, UserListResponse
from app.services import delete_user, get_user, get_users, load_data, update_user_roles
from app.utils.roles import Role

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role(Role.admin))],
)


def _sanitize(user: dict) -> dict:
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
    """Lista todos los usuarios. Solo admin."""
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
    """Añade o elimina un rol de un usuario. Solo admin."""
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
    """Estadísticas del sistema. Solo admin."""
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
    """Elimina un usuario (solo admin). El admin no puede eliminarse a sí mismo."""
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    if not delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
