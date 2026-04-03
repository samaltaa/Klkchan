"""
security.py — Utilidades de seguridad JWT y hashing — KLKCHAN.

Gestiona la creación, decodificación y validación de tokens JWT,
y el hashing de contraseñas con bcrypt.

Tipos de token:
  - access:         autenticación de requests (corta duración, default 15 min).
  - refresh:        renovación del access token (larga duración, default 7 días).
  - password_reset: reset de contraseña de un solo uso (1 hora).

Configuración por variables de entorno (.env):
  SECRET_KEY                   — clave HMAC (requerida, sin fallback).
  ALGORITHM                    — algoritmo JWT (default: HS256).
  ACCESS_TOKEN_EXPIRE_MINUTES  — TTL access token en minutos (default: 15).
  REFRESH_TOKEN_EXPIRE_DAYS    — TTL refresh token en días (default: 7).
  JWT_ISS                      — claim issuer (default: "klkchan").
"""
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

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is required. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
ISSUER = os.getenv("JWT_ISS", "klkchan")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------- Password hashing ----------------
def hash_password(password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña en texto plano.

    Args:
        password: Contraseña en texto plano.

    Returns:
        Hash bcrypt listo para almacenar en la BD.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que una contraseña en texto plano coincide con su hash.

    Args:
        plain_password: Contraseña candidata en texto plano.
        hashed_password: Hash bcrypt almacenado en la BD.

    Returns:
        True si la contraseña es correcta, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def check_password_policy(pwd: str) -> Tuple[bool, Optional[str]]:
    """
    Valida que la contraseña cumpla la política mínima de seguridad.

    Política:
      - Mínimo 8 caracteres
      - Al menos 1 letra mayúscula
      - Al menos 1 letra minúscula
      - Al menos 1 dígito

    Args:
        pwd: Contraseña a validar.

    Returns:
        Tupla (ok, msg_error): ok=True si cumple la política,
        ok=False con msg_error describiendo el primer requisito
        no cumplido.
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
    """Retorna el timestamp Unix actual en segundos (UTC)."""
    return int(datetime.now(timezone.utc).timestamp())


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea y firma un access token JWT con los datos del usuario.

    Incluye automáticamente: iss, jti (UUID v4), iat, nbf, exp.
    Si data no incluye 'roles' o 'scopes', se asignan defaults
    (['user'] y [] respectivamente).

    Args:
        data: Payload del token. Debe incluir al menos 'sub' (user_id str).
              Puede incluir 'roles', 'scopes' y cualquier claim adicional.
        expires_delta: TTL personalizado. Si se omite, usa
                       ACCESS_TOKEN_EXPIRE_MINUTES del entorno.

    Returns:
        JWT firmado como string.
    """
    now = _now_ts()
    ttl = int(expires_delta.total_seconds()) if expires_delta else ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload: Dict[str, Any] = {
        "iss": ISSUER,
        "jti": str(uuid.uuid4()),
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
    Decodifica y valida un access token JWT.

    Verifica firma, algoritmo, issuer, exp y nbf.
    No verifica audience (verify_aud=False).

    Args:
        token: JWT en formato string.

    Returns:
        Payload decodificado como dict.

    Raises:
        JWTError: Si la firma es inválida, el token expiró,
                  el issuer no coincide o el formato es incorrecto.
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
    Crea un refresh token JWT para el usuario indicado.

    El refresh token incluye typ='refresh' para distinguirlo del
    access token. Válido por REFRESH_TOKEN_EXPIRE_DAYS (default 7 días).

    Args:
        user_id: ID numérico del usuario. Se almacena en 'sub' como str.

    Returns:
        Tupla (token, jti, exp_ts):
          - token:  JWT firmado como string.
          - jti:    UUID del token (para blacklist al hacer logout).
          - exp_ts: Timestamp Unix de expiración (int).
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
    Decodifica y valida un refresh token JWT.

    Además de las validaciones estándar (firma, exp, issuer),
    verifica que el campo 'typ' sea 'refresh'. Rechaza access tokens
    u otros tipos presentados como refresh.

    Args:
        token: JWT en formato string.

    Returns:
        Payload decodificado como dict.

    Raises:
        JWTError: Si la firma es inválida, el token expiró,
                  o typ != 'refresh'.
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


# ---------------- Password reset tokens ----------------
def create_password_reset_token(user_id: int) -> Tuple[str, str, int]:
    """
    Crea un token JWT de un solo uso para restablecer contraseña.

    El token incluye typ='password_reset' y tiene TTL de 1 hora.
    Tras usarlo, el JTI debe añadirse a la blacklist para garantizar
    uso único (implementado en POST /auth/reset-password).

    Args:
        user_id: ID del usuario que solicitó el reset.

    Returns:
        Tupla (token, jti, exp_ts):
          - token:  JWT firmado como string.
          - jti:    UUID del token (para invalidarlo tras uso).
          - exp_ts: Timestamp Unix de expiración (int, now + 3600s).
    """
    jti = str(uuid.uuid4())
    now = _now_ts()
    exp_ts = now + 3600  # 1 hour
    payload = {
        "iss": ISSUER,
        "sub": str(user_id),
        "typ": "password_reset",
        "jti": jti,
        "iat": now,
        "nbf": now,
        "exp": exp_ts,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), jti, exp_ts


def decode_password_reset_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida un token de reset de contraseña.

    Reutiliza decode_access_token() para verificar firma/exp/issuer,
    y además verifica que typ == 'password_reset'. Rechaza access tokens
    o refresh tokens presentados como reset tokens.

    Args:
        token: JWT en formato string.

    Returns:
        Payload decodificado como dict.

    Raises:
        JWTError: Si la firma es inválida, el token expiró,
                  o typ != 'password_reset'.
    """
    payload = decode_access_token(token)
    if payload.get("typ") != "password_reset":
        raise JWTError("Invalid token type")
    return payload
