"""
terms.py — Router de Términos y Condiciones — KLKCHAN.

Expone los endpoints para consultar, aceptar y verificar el estado de
aceptación de los Términos y Condiciones del servicio.

Endpoints:
  GET  /terms/latest  → versión activa de los T&C (público, 404 si no existe).
  POST /terms/accept  → acepta los T&C vigentes (requiere JWT, idempotente).
  GET  /terms/status  → estado de aceptación del usuario autenticado.
"""
# app/routers/terms.py
from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import HTTPException

from app.deps import get_current_user
from app.schemas.schemas import TermsOut, TermsStatusOut
from app.services import (
    create_acceptance,
    get_active_terms,
    get_user_acceptance,
    has_accepted_current_terms,
)

router = APIRouter(prefix="/terms", tags=["Terms"])


@router.get(
    "/latest",
    response_model=TermsOut,
    summary="Obtener versión activa de los T&C",
)
def get_latest_terms():
    """
    Retorna los Términos y Condiciones actualmente vigentes.

    Endpoint público (no requiere autenticación). Útil para mostrar
    el enlace a los T&C antes de que el usuario se registre o acepte.

    Returns:
        TermsOut con los datos de la versión activa.

    Raises:
        HTTPException 404: Si no hay ninguna versión activa de los T&C.
    """
    active = get_active_terms()
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay términos y condiciones activos.",
        )
    return active


@router.post(
    "/accept",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Aceptar los T&C vigentes",
)
def accept_terms(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Registra la aceptación de los Términos y Condiciones por parte del usuario.

    Es idempotente: si el usuario ya aceptó la versión vigente, retorna 204
    sin crear un registro duplicado.

    La dirección IP se extrae del request para el registro de auditoría.

    Args:
        request: Request de FastAPI para obtener la IP del cliente.
        current_user: Usuario autenticado inyectado por get_current_user.

    Raises:
        HTTPException 404: Si no hay T&C activos que aceptar.
    """
    active = get_active_terms()
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay términos y condiciones activos.",
        )

    # Verificar si ya aceptó (idempotencia explícita antes de crear)
    existing = get_user_acceptance(current_user["id"], active["id"])
    if existing:
        return  # 204 sin duplicar

    # Extraer IP del cliente (considera proxies vía X-Forwarded-For)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    create_acceptance(
        user_id=current_user["id"],
        terms_id=active["id"],
        ip_address=ip_address,
    )


@router.get(
    "/status",
    response_model=TermsStatusOut,
    summary="Estado de aceptación de T&C del usuario",
)
def get_terms_status(current_user: dict = Depends(get_current_user)):
    """
    Retorna si el usuario autenticado ha aceptado la versión vigente de los T&C.

    Útil para que el frontend decida si debe mostrar el banner/modal de aceptación
    antes de permitir acciones protegidas.

    Args:
        current_user: Usuario autenticado inyectado por get_current_user.

    Returns:
        TermsStatusOut con up_to_date=True si el usuario está al día,
        y current_version con la versión activa (o None si no hay T&C activos).
    """
    active = get_active_terms()
    if not active:
        return TermsStatusOut(up_to_date=True, current_version=None)

    accepted = get_user_acceptance(current_user["id"], active["id"]) is not None
    return TermsStatusOut(up_to_date=accepted, current_version=active["version"])
