"""
main.py — Punto de entrada raíz de KLKCHAN.

Monta las versiones de la API como sub-aplicaciones:
  /v1  → API actual (usuarios registrados, JWT, sistema completo)
  /v2  → API futura (anónimos, captcha) — en construcción

Uso local:
    uvicorn main:root --reload --port 8000

Documentación interactiva (desarrollo):
    /v1/docs  → Swagger UI de v1
    /v2/docs  → Swagger UI de v2
"""
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

# CORS en la app raíz (aplica a ambas versiones)
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
    _CORS_ORIGINS = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]

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
