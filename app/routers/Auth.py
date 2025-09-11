# app/routers/auth.py
from datetime import timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.schemas import (
    UserCreate, UserResponse, Token, ChangePasswordRequest,
    LogoutResponse, ForgotPasswordRequest, ResetPasswordRequest
)
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
    get_user_by_id,             
    update_user_password,     
)
from app.utils.helpers import normalize_email
from app.deps import get_current_user   # Debe devolver al menos {"id": int}

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

    # Pydantic v2 → model_dump()
    user_dict = user.model_dump()
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.patch("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Cambia la contraseña del usuario autenticado.
    Retorna 204 No Content si todo sale bien.
    """
    try:
        # 0) Relee el usuario REAL desde la “DB” por id
        db_user = get_user_by_id(current_user["id"])
        if not db_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        stored_hash = db_user.get("password")
        if not stored_hash:
            raise HTTPException(status_code=500, detail="No se encontró el hash actual.")

        # 1) validar actual
        if not verify_password(payload.old_password, stored_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta.")

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
        if not update_user_password(db_user["id"], new_hash):
            raise HTTPException(
                status_code=500,
                detail="No se pudo actualizar la contraseña (update_user_password=False).",
            )

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"change-password error: {type(e).__name__}: {e}"
        )


# ────────────── LOGOUT ──────────────
@router.post("/logout", response_model=LogoutResponse)
def logout(current_user: dict = Depends(get_current_user)):
    """
    Revoca el access token actual (si implementas blacklist) y/o limpia cookies.
    """
    # TODO:
    # - Si usas cookies HttpOnly: setear expiración pasada en access/refresh.
    # - Si usas blacklist/Redis: revocar jti del token actual.
    return LogoutResponse()


# ─────────── FORGOT PASSWORD (cascarón) ─────────
@router.post("/forgot-password", status_code=204)
def forgot_password(body: ForgotPasswordRequest):
    """
    Envía instrucciones de reseteo si el email existe.
    Devolvemos 204 para no revelar existencia del usuario.
    """
    # TODO:
    # - Buscar usuario por email (silencioso).
    # - Generar reset token (JWT con scope reset:password).
    # - Enviar email con link/ token.
    return Response(status_code=204)


# ─────────── RESET PASSWORD (cascarón) ──────────
@router.post("/reset-password", status_code=200)
def reset_password(body: ResetPasswordRequest):
    """
    Consume el token de reset y establece nueva contraseña.
    """
    # TODO:
    # - Decodificar/validar token (scope reset:password, exp, jti, issuer).
    # - Aplicar política de contraseña.
    # - Guardar nuevo hash.
    # - Invalidar sesiones previas si aplica.
    return {"detail": "Password updated"}


@router.get("/_auth_probe")
def _auth_probe():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}
