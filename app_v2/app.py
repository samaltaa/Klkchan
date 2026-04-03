import os
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app_v1.utils.limiter import limiter
from app_v2.routers import captcha, boards, posts, comments

app = FastAPI(
    title="KLKCHAN API v2",
    version="2.0.0-alpha",
    description="API v2 — anónimos + captcha. Site key de prueba: 10000000-ffff-ffff-ffff-000000000001",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(captcha.router)
app.include_router(boards.router)
app.include_router(posts.router)
app.include_router(comments.router)

@app.get("/health", tags=["System"])
async def health_v2():
    return {"status": "ok", "version": "2.0.0-alpha", "auth": "hcaptcha + guest token cookie"}
