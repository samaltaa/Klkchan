# app/deps.py
from typing import Any, Dict, Sequence
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.utils.security import decode_access_token
from app.services import get_user_by_id
from app.utils.roles import Role  


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_payload(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Valida y decodifica el access token. Devuelve el payload crudo.
    Espera al menos: {'sub': <user_id>, 'exp': ..., 'roles': [...], 'scopes': [...]}
    """
    try:
        payload = decode_access_token(token)
    except Exception:
        raise _unauthorized("Token inválido o expirado")

    if not isinstance(payload, dict) or "sub" not in payload:
        raise _unauthorized("Token inválido")

    return payload


async def get_current_user(payload: Dict[str, Any] = Depends(get_current_payload)) -> Dict[str, Any]:
    """
    Obtiene el usuario actual desde el storage a partir de payload['sub'].
    NO expone el hash de contraseña.
    """
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido")

    user = get_user_by_id(user_id)
    if not user:
        raise _unauthorized("Usuario no encontrado")

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "posts": user.get("posts", []),
        "roles": payload.get("roles", ["user"]),
        "scopes": payload.get("scopes", []),
    }


def require_role(*accepted: Role):
    """
    Guard de autorización por rol. Ejemplo de uso:
    @router.get("/admin", dependencies=[Depends(require_role(Role.admin))])
    """
    accepted_values = {r.value if isinstance(r, Role) else str(r) for r in accepted}

    def dep(user: Dict[str, Any] = Depends(get_current_user)):
        roles = set(user.get("roles", []))
        if roles.isdisjoint(accepted_values):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dep


def require_scopes(required: Sequence[str]):
    """
    Guard por scopes granulares. Ejemplo:
    @router.get("/x", dependencies=[Depends(require_scopes(['mod']))])
    """
    required_set = set(required)

    def dep(user: Dict[str, Any] = Depends(get_current_user)):
        scopes = set(user.get("scopes", []))
        missing = [s for s in required_set if s not in scopes]
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing scopes: {missing}")
        return user

    return dep
