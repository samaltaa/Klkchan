"""
main.py — Punto de entrada raiz de KLKCHAN.

Monta las versiones de la API como sub-aplicaciones:
  /v1  -> API actual (usuarios registrados, JWT, sistema completo)
  /v2  -> API futura (anonimos, captcha) -- en construccion

Uso local:
    uvicorn main:root --reload --port 8000

Documentacion interactiva (desarrollo):
    /v1/docs  -> Swagger UI de v1
    /v2/docs  -> Swagger UI de v2
"""
# load_dotenv MUST run before any app_v1/app_v2 import.
# app_v1.utils.security reads SECRET_KEY at module level; if the .env is not
# loaded first, uvicorn aborts with "ValueError: SECRET_KEY ... is required".
# Using an absolute path relative to this file makes startup independent of
# the working directory from which uvicorn is invoked.
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app_v1.app import app as v1_app
from app_v2.app import app as v2_app

_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

root = FastAPI(
    title="KLKCHAN",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS on root covers the /health endpoint.
# Sub-apps (/v1, /v2) carry their own CORSMiddleware — Starlette mount()
# isolates middleware stacks, so this root config does not reach /v1/* or /v2/*.
_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]
_FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")   # production Vercel domain
if _FRONTEND_ORIGIN:
    _CORS_ORIGINS.append(_FRONTEND_ORIGIN)

root.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root.mount("/v1", v1_app)
root.mount("/v2", v2_app)


@root.get("/health", tags=["System"])
async def root_health():
    return {"status": "ok", "versions": ["v1", "v2"]}
