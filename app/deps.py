# app/deps.py
from typing import Any, Dict, Sequence
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError  # ✅ captura explícita de errores JWT

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
    except JWTError:
        raise _unauthorized("Token inválido o expirado")
    except Exception:
        # Fallback por si decode_access_token cambia la excepción
        raise _unauthorized("Token inválido")

    if not isinstance(payload, dict) or "sub" not in payload:
        raise _unauthorized("Token inválido")

    return payload


async def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_payload),
) -> Dict[str, Any]:
    """
    Obtiene el usuario actual desde el storage a partir de payload['sub'].
    NO expone el hash de contraseña. Adjunta roles/scopes desde el token.
    """
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido")

    user = get_user_by_id(user_id)
    if not user:
        raise _unauthorized("Usuario no encontrado")

    # roles y scopes vienen del JWT; default ya lo pone create_access_token
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
    Guard de autorización por rol (case-insensitive).
    Uso típico:
      @router.get("/x", dependencies=[Depends(require_role(Role.mod, Role.admin))])
    """
    # accepted puede traer Enum Role o strings; los normalizamos a str lower
    accepted_values_lc = {
        (r.value if isinstance(r, Role) else str(r)).lower() for r in accepted
    }

    def dep(user: Dict[str, Any] = Depends(get_current_user)):
        roles = user.get("roles", [])
        roles_lc = {str(r).lower() for r in roles}
        if roles_lc.isdisjoint(accepted_values_lc):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dep


def require_scopes(required: Sequence[str]):
    """
    Guard por scopes granulares.
    Ejemplo:
      @router.get("/x", dependencies=[Depends(require_scopes(['mod']))])
    """
    required_set = {str(s).lower() for s in required}

    def dep(user: Dict[str, Any] = Depends(get_current_user)):
        scopes = {str(s).lower() for s in user.get("scopes", [])}
        missing = [s for s in required_set if s not in scopes]
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing scopes: {missing}")
        return user

    return dep
