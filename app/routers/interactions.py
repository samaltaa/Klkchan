# app/routers/interactions.py
from enum import Enum
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from app.deps import get_current_user

router = APIRouter(prefix="/interactions", tags=["Interactions"])

class TargetType(str, Enum):
    post = "post"
    comment = "comment"

class VoteRequest(BaseModel):
    target_type: TargetType
    target_id: int = Field(ge=1)
    value: int

    @field_validator("value")
    @classmethod
    def only_neg_or_pos(cls, v: int) -> int:
        if v not in (-1, 1):
            raise ValueError("Vote value must be -1 or +1")
        return v

@router.post("/votes", status_code=status.HTTP_202_ACCEPTED)
def cast_vote(payload: VoteRequest, current_user: dict = Depends(get_current_user)):
    """
    MODEL-13 (stub) — Acepta el payload, no persiste aún.
    """
    return {"accepted": True, "detail": "Vote stub accepted", "next": "MODEL-13"}
