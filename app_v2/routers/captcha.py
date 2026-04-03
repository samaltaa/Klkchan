from fastapi import APIRouter, HTTPException, Response
from app_v2.schemas import CaptchaVerifyRequest, GuestTokenResponse
from app_v2.security import verify_hcaptcha, create_guest_token, GUEST_TOKEN_EXPIRE_SECONDS

router = APIRouter(prefix="/captcha", tags=["Captcha"])

@router.post("/verify", response_model=GuestTokenResponse)
async def verify_captcha(body: CaptchaVerifyRequest, response: Response):
    if not await verify_hcaptcha(body.hcaptcha_token):
        raise HTTPException(status_code=400, detail="Captcha inválido")
    token = create_guest_token()
    response.set_cookie(key="guest_token", value=token, httponly=True, secure=False, samesite="lax", max_age=GUEST_TOKEN_EXPIRE_SECONDS)
    return GuestTokenResponse(guest_token=token, expires_in=GUEST_TOKEN_EXPIRE_SECONDS)
