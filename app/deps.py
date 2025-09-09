# app/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.utils.security import decode_access_token
from app.services import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decodifica el JWT, obtiene el user_id del 'sub' y retorna el usuario actual
    incluyendo el hash de contraseña (para endpoints como cambio de contraseña).
    """
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise _unauthorized("Token inválido o expirado")

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
        "password": user.get("password"),  # hash
    }
