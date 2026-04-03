# app/routers/reports.py
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app_v1.deps import get_current_user, require_role
from app_v1.services import moderation_queue_list, moderation_report_create
from app_v1.utils.roles import Role

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
    report = moderation_report_create(
        reporter_id=current_user["id"],
        target_type=payload.target_type.value,
        target_id=payload.target_id,
        reason=payload.reason,
    )
    return {"accepted": True, "id": report["id"]}


@router.get("/reports", dependencies=[Depends(require_role(Role.mod, Role.admin))])
def list_reports(
    filter_status: Optional[str] = Query(default=None, alias="status"),
):
    items = moderation_queue_list(status=filter_status)
    return {"items": items}
