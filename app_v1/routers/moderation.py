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

from app_v1.deps import require_role
from app_v1.utils.roles import Role
from app_v1.services import (
    get_user,
    delete_user,
    ban_user,
    get_post,
    delete_post,
    get_comment,
    delete_comment,
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
      - comment + remove       → elimina el comentario (cascade: votos del comentario)
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
        Los replies huérfanos tras eliminar un comentario raíz son promovidos
        a nivel raíz por build_comment_tree() en las respuestas de lectura.
    """

    # USER
    if payload.target_type == TargetType.user:
        if payload.action == ActionType.ban_user:
            user = get_user(payload.target_id)
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            result = ban_user(payload.target_id)
            if not result:
                raise HTTPException(status_code=500, detail="No se pudo suspender el usuario")
            return ModerationActionResponse(applied=True, detail="Usuario suspendido correctamente")
        if payload.action == ActionType.remove:
            user = get_user(payload.target_id)
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            ok = delete_user(payload.target_id)
            if not ok:
                raise HTTPException(status_code=500, detail="No se pudo eliminar el usuario")
            return ModerationActionResponse(applied=True, detail="Usuario eliminado")
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

    # COMMENT
    if payload.target_type == TargetType.comment:
        if payload.action == ActionType.remove:
            comment = get_comment(payload.target_id)
            if not comment:
                raise HTTPException(status_code=404, detail="Comentario no encontrado")
            ok = delete_comment(payload.target_id)
            if not ok:
                raise HTTPException(status_code=500, detail="No se pudo eliminar el comentario")
            return ModerationActionResponse(applied=True, detail="Comentario eliminado")
        if payload.action in {ActionType.lock, ActionType.approve, ActionType.shadowban}:
            return ModerationActionResponse(applied=False, detail=f"Acción {payload.action} no implementada para comment")
        raise HTTPException(status_code=400, detail=f"Acción {payload.action} inválida para comment")

    raise HTTPException(status_code=400, detail="Target type no soportado")
