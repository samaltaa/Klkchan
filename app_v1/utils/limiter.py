"""
limiter.py — Configuración de rate limiting — KLKCHAN.

Instancia compartida de SlowAPI para limitar requests por IP.
Se mantiene en módulo propio para evitar imports circulares
entre app.py y los routers.

Límites configurados en los endpoints (vía @limiter.limit):
  - Auth endpoints (login, register): 5/minute
  - Escritura (POST/PUT/PATCH/DELETE): 30/minute
  - Lectura (GET): 60/minute (default global)

El rate limiting se deshabilita en tests asignando
limiter.enabled = False en conftest.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
)
