"""
moderation.py — Endpoints de moderación de KLKCHAN.

Expone herramientas para moderadores y administradores:
- Queue de moderación: lista de contenido reportado pendiente
- Actions: ejecutar acciones sobre usuarios o contenido
- Reports: crear y consultar reportes de contenido

Roles requeridos:
  - GET /moderation/queue    → mod o admin
  - POST /moderation/actions → mod o admin
  - POST /moderation/reports → cualquier usuario autenticado
  - GET /moderation/reports  → mod o admin

Acciones implementadas: remove (post, comment, user) y ban_user (user).
Acciones pendientes (placeholders): approve, lock, sticky, shadowban.
"""
# app/routers/moderation.py
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import require_role
from app.utils.roles import Role
from app.services import (
    get_user,
    delete_user,
    get_post,
    delete_post,
    load_data,
    save_data,
    moderation_queue_list,
)

router = APIRouter(prefix="/moderation", tags=["Moderation"])


# ─────────────────────────── Schemas ───────────────────────────
class TargetType(str, Enum):
    """Tipos de entidades sobre las que se puede aplicar una acción de moderación."""

    user = "user"
    post = "post"
    comment = "comment"


class ActionType(str, Enum):
    """
    Acciones de moderación disponibles.

    Implementadas:
      - remove:    elimina la entidad (user, post o comment).
      - ban_user:  alias de remove para usuarios (misma lógica que remove).

    Pendientes — retornan applied=False sin error:
      - approve:   aprobar contenido reportado.
      - lock:      bloquear nuevos comentarios en un post.
      - sticky:    fijar un post en la parte superior de su board.
      - shadowban: ocultar contenido al resto de usuarios sin notificar al autor.
    """

    remove = "remove"
    approve = "approve"
    lock = "lock"
    sticky = "sticky"
    ban_user = "ban_user"
    shadowban = "shadowban"


class ModerationActionRequest(BaseModel):
    """
    Payload para ejecutar una acción de moderación.

    Attributes:
        target_type: Tipo de entidad afectada (user, post o comment).
        target_id: ID de la entidad afectada (≥ 1).
        action: Acción a aplicar (ver ActionType).
        reason: Motivo de la acción (opcional, para registro).
    """

    target_type: TargetType = Field(..., description="user | post | comment")
    target_id: int = Field(..., ge=1)
    action: ActionType
    reason: Optional[str] = None


class ModerationActionResponse(BaseModel):
    """
    Respuesta de una acción de moderación.

    Attributes:
        applied: True si la acción se ejecutó efectivamente.
                 False si la acción es un placeholder no implementado aún.
        detail: Mensaje descriptivo del resultado.
    """

    applied: bool
    detail: Optional[str] = None


# ─────────────────────────── Queue ─────────────────────────────
@router.get("/queue", dependencies=[Depends(require_role(Role.mod, Role.admin))])
def moderation_queue():
    """
    Lista los reportes de contenido pendientes de revisión.

    Retorna todos los items con status 'pending' en la cola de moderación.
    Solo moderadores y administradores pueden acceder.

    Returns:
        Dict con clave 'items': lista de reportes pendientes. Cada reporte
        incluye id, reporter_id, target_type, target_id, reason y created_at.

    Raises:
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol mod ni admin.
    """
    items = moderation_queue_list(status="pending")
    return {"items": items}


# ──────────────────────── Actions (core) ───────────────────────
@router.post(
    "/actions",
    response_model=ModerationActionResponse,
    dependencies=[Depends(require_role(Role.mod, Role.admin))],
)
def moderation_actions(payload: ModerationActionRequest):
    """
    Aplica una acción de moderación sobre un usuario, post o comentario.

    Las acciones implementadas eliminan la entidad objetivo con cascade delete.
    Las acciones no implementadas retornan applied=False sin lanzar error,
    lo que permite al cliente identificar funcionalidades pendientes.

    Acciones por target_type:
      - user + ban_user/remove → elimina el usuario (cascade: posts, comentarios, votos)
      - user + otras           → applied=False (no implementado)
      - post + remove          → elimina el post (cascade: comentarios, votos)
      - post + lock/sticky/approve/shadowban → applied=False
      - comment + remove       → elimina el comentario (sin cascade a votos del comentario)
      - comment + lock/approve/shadowban     → applied=False
      - comment + ban_user     → 400 (acción inválida para este target_type)

    Args:
        payload: Datos de la acción con target_type, target_id, action y reason opcional.

    Returns:
        ModerationActionResponse con applied (bool) y detail (str).

    Raises:
        HTTPException 400: Si la acción es inválida para el target_type indicado.
        HTTPException 401: Si no se provee un token válido.
        HTTPException 403: Si el usuario no tiene rol mod ni admin.
        HTTPException 404: Si la entidad objetivo no existe.
        HTTPException 500: Si la eliminación falla inesperadamente.

    Notas:
        La eliminación de comentarios es inline (no usa delete_comment() de
        services.py) y NO elimina los votos del comentario. Esto es una
        inconsistencia respecto al cascade delete de DELETE /comments/{id}.
    """

    # USER
    if payload.target_type == TargetType.user:
        if payload.action in {ActionType.ban_user, ActionType.remove}:
            user = get_user(payload.target_id)
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            ok = delete_user(payload.target_id)
            if not ok:
                raise HTTPException(status_code=500, detail="No se pudo eliminar el usuario")
            return ModerationActionResponse(applied=True, detail="Usuario eliminado/baneado")
        return ModerationActionResponse(applied=False, detail=f"Acción {payload.action} no implementada para user")

    # POST
    if payload.target_type == TargetType.post:
        if payload.action == ActionType.remove:
            post = get_post(payload.target_id)
            if not post:
                raise HTTPException(status_code=404, detail="Post no encontrado")
            ok = delete_post(payload.target_id)
            if not ok:
                raise HTTPException(status_code=500, detail="No se pudo eliminar el post")
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

    raise HTTPException(status_code=400, detail="Target type no soportado")
