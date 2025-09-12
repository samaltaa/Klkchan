# app/routers/reports.py
from enum import Enum
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from app.deps import get_current_user, require_role
from app.utils.roles import Role

router = APIRouter(prefix="/moderation", tags=["Moderation"])

class ReportTarget(str, Enum):
    user = "user"
    post = "post"
    comment = "comment"

class ReportCreate(BaseModel):
    target_type: ReportTarget
    target_id: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=280)
    extra: Optional[str] = Field(default=None, max_length=500)

@router.post("/reports", status_code=status.HTTP_202_ACCEPTED)
def create_report(payload: ReportCreate, current_user: dict = Depends(get_current_user)):
    """
    MODEL-30 (stub) — Cola de reports real pendiente.
    """
    return {"accepted": True, "detail": "Report stub queued", "next": "MODEL-30"}

@router.get("/reports", dependencies=[Depends(require_role(Role.mod, Role.admin))])
def list_reports():
    """
    MODEL-30 (stub) — Listado vacío por ahora.
    """
    return {"items": [], "detail": "Reports stub list", "next": "MODEL-30"}
