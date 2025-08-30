# app/routers/Auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Optional
from fastapi import Security
from app.deps import oauth2_scheme

from app.schemas import UserCreate, UserResponse, Token
from app.utils.security import hash_password, verify_password, create_access_token
from app.services import get_users, create_user as service_create_user

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 30

def find_user_by_username(username: str) -> Optional[dict]:
    # Tus services devuelven estructuras dict desde data.json
    users = get_users()
    for u in users:
        if u["username"] == username:
            return u
    return None

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate):
    # Verifica unicidad simple
    if find_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username ya existe")

    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["posts"] = []

    created = service_create_user(user_dict)
    # Mapea solo campos públicos a UserResponse
    return {
        "id": created["id"],
        "username": created["username"],
        "email": created["email"],
        "posts": created.get("posts", []),
    }

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Nota: OAuth2PasswordRequestForm trae `username` y `password`
    user = find_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}



from app.deps import oauth2_scheme  # ⬅️ importa el esquema

@router.get("/_auth_probe")
async def _auth_probe(token: str = Depends(oauth2_scheme)):
    # Esta ruta fuerza a incluir el esquema en OpenAPI.
    return {"ok": True}

