# tests/test_cors.py
"""
CORS preflight tests for app_v1 and app_v2.

Verifies that CORSMiddleware is correctly mounted on each sub-app so that
OPTIONS preflight requests from allowed origins receive the required headers,
and requests from disallowed origins do not.

Background: Starlette mount() isolates each sub-app's middleware stack.
Root-level add_middleware does not propagate to mounted apps, so each sub-app
must carry its own CORSMiddleware.
"""
import pytest
from fastapi.testclient import TestClient

from app_v1.app import app as v1_app
from app_v2.app import app as v2_app


@pytest.fixture(scope="module")
def v1_client():
    with TestClient(v1_app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="module")
def v2_client():
    with TestClient(v2_app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# v1 CORS preflight
# ---------------------------------------------------------------------------

def test_cors_preflight_allowed_origin_v1(v1_client, temp_data_path):
    """OPTIONS /posts desde origen permitido retorna CORS headers correctos."""
    r = v1_client.options(
        "/posts",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    # CORSMiddleware returns 200 for a valid preflight
    assert r.status_code == 200, f"expected 200 preflight, got {r.status_code}: {r.text}"
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    # allow-headers must cover authorization (needed for Bearer token)
    ach = r.headers.get("access-control-allow-headers", "")
    assert ach == "*" or "authorization" in ach.lower(), (
        f"access-control-allow-headers missing 'authorization': {ach!r}"
    )


def test_cors_preflight_rejected_origin_v1(v1_client, temp_data_path):
    """OPTIONS /posts desde origen no permitido NO obtiene access-control-allow-origin."""
    r = v1_client.options(
        "/posts",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    # The response must not grant CORS to the untrusted origin
    acao = r.headers.get("access-control-allow-origin", "")
    assert acao != "http://evil.com", (
        "Evil origin must not appear in access-control-allow-origin"
    )


# ---------------------------------------------------------------------------
# v2 CORS preflight
# ---------------------------------------------------------------------------

def test_cors_preflight_allowed_origin_v2(v2_client, temp_data_path):
    """OPTIONS /posts en v2 desde origen permitido retorna CORS headers correctos."""
    r = v2_client.options(
        "/posts",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200, f"v2 preflight failed: {r.status_code}: {r.text}"
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
