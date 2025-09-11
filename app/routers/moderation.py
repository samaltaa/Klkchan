# app/routers/moderation.py
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import require_role
from app.utils.roles import Role
from app.services import (
    get_user_by_id,
    delete_user,
    get_post,
    delete_post,
    load_data,
    save_data,
)

router = APIRouter(prefix="/moderation", tags=["Moderation"])


# ─────────────────────────── Schemas ───────────────────────────
class TargetType(str, Enum):
    user = "user"
    post = "post"
    comment = "comment"


class ActionType(str, Enum):
    remove = "remove"        # Ocultar/Eliminar recurso
    approve = "approve"      # No-op aquí; útil si implementas colas
    lock = "lock"            # Placeholder para post/comentario
    sticky = "sticky"        # Placeholder para post
    ban_user = "ban_user"    # Ban lógico = delete_user en JSON store
    shadowban = "shadowban"  # Placeholder


class ModerationActionRequest(BaseModel):
    target_type: TargetType = Field(..., description="user | post | comment")
    target_id: int = Field(..., ge=1)
    action: ActionType
    reason: Optional[str] = None


class ModerationActionResponse(BaseModel):
    applied: bool
    detail: Optional[str] = None


# ───────────────────── Queue (placeholder) ─────────────────────
@router.get("/queue", dependencies=[Depends(require_role(Role.mod, Role.admin))])
def moderation_queue():
    # TODO: Integrar reports/flags reales
    return {"items": []}


# ──────────────────────── Actions (core) ───────────────────────
@router.post(
    "/actions",
    response_model=ModerationActionResponse,
    dependencies=[Depends(require_role(Role.mod, Role.admin))],
)
def moderation_actions(payload: ModerationActionRequest):
    """
    Aplica acciones moderación mínimas sobre user/post/comment.
    - user + ban_user/remove → delete_user
    - post + remove          → delete_post
    - comment + remove       → elimina comentario del JSON (inline)
    El resto de acciones son placeholders (lock/sticky/shadowban/approve).
    """

    # USER
    if payload.target_type == TargetType.user:
        if payload.action in {ActionType.ban_user, ActionType.remove}:
            user = get_user_by_id(payload.target_id)
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            delete_user(payload.target_id)
            return ModerationActionResponse(applied=True, detail="Usuario eliminado/baneado")
        # Otros (shadowban, approve...) → placeholder
        return ModerationActionResponse(applied=False, detail=f"Acción {payload.action} no implementada para user")

    # POST
    if payload.target_type == TargetType.post:
        if payload.action == ActionType.remove:
            post = get_post(payload.target_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post no encontrado")
            delete_post(payload.target_id)
            return ModerationActionResponse(applied=True, detail="Post eliminado")
        if payload.action in {ActionType.lock, ActionType.sticky, ActionType.approve, ActionType.shadowban}:
            return ModerationActionResponse(applied=False, detail=f"Acción {payload.action} no implementada para post")
        raise HTTPException(status_code=400, detail=f"Acción {payload.action} inválida para post")

    # COMMENT (inline porque aún no hay service helpers)
    if payload.target_type == TargetType.comment:
        if payload.action == ActionType.remove:
            data = load_data()
            before = len(data.get("comments", []))
            data["comments"] = [c for c in data.get("comments", []) if c.get("id") != payload.target_id]
            after = len(data["comments"])
            if before == after:
                raise HTTPException(status_code=404, detail="Comentario no encontrado")
            save_data(data)
            return ModerationActionResponse(applied=True, detail="Comentario eliminado")
        if payload.action in {ActionType.lock, ActionType.approve, ActionType.shadowban}:
            return ModerationActionResponse(applied=False, detail=f"Acción {payload.action} no implementada para comment")
        raise HTTPException(status_code=400, detail=f"Acción {payload.action} inválida para comment")

    # Fallback imposible por Enum, pero por si acaso:
    raise HTTPException(status_code=400, detail="Target type no soportado")
