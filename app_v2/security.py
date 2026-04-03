import os, hashlib, httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Cookie, HTTPException, status

GUEST_SECRET = os.getenv("GUEST_SECRET_KEY", "klkchan-v2-dev-secret")
ALGORITHM = "HS256"
GUEST_TOKEN_EXPIRE_SECONDS = 3600
HCAPTCHA_SECRET = os.getenv("HCAPTCHA_SECRET_KEY", "0x0000000000000000000000000000000000000000")
HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"

async def verify_hcaptcha(token: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(HCAPTCHA_VERIFY_URL, data={"secret": HCAPTCHA_SECRET, "response": token}, timeout=5.0)
            return r.json().get("success", False)
        except Exception:
            return False

def create_guest_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": "guest", "type": "guest", "iat": now, "exp": now + timedelta(seconds=GUEST_TOKEN_EXPIRE_SECONDS)}
    return jwt.encode(payload, GUEST_SECRET, algorithm=ALGORITHM)

def decode_guest_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, GUEST_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "guest":
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Guest token inválido o expirado — completa el captcha")

def derive_anon_id(payload: dict) -> str:
    raw = f"{payload.get('iat')}-{payload.get('exp')}-{GUEST_SECRET}"
    return "Anon-" + hashlib.sha256(raw.encode()).hexdigest()[:4]

def require_guest_token(guest_token: Optional[str] = Cookie(default=None)) -> dict:
    if not guest_token:
        raise HTTPException(status_code=401, detail="Completa el captcha primero")
    return decode_guest_token(guest_token)
