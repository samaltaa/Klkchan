# app/utils/security.py
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any

from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
ISSUER = os.getenv("JWT_ISS", "klkchan")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------- Password hashing ----------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def check_password_policy(pwd: str) -> Tuple[bool, Optional[str]]:
    """
    Política mínima:
      - >= 8 caracteres
      - >= 1 mayúscula, 1 minúscula, 1 dígito
    Retorna (ok, msg_error)
    """
    if len(pwd) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", pwd):
        return False, "Debe contener al menos una letra mayúscula."
    if not re.search(r"[a-z]", pwd):
        return False, "Debe contener al menos una letra minúscula."
    if not re.search(r"[0-9]", pwd):
        return False, "Debe contener al menos un dígito."
    return True, None


# ---------------- JWT helpers ----------------
def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Firma un JWT con iat/nbf/exp como timestamps (int).
    Añade defaults para roles y scopes si no vienen en data.
    """
    now = _now_ts()
    ttl = int(expires_delta.total_seconds()) if expires_delta else ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload: Dict[str, Any] = {
        "iss": ISSUER,
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        **data,
    }
    payload.setdefault("roles", ["user"])
    payload.setdefault("scopes", [])

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida firma/exp/nbf. Lanza JWTError si es inválido.
    """
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_aud": False},
        issuer=ISSUER,
    )


# ---------------- Refresh tokens ----------------
def create_refresh_token(user_id: int) -> Tuple[str, str, int]:
    """
    Retorna: (token, jti, exp_ts)
    """
    jti = str(uuid.uuid4())
    now = _now_ts()
    exp_ts = now + int(timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
    payload = {
        "iss": ISSUER,
        "sub": str(user_id),
        "typ": "refresh",
        "jti": jti,
        "iat": now,
        "nbf": now,
        "exp": exp_ts,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, exp_ts


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida refresh. Lanza JWTError si falla o si typ != 'refresh'.
    """
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_aud": False},
        issuer=ISSUER,
    )
    if payload.get("typ") != "refresh":
        raise JWTError("Invalid token type")
    return payload
