import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app_v1.utils.limiter import limiter

from app_v1.routers import (
    admin,
    auth,
    boards,
    comments,
    interactions,
    moderation,
    models_docs,
    posts,
    reports,
    terms,
    users,
)
from app_v1.services import load_data

APP_VERSION = "0.1.0"
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_dir = Path(__file__).resolve().parents[0] / "data" / "ldnoobw"
    for filename in ("es.txt", "en.txt"):
        if not (data_dir / filename).exists():
            logging.warning("LDNOOBW dictionary %s not found in %s", filename, data_dir)
    _ = load_data()
    yield


app = FastAPI(
    title="KLKCHAN API",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url=None if _ENVIRONMENT == "production" else "/docs",
    redoc_url=None if _ENVIRONMENT == "production" else "/redoc",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication and password flows."},
        {"name": "Users", "description": "User profiles and account management."},
        {"name": "Boards", "description": "Discussion boards (forums)."},
        {"name": "Posts", "description": "Threads and timeline entries."},
        {"name": "Comments", "description": "Threaded replies."},
        {"name": "System", "description": "Health checks and diagnostics."},
        {"name": "Admin", "description": "Administrative endpoints."},
        {"name": "Moderation", "description": "Moderation queue and actions."},
        {"name": "Interactions", "description": "Votes and social interactions."},
        {"name": "Terms", "description": "Términos y Condiciones del servicio."},
    ],
)

# ---------------------------------------------------------------------------
# Rate limiting (SlowAPI)
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(boards.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(admin.router)
app.include_router(moderation.router)
app.include_router(interactions.router)
app.include_router(reports.router)
app.include_router(terms.router)
app.include_router(models_docs.router)


@app.get("/health", tags=["System"])
async def health():
    try:
        load_data()
        db_status = "ok"
    except Exception as exc:  # pragma: no cover - defensive
        logging.exception("healthcheck: data load failed: %s", exc)
        db_status = "error"
    status_value = "ok" if db_status == "ok" else "degraded"
    return {
        "status": status_value,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": {"status": db_status},
        "cache": {"status": "unavailable"},
    }


@app.get("/", tags=["System"])
async def root_status():
    return {
        "service": "KLKCHAN API",
        "version": APP_VERSION,
        "docs": "/docs",
    }
