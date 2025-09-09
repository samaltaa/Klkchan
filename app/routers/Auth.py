# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional

from app.schemas import UserCreate, UserResponse, Token, ChangePasswordRequest
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    check_password_policy,
)
from app.services import (
    get_users,
    create_user as service_create_user,
    get_user_by_email,
)
from app.utils.helpers import normalize_email
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

ACCESS_TOKEN_EXPIRE_MINUTES = 30


def find_user_by_username(username: str) -> Optional[dict]:
    for u in get_users():
        if u.get("username") == username:
            return u
    return None


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate):
    email = normalize_email(user.email)
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email ya existe")
    if find_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username ya existe")

    user_dict = user.dict()
    user_dict["email"] = email
    user_dict["password"] = hash_password(user.password)
    user_dict["posts"] = []

    created = service_create_user(user_dict)
    return {
        "id": created["id"],
        "username": created["username"],
        "email": created["email"],
        "posts": created.get("posts", []),
    }


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    En Swagger, el campo 'username' representa el EMAIL.
    """
    email = normalize_email(form_data.username)
    user = get_user_by_email(email)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )

    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.patch("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest, current_user: dict = Depends(get_current_user)
):
    """
    Cambia la contraseña del usuario autenticado.
    Retorna 204 No Content si todo sale bien.
    """
    # ⬇️ Import diferido para evitar import circular / símbolos aún no cargados
    from app.services import update_user_password  # type: ignore

    try:
        stored_hash = current_user.get("password")
        if not stored_hash:
            raise HTTPException(
                status_code=500, detail="No se encontró la contraseña actual."
            )

        # 1) validar actual
        if not verify_password(payload.old_password, stored_hash):
            raise HTTPException(
                status_code=400, detail="Contraseña actual incorrecta."
            )

        # 2) política
        ok, msg = check_password_policy(payload.new_password)
        if not ok:
            raise HTTPException(status_code=422, detail=msg)

        # 3) evitar repetir
        if verify_password(payload.new_password, stored_hash):
            raise HTTPException(
                status_code=400,
                detail="La nueva contraseña no puede ser igual a la anterior.",
            )

        # 4) guardar nuevo hash
        new_hash = hash_password(payload.new_password)
        if not update_user_password(current_user["id"], new_hash):
            raise HTTPException(
                status_code=500,
                detail="No se pudo actualizar la contraseña (update_user_password=False).",
            )

        return  # 204
    except HTTPException:
        raise
    except Exception as e:
        # Para depuración: muestra el motivo real del 500 en Swagger
        raise HTTPException(
            status_code=500, detail=f"change-password error: {type(e).__name__}: {e}"
        )


@router.get("/_auth_probe")
def _auth_probe():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}
