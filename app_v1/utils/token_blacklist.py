"""
token_blacklist.py — Blacklist de tokens revocados — KLKCHAN.

Almacena en memoria los JTIs (JWT ID) de tokens revocados. Se utiliza
para invalidar tokens activos en los flujos de:
  - POST /auth/logout         → revoca access token (y opcionalmente refresh)
  - POST /auth/change-password → revoca el token activo del usuario
  - POST /auth/reset-password  → revoca tokens de reset usados
  - DELETE /users/me           → revoca el access token del usuario eliminado

Limitaciones:
  - Storage in-process: se borra al reiniciar el servidor.
  - No distribuido: en un deployment multi-proceso cada proceso
    tiene su propia blacklist.
  - Pendiente de migrar a Redis o Supabase en Sprint 3.

Los tokens expirados se eliminan automáticamente (eviction lazy)
para evitar crecimiento ilimitado del diccionario.
"""
from __future__ import annotations

import threading
import time
from typing import Dict

_lock = threading.Lock()
_store: Dict[str, float] = {}  # jti -> exp (unix timestamp)


def revoke(jti: str, exp: float) -> None:
    """
    Añade un JTI a la blacklist hasta su expiración natural.

    Thread-safe. Llama a _evict() internamente para limpiar
    entradas expiradas antes de insertar.

    Args:
        jti: JWT ID único del token a revocar.
        exp: Timestamp Unix (float) de expiración del token.
             Cuando el tiempo actual supere este valor, la entrada
             será eliminada automáticamente por _evict().
    """
    with _lock:
        _store[jti] = float(exp)
        _evict()


def is_revoked(jti: str) -> bool:
    """
    Retorna True si el JTI está en la blacklist y aún no ha expirado.

    Thread-safe. Llama a _evict() antes de la consulta para no
    reportar como revocados tokens que ya expiraron naturalmente.

    Args:
        jti: JWT ID a verificar.

    Returns:
        True si el token está revocado y vigente, False en caso contrario.
    """
    with _lock:
        _evict()
        return jti in _store


def _evict() -> None:
    """
    Elimina del store las entradas cuya expiración ya pasó.

    Debe llamarse siempre dentro del contexto de _lock.
    Evita que el diccionario crezca indefinidamente con tokens
    que ya expiraron y no representan ningún riesgo.
    """
    now = time.time()
    expired = [jti for jti, exp in _store.items() if exp <= now]
    for jti in expired:
        del _store[jti]
