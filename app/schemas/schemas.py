from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class OrmBase(BaseModel):
    """Base model configured to work with ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    code: str = Field(..., description="Machine readable error identifier.")
    message: str = Field(..., description="Human readable error description.")
    details: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional contextual information that helps callers debug the issue.",
    )


class CursorPage(BaseModel):
    limit: int = Field(..., ge=1, le=100, description="Number of records requested.")
    next_cursor: Optional[int] = Field(
        default=None,
        description="Cursor to resume pagination in subsequent requests, when available.",
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    display_name: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=280)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=32)
    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(default=None, max_length=80)
    bio: Optional[str] = Field(default=None, max_length=280)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class User(OrmBase, UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    posts: List[int] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=lambda: ["user"])
    is_active: bool = True


class UserResponse(User):
    pass


class UserListResponse(CursorPage):
    items: List[User] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------
class BoardBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    description: Optional[str] = Field(default=None, max_length=280)


class BoardCreate(BoardBase):
    pass


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=64)
    description: Optional[str] = Field(default=None, max_length=280)


class Board(OrmBase, BoardBase):
    id: int
    slug: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    post_count: Optional[int] = Field(default=None, ge=0)


class BoardListResponse(CursorPage):
    items: List[Board] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tags and attachments (placeholders for future PRs)
# ---------------------------------------------------------------------------
class Tag(BaseModel):
    id: int
    name: str = Field(..., min_length=1, max_length=64)
    slug: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=280)


class Attachment(BaseModel):
    id: str
    url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Comments and replies
# ---------------------------------------------------------------------------
class CommentBase(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)


class CommentCreate(CommentBase):
    post_id: int = Field(..., ge=1)
    parent_id: Optional[int] = Field(default=None, ge=1)


class Comment(OrmBase, CommentBase):
    id: int
    post_id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    votes: int = 0
    parent_id: Optional[int] = None


class CommentListResponse(CursorPage):
    items: List[Comment] = Field(default_factory=list)


class Reply(OrmBase):
    id: int
    comment_id: int
    user_id: int
    body: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    votes: int = 0


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------
class PostBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    body: str = Field(..., min_length=1)
    board_id: int = Field(..., ge=1)
    tags: List[str] = Field(default_factory=list)


class PostCreate(PostBase):
    attachments: List[Attachment] = Field(default_factory=list)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=300)
    body: Optional[str] = Field(default=None, min_length=1)
    board_id: Optional[int] = Field(default=None, ge=1)
    tags: Optional[List[str]] = None


class Post(OrmBase, PostBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    votes: int = 0
    score: Optional[int] = None
    comment_count: Optional[int] = None
    attachments: List[Attachment] = Field(default_factory=list)
    comments: List[Comment] = Field(default_factory=list)


class PostListResponse(CursorPage):
    items: List[Post] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Votes, subscriptions, reports
# ---------------------------------------------------------------------------
class Vote(BaseModel):
    id: int
    target_type: str
    target_id: int
    user_id: int
    value: int = Field(..., ge=-1, le=1)
    created_at: datetime


class VoteSummary(BaseModel):
    target_type: str
    target_id: int
    score: int
    upvotes: int
    downvotes: int
    user_vote: Optional[int] = None


class UserForumSubscription(BaseModel):
    id: int
    user_id: int
    board_id: int
    created_at: datetime


class Report(BaseModel):
    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str = Field(..., min_length=3, max_length=500)
    status: str = Field(default="pending")
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    details: Optional[Dict[str, str]] = None


# ---------------------------------------------------------------------------
# Auth / Tokens
# ---------------------------------------------------------------------------
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., ge=1, description="Seconds until the access token expires.")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    jti: Optional[str] = None
    typ: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)


class LogoutResponse(BaseModel):
    detail: str = "Logged out"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    detail: str = "If the email exists, reset instructions were sent"


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Reset token delivered over email")
    new_password: str = Field(..., min_length=12, max_length=128)


class ResetPasswordResponse(BaseModel):
    detail: str = "Password updated"


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=4096, description="Verification token")

    @field_validator("token")
    @classmethod
    def token_must_not_contain_spaces(cls, value: str) -> str:
        if any(ch.isspace() for ch in value):
            raise ValueError("The token must not contain whitespace.")
        parts = value.split(".")
        if len(parts) not in (1, 3):
            raise ValueError("Unexpected token format.")
        return value


class ResendVerificationRequest(BaseModel):
    email: EmailStr


__all__ = [
    "Attachment",
    "Board",
    "BoardCreate",
    "BoardListResponse",
    "BoardUpdate",
    "ChangePasswordRequest",
    "Comment",
    "CommentBase",
    "CommentCreate",
    "CommentListResponse",
    "CursorPage",
    "ErrorResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "LogoutResponse",
    "OrmBase",
    "Post",
    "PostCreate",
    "PostListResponse",
    "PostUpdate",
    "Report",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "Reply",
    "Tag",
    "TokenPair",
    "TokenPayload",
    "RefreshTokenRequest",
    "User",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "UserForumSubscription",
    "VerifyEmailRequest",
    "Vote",
]
