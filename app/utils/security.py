# app/utils/security.py
import os
import re
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
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------- Password hashing --------
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

# -------- JWT helpers --------
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    

    # --- NUEVO: refresh ---
def create_refresh_token(user_id: int) -> Tuple[str, str, datetime]:
    """
    Retorna: (token, jti, exp)
    """
    jti = str(uuid.uuid4())
    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "jti": jti, "typ": "refresh", "exp": exp}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, exp

def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "refresh":
            return None
        return payload
    except JWTError:
        return None
