from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator

from app.deps import get_current_user
from app.schemas import ErrorResponse, VoteSummary
from app.services import apply_vote, get_vote_summary

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
    def only_allowed_values(cls, value: int) -> int:
        if value not in (-1, 0, 1):
            raise ValueError("Vote value must be -1, 0, or 1")
        return value


@router.post(
    "/votes",
    response_model=VoteSummary,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
def cast_vote(
    payload: VoteRequest,
    current_user: dict = Depends(get_current_user),
) -> VoteSummary:
    try:
        result = apply_vote(
            user_id=current_user["id"],
            target_type=payload.target_type.value,
            target_id=payload.target_id,
            value=payload.value,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "target_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    result["user_vote"] = result.pop("value")
    return VoteSummary(**result)


@router.get(
    "/votes/{target_type}/{target_id}",
    response_model=VoteSummary,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def read_vote_summary(target_type: TargetType, target_id: int = Path(..., ge=1)) -> VoteSummary:
    summary = get_vote_summary(target_type.value, target_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return VoteSummary(**summary)
