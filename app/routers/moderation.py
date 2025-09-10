from fastapi import APIRouter, Depends
from app.deps import require_role
from app.utils.roles import Role

router = APIRouter(prefix="/moderation", tags=["Moderation"])

@router.get("/queue", dependencies=[Depends(require_role(Role.mod, Role.admin))])
def moderation_queue():
    # TODO: traer reportes/pendientes
    return {"items": []}

@router.post("/actions", dependencies=[Depends(require_role(Role.mod, Role.admin))])
def moderation_actions(
    payload: dict  # puedes moverlo a schemas si prefieres
):
    """
    Esperado (ejemplo):
    {
      "target_type": "post|comment|user",
      "target_id": 123,
      "action": "remove|approve|lock|sticky|ban_user|shadowban",
      "reason": "opcional"
    }
    """
    # TODO: aplicar acción
    return {"applied": True}
