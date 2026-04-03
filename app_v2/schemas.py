from typing import Optional, List
from pydantic import BaseModel, Field


class CaptchaVerifyRequest(BaseModel):
    hcaptcha_token: str

class GuestTokenResponse(BaseModel):
    guest_token: str
    expires_in: int
    token_type: str = "bearer"

class BoardV2(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    post_count: int = 0

class BoardListResponseV2(BaseModel):
    items: List[BoardV2]
    total: int

class PostCreateV2(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1, max_length=10000)
    board_id: int
    image: Optional[str] = None

class PostResponseV2(BaseModel):
    id: int
    title: str
    body: str
    board_id: int
    created_at: str
    votes: int = 0
    image: Optional[str] = None
    anon_id: Optional[str] = None
    comment_count: int = 0

class PostListResponseV2(BaseModel):
    items: List[PostResponseV2]
    total: int
    next_cursor: Optional[int] = None

class CommentCreateV2(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)
    post_id: int
    parent_comment_id: Optional[int] = None

class CommentResponseV2(BaseModel):
    id: int
    body: str
    post_id: int
    parent_comment_id: Optional[int] = None
    created_at: str
    votes: int = 0
    anon_id: Optional[str] = None
    replies: List["CommentResponseV2"] = []

CommentResponseV2.model_rebuild()
