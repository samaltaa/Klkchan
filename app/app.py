import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.utils.limiter import limiter

from app.routers import (
    admin,
    auth,
    boards,
    comments,
    interactions,
    moderation,
    posts,
    reports,
    users,
)
from app.services import load_data

APP_VERSION = "0.1.0"


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
    ],
)

# ---------------------------------------------------------------------------
# Rate limiting (SlowAPI)
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if _ENVIRONMENT == "development":
    _CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]
else:
    _CORS_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
