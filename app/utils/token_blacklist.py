"""
In-memory token blacklist (per-process, cleared on restart).
Stores revoked JTI values with their expiry timestamps so expired
entries are automatically pruned without growing unboundedly.
"""
from __future__ import annotations

import threading
import time
from typing import Dict

_lock = threading.Lock()
_store: Dict[str, float] = {}  # jti -> exp (unix timestamp)


def revoke(jti: str, exp: float) -> None:
    """Add a JTI to the blacklist until its natural expiry."""
    with _lock:
        _store[jti] = float(exp)
        _evict()


def is_revoked(jti: str) -> bool:
    """Return True if the JTI is blacklisted and not yet expired."""
    with _lock:
        _evict()
        return jti in _store


def _evict() -> None:
    """Remove entries whose expiry has already passed (call under _lock)."""
    now = time.time()
    expired = [jti for jti, exp in _store.items() if exp <= now]
    for jti in expired:
        del _store[jti]
