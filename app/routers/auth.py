from datetime import timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

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
    check_password_policy,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.services import (
    create_user as service_create_user,
    get_user_by_email,
    get_user_by_id,
    get_users,
    update_user_password,
)
from app.utils.helpers import normalize_email
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

ACCESS_TOKEN_EXPIRE_MINUTES = 30


def find_user_by_username(username: str) -> Optional[dict]:
    for user in get_users():
        if user.get("username") == username:
            return user
    return None


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate) -> UserResponse:
    email = normalize_email(user.email)

    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already exists")

    if find_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    user_dict = user.model_dump()
    user_dict["email"] = email
    user_dict["password"] = hash_password(user.password)
    user_dict["posts"] = []

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
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenPair:
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
def refresh_tokens(payload: RefreshTokenRequest) -> TokenPair:
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
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> Response:
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

        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"change-password error: {type(exc).__name__}: {exc}")


@router.post("/logout", response_model=LogoutResponse)
def logout(current_user: dict = Depends(get_current_user)) -> LogoutResponse:
    _ = current_user
    return LogoutResponse()


@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=202)
def forgot_password(body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    _ = body
    return ForgotPasswordResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(body: ResetPasswordRequest) -> ResetPasswordResponse:
    _ = body
    return ResetPasswordResponse()


@router.post("/verify-email", status_code=status.HTTP_202_ACCEPTED)
def verify_email(payload: VerifyEmailRequest):
    _ = payload
    return {"accepted": True, "detail": "Email verification stub", "next": "MODEL-32"}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(payload: ResendVerificationRequest):
    _ = payload
    return {"accepted": True, "detail": "Resend verification stub", "next": "MODEL-32"}


@router.get("/_auth_probe")
def _auth_probe():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}
