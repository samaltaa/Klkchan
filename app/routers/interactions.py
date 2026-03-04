"""
interactions.py — Endpoints de interacciones de KLKCHAN.

Gestiona el sistema de votación sobre posts y comentarios.
Los votos usan una escala de tres valores:
  -1 → downvote
   0 → quitar voto (neutro)
   1 → upvote

Un usuario solo puede tener un voto activo por target.
Votar de nuevo con el mismo valor reemplaza el voto anterior.
Votar con value=0 elimina el registro del voto de la base de datos.
"""
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator

from app.deps import get_current_user
from app.schemas import ErrorResponse, VoteSummary
from app.services import apply_vote, get_vote_summary

router = APIRouter(prefix="/interactions", tags=["Interactions"])


class TargetType(str, Enum):
    """Tipos de entidades sobre las que se puede votar."""

    post = "post"
    comment = "comment"


class VoteRequest(BaseModel):
    """
    Payload para emitir un voto.

    Attributes:
        target_type: Tipo de entidad objetivo (post o comment).
        target_id: ID de la entidad a votar (≥ 1).
        value: Valor del voto. -1 downvote, 0 quitar voto, 1 upvote.
    """

    target_type: TargetType
    target_id: int = Field(ge=1)
    value: int

    @field_validator("value")
    @classmethod
    def only_allowed_values(cls, value: int) -> int:
        """Valida que el voto sea -1, 0 o 1."""
        if value not in (-1, 0, 1):
            raise ValueError("Vote value must be -1, 0, or 1")
        return value


@router.post(
    "/votes",
    response_model=VoteSummary,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def cast_vote(
    payload: VoteRequest,
    current_user: dict = Depends(get_current_user),
) -> VoteSummary:
    """
    Emite o retira un voto sobre un post o comentario.

    Si el usuario ya tenía un voto sobre el mismo target, este se reemplaza
    por el nuevo valor. Usar value=0 equivale a quitar el voto (el registro
    se elimina de la base de datos). El endpoint retorna el resumen actualizado
    del target tras aplicar el cambio.

    El campo user_vote en la respuesta refleja el voto activo del usuario
    que realizó la petición (-1, 0 o 1).

    Args:
        payload: Datos del voto con target_type, target_id y value.
        current_user: Usuario autenticado (inyectado por get_current_user).

    Returns:
        VoteSummary con target_type, target_id, score (upvotes - downvotes),
        upvotes, downvotes y user_vote (voto activo del usuario actual).

    Raises:
        HTTPException 400: Si value no es -1, 0 o 1 (validado por schema).
        HTTPException 401: Si no se provee un token válido.
        HTTPException 404: Si el target (post o comment) no existe.
    """
    try:
        result = apply_vote(
            user_id=current_user["id"],
            target_type=payload.target_type.value,
            target_id=payload.target_id,
            value=payload.value,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "target_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    result["user_vote"] = result.pop("value")
    return VoteSummary(**result)


@router.get(
    "/votes/{target_type}/{target_id}",
    response_model=VoteSummary,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def read_vote_summary(target_type: TargetType, target_id: int = Path(..., ge=1)) -> VoteSummary:
    """
    Retorna el resumen de votos de un post o comentario.

    Endpoint público — no requiere autenticación. El campo user_vote
    siempre es null en este endpoint ya que no hay usuario identificado.
    Para obtener user_vote personalizado, el cliente debe llamar a
    POST /interactions/votes con el token del usuario.

    Args:
        target_type: Tipo de entidad (post o comment).
        target_id: ID de la entidad (≥ 1).

    Returns:
        VoteSummary con score (upvotes - downvotes), upvotes, downvotes
        y user_vote=null.

    Raises:
        HTTPException 404: Si el target no existe.
    """
    summary = get_vote_summary(target_type.value, target_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return VoteSummary(**summary)
