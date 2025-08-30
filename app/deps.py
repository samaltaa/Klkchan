# app/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.utils.security import decode_access_token
from app.services import get_users

print("IMPORTANDO deps.py OK")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/Auth/login")

def _find_user_by_username(username: str) -> Optional[dict]:
    for u in get_users():
        if u["username"] == username:
            return u
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    user = _find_user_by_username(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

  
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "posts": user.get("posts", []),
    }
