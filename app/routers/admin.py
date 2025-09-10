from fastapi import APIRouter, Depends
from app.deps import require_role
from app.utils.roles import Role  # o app.security.roles si lo tienes ahí

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", dependencies=[Depends(require_role(Role.admin))])
def list_users_admin():
    # TODO: filtrar/paginar desde tu storage/DB
    return {"items": [], "total": 0}

@router.get("/stats", dependencies=[Depends(require_role(Role.admin))])
def admin_stats():
    # TODO: métricas de la plataforma
    return {"users": 0, "posts": 0, "comments": 0}
