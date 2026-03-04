"""
auth.py — Endpoints de autenticación de KLKCHAN.

Gestiona el ciclo completo de identidad del usuario:
registro, login, refresh de tokens, cambio y reset de
contraseña, y logout.

Flujo de tokens:
  - Login genera un par access token (15 min) + refresh token (7 días).
  - El access token se envía en cada request autenticado
    (header Authorization: Bearer <token>).
  - El refresh token permite obtener un nuevo par sin volver a loguearse.
  - Logout y change-password revocan el access token activo (blacklist).
  - Reset-password revoca TODOS los tokens activos del usuario mediante
    iat_cutoff: cualquier token emitido antes del reset queda invalidado.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.utils.limiter import limiter

from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LogoutResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ResendVerificationRequest,
    TokenPair,
    UserCreate,
    UserResponse,
    VerifyEmailRequest,
)
from app.utils.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    check_password_policy,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.services import (
    create_user as service_create_user,
    get_user_by_email,
    get_user_by_id,
    get_users,
    update_user_iat_cutoff,
    update_user_password,
)
from app.utils.helpers import normalize_email
from app.deps import get_current_payload, get_current_user
from app.utils.token_blacklist import is_revoked, revoke as revoke_token

router = APIRouter(prefix="/auth", tags=["Auth"])


def _assign_initial_roles(email: str) -> List[str]:
    """
    Determina los roles iniciales de un usuario recién registrado.

    Lee las variables de entorno ADMIN_EMAILS y MOD_EMAILS (listas
    separadas por comas) en tiempo de ejecución. Si el email del nuevo
    usuario aparece en ADMIN_EMAILS, recibe el rol "admin"; si aparece
    en MOD_EMAILS, recibe "mod". En cualquier otro caso, solo "user".
    La comparación es case-insensitive.

    Args:
        email: Email normalizado (lowercase, sin espacios) del usuario.

    Returns:
        Lista de roles. Siempre incluye "user". Puede incluir "admin"
        o "mod" dependiendo de la configuración del entorno.
    """
    admin_emails = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    mod_emails = [e.strip().lower() for e in os.getenv("MOD_EMAILS", "").split(",") if e.strip()]

    roles: List[str] = ["user"]
    normalized = email.strip().lower()
    if normalized in admin_emails:
        roles.append("admin")
    elif normalized in mod_emails:
        roles.append("mod")
    return roles


def find_user_by_username(username: str) -> Optional[dict]:
    """
    Busca un usuario por username (comparación exacta, case-sensitive).

    Escanea todos los usuarios del sistema. Se usa en el registro para
    detectar duplicados de username antes de crear el nuevo usuario.

    Args:
        username: Nombre de usuario exacto a buscar.

    Returns:
        Dict del usuario si existe, None si no se encuentra.
    """
    for user in get_users():
        if user.get("username") == username:
            return user
    return None


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
def register(request: Request, user: UserCreate) -> UserResponse:
    """
    Registra un nuevo usuario en el sistema.

    Valida que el email y el username no estén en uso, hashea la contraseña,
    asigna roles iniciales según ADMIN_EMAILS/MOD_EMAILS y persiste el usuario.
    La contraseña debe cumplir la política: mínimo 8 caracteres, al menos
    una mayúscula y un dígito (validado por el schema UserCreate).

    Args:
        request: Request de FastAPI (requerido por el rate limiter).
        user: Datos del nuevo usuario (username, email, password).

    Returns:
        UserResponse con id, username, email y posts (lista vacía).

    Raises:
        HTTPException 400: Si el email ya está registrado.
        HTTPException 400: Si el username ya está en uso.
        HTTPException 422: Si la contraseña no cumple la política.
        HTTPException 429: Si se supera el límite de 10 registros/minuto.
    """
    email = normalize_email(user.email)

    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already exists")

    if find_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    user_dict = user.model_dump()
    user_dict["email"] = email
    user_dict["password"] = hash_password(user.password)
    user_dict["posts"] = []
    user_dict["roles"] = _assign_initial_roles(email)

    created = service_create_user(user_dict)

    return UserResponse(
        id=created["id"],
        username=created["username"],
        email=created["email"],
        posts=created.get("posts", []),
    )


@router.post(
    "/login",
    response_model=TokenPair,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"}},
)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> TokenPair:
    """
    Autentica un usuario y genera un par de tokens de acceso.

    Acepta el campo username del formulario OAuth2 como email
    (el campo se llama username por convención OAuth2 pero se
    trata internamente como email, normalizando antes de buscar).

    Genera:
    - access_token: JWT de corta duración (ACCESS_TOKEN_EXPIRE_MINUTES).
      Contiene sub (user_id como string) y roles.
    - refresh_token: JWT de larga duración (7 días) para renovar el par.
    - expires_in: Segundos de vida del access token.

    Args:
        request: Request de FastAPI (requerido por el rate limiter).
        form_data: Formulario OAuth2 con username (email) y password.

    Returns:
        TokenPair con access_token, refresh_token y expires_in.

    Raises:
        HTTPException 401: Si el email no existe o la contraseña es incorrecta.
        HTTPException 429: Si se supera el límite de 10 logins/minuto.
    """
    email = normalize_email(form_data.username)
    user = get_user_by_email(email)

    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    roles = user.get("roles", ["user"])
    access_token = create_access_token(
        data={"sub": str(user["id"]), "roles": roles},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token, _refresh_jti, _refresh_exp = create_refresh_token(user_id=user["id"])
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Invalid refresh token"}},
)
@limiter.limit("20/minute")
def refresh_tokens(request: Request, payload: RefreshTokenRequest) -> TokenPair:
    """
    Renueva el par de tokens usando un refresh token válido.

    Verifica que el refresh token tenga tipo "refresh", que la firma sea
    correcta y que el usuario referenciado en el campo sub siga existiendo.
    Si todo es válido, emite un nuevo access token y un nuevo refresh token
    (rotación de refresh token).

    Nota: los refresh tokens revocados (p. ej. tras logout) NO son
    verificados aquí porque la blacklist actual solo cubre access tokens.
    En producción se debería añadir verificación del jti del refresh token.

    Args:
        request: Request de FastAPI (requerido por el rate limiter).
        payload: Objeto con el campo refresh_token (string JWT).

    Returns:
        TokenPair con el nuevo access_token, nuevo refresh_token y expires_in.

    Raises:
        HTTPException 401: Si el refresh token es inválido, expirado o
                           si el usuario asociado no existe.
        HTTPException 429: Si se supera el límite de 20 refresh/minuto.
    """
    try:
        refresh_payload = decode_refresh_token(payload.refresh_token)
    except Exception:  # pragma: no cover - jose raises JWTError
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = refresh_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = get_user_by_id(user_id_int)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    roles = user.get("roles", ["user"])
    access_token = create_access_token(
        data={"sub": str(user_id_int), "roles": roles},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token, _refresh_jti, _refresh_exp = create_refresh_token(user_id=user_id_int)
    return TokenPair(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.patch("/change-password", status_code=204)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    token_payload: dict = Depends(get_current_payload),
) -> Response:
    """
    Cambia la contraseña del usuario autenticado.

    Requiere la contraseña actual para confirmar la identidad. Tras el
    cambio exitoso, revoca el access token activo (lo añade a la blacklist)
    para forzar un nuevo login. El cliente debe descartar ambos tokens y
    volver a autenticarse.

    Validaciones:
    1. El usuario sigue existiendo en la base de datos.
    2. La contraseña actual es correcta (verify_password).
    3. La nueva contraseña cumple la política (mayúscula + dígito + ≥8 chars).
    4. La nueva contraseña es diferente de la actual.

    Args:
        request: Request de FastAPI (requerido por el rate limiter).
        payload: Objeto con old_password y new_password.
        current_user: Usuario autenticado (inyectado por get_current_user).
        token_payload: Claims del JWT activo (inyectado por get_current_payload).

    Returns:
        Respuesta vacía 204 No Content si el cambio fue exitoso.

    Raises:
        HTTPException 400: Si la contraseña actual es incorrecta.
        HTTPException 400: Si la nueva contraseña es igual a la actual.
        HTTPException 422: Si la nueva contraseña no cumple la política.
        HTTPException 429: Si se supera el límite de 5 cambios/minuto.
        HTTPException 500: Si la actualización falla inesperadamente.
    """
    try:
        db_user = get_user_by_id(current_user["id"])
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        stored_hash = db_user.get("password")
        if not stored_hash:
            raise HTTPException(status_code=500, detail="Missing password hash")

        if not verify_password(payload.old_password, stored_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        ok, msg = check_password_policy(payload.new_password)
        if not ok:
            raise HTTPException(status_code=422, detail=msg)

        if verify_password(payload.new_password, stored_hash):
            raise HTTPException(
                status_code=400,
                detail="New password cannot match the current password.",
            )

        new_hash = hash_password(payload.new_password)
        if not update_user_password(db_user["id"], new_hash):
            raise HTTPException(status_code=500, detail="Password update failed")

        # Revoke the current access token so the client must re-login
        jti = token_payload.get("jti")
        exp = token_payload.get("exp", 0)
        if jti:
            revoke_token(jti, float(exp))

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"change-password error: {type(exc).__name__}: {exc}")


@router.post("/logout", response_model=LogoutResponse)
def logout(
    token_payload: dict = Depends(get_current_payload),
    current_user: dict = Depends(get_current_user),
) -> LogoutResponse:
    """
    Cierra la sesión del usuario revocando el access token activo.

    Extrae el jti (JWT ID único) del token y lo añade a la blacklist
    hasta que expire naturalmente. Cualquier request posterior con ese
    mismo token recibirá 401. El refresh token NO es revocado en este
    endpoint (limitación actual).

    Args:
        token_payload: Claims del JWT activo (inyectado por get_current_payload).
        current_user: Usuario autenticado (inyectado por get_current_user,
                      requerido para validar que el token es válido).

    Returns:
        LogoutResponse con message="Sesión cerrada correctamente." (200 OK).

    Raises:
        HTTPException 401: Si el token no es válido o ya fue revocado.
    """
    _ = current_user
    jti = token_payload.get("jti")
    exp = token_payload.get("exp", 0)
    if jti:
        revoke_token(jti, float(exp))
    return LogoutResponse()


@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=202)
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """
    Inicia el flujo de recuperación de contraseña.

    Si el email está registrado, genera un token JWT de uso único
    (tipo "reset", firmado, con expiración corta) para el usuario.
    Siempre retorna 202 independientemente de si el email existe o no,
    para evitar enumerar usuarios registrados (timing-safe response).

    IMPORTANTE — Estado actual (MVP):
    El reset_token se devuelve directamente en la respuesta JSON.
    En producción, este token debe enviarse por email al usuario y
    el campo reset_token de la respuesta debe ser null siempre.
    Ver TODO en el código (integración de email pendiente: MODEL-32).

    Args:
        request: Request de FastAPI (requerido por el rate limiter).
        body: Objeto con el campo email del usuario.

    Returns:
        ForgotPasswordResponse con reset_token (string JWT) si el email
        existe, o reset_token=null si no existe. Siempre 202 Accepted.

    Raises:
        HTTPException 429: Si se supera el límite de 5 solicitudes/minuto.
    """
    email = normalize_email(body.email)
    user = get_user_by_email(email)

    reset_token = None
    if user:
        token, _jti, _exp_ts = create_password_reset_token(user["id"])
        reset_token = token  # TODO: enviar por email en producción, no retornar aquí

    # Siempre retorna 202 — no revelar si el email está registrado
    return ForgotPasswordResponse(reset_token=reset_token)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(body: ResetPasswordRequest) -> ResetPasswordResponse:
    """
    Completa el reset de contraseña usando el token de un solo uso.

    Flujo completo:
    1. Verifica firma y expiración del token JWT de reset.
    2. Verifica que el jti del token no esté en la blacklist (uso único).
    3. Valida que el usuario referenciado siga existiendo.
    4. Verifica la política de contraseña (mayúscula + dígito + ≥8 chars).
    5. Actualiza el hash de contraseña en la base de datos.
    6. Establece iat_cutoff = ahora → TODOS los tokens activos del usuario
       quedan invalidados (sesiones revocadas en todas las instancias).
    7. Consume el token de reset añadiendo su jti a la blacklist.

    El token de reset se obtiene previamente llamando a POST /auth/forgot-password.

    Args:
        body: Objeto con token (JWT de reset) y new_password.

    Returns:
        ResetPasswordResponse con message="Contraseña restablecida." (200 OK).

    Raises:
        HTTPException 400: Si el token es inválido, expirado o ya fue utilizado.
        HTTPException 404: Si el usuario referenciado en el token no existe.
        HTTPException 422: Si la nueva contraseña no cumple la política.
    """
    try:
        payload = decode_password_reset_token(body.token)
    except Exception:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    jti = payload.get("jti")
    if jti and is_revoked(jti):
        raise HTTPException(status_code=400, detail="Token ya utilizado")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Token inválido")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    ok, msg = check_password_policy(body.new_password)
    if not ok:
        raise HTTPException(status_code=422, detail=msg)

    new_hash = hash_password(body.new_password)
    update_user_password(user_id, new_hash)

    # Invalidar todas las sesiones activas del usuario
    cutoff_ts = int(datetime.now(timezone.utc).timestamp())
    update_user_iat_cutoff(user_id, cutoff_ts)

    # Consumir el token (uso único)
    if jti:
        revoke_token(jti, float(payload.get("exp", 0)))

    return ResetPasswordResponse()


@router.post("/verify-email", status_code=status.HTTP_202_ACCEPTED)
def verify_email(payload: VerifyEmailRequest):
    """
    Stub: verifica el email de un usuario mediante un token de confirmación.

    PENDIENTE — No implementado. Siempre retorna 202 Accepted.
    La implementación real está planificada en MODEL-32 (integración de email).

    Args:
        payload: Objeto con el token de verificación de email.

    Returns:
        Dict con accepted=True y detail indicando que es un stub.
    """
    _ = payload
    return {"accepted": True, "detail": "Email verification stub", "next": "MODEL-32"}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(payload: ResendVerificationRequest):
    """
    Stub: reenvía el email de verificación de cuenta.

    PENDIENTE — No implementado. Siempre retorna 202 Accepted.
    La implementación real está planificada en MODEL-32 (integración de email).

    Args:
        payload: Objeto con el email al que reenviar la verificación.

    Returns:
        Dict con accepted=True y detail indicando que es un stub.
    """
    _ = payload
    return {"accepted": True, "detail": "Resend verification stub", "next": "MODEL-32"}

