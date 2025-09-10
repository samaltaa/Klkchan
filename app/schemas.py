# app/schemas.py
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Base para modelos que reciben datos desde objetos/ORM
class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# ─────────────────────────────────────────────────────────
# Users
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class User(OrmBase):
    id: int
    username: str
    email: EmailStr
    posts: List[int] = Field(default_factory=list)

# Respuesta pública (similar a User, pero explícita)
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    posts: List[int] = Field(default_factory=list)

# ─────────────────────────────────────────────────────────
# Boards
class BoardCreate(BaseModel):
    name: str
    description: str

class Board(OrmBase, BoardCreate):
    id: int

# ─────────────────────────────────────────────────────────
# Comments
class CommentBase(BaseModel):
    body: str

class CommentCreate(CommentBase):
    post_id: int

class Comment(OrmBase, CommentBase):
    id: int
    created_at: date
    votes: int
    user_id: int
    post_id: int

# ─────────────────────────────────────────────────────────
# Posts
class PostCreate(BaseModel):
    title: str
    body: str
    board_id: int
    user_id: int
    comments: List[CommentBase] = Field(default_factory=list)

class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    board_id: Optional[int] = None

class Post(OrmBase):
    id: int
    title: str
    body: str
    board_id: int
    created_at: date
    votes: int
    user_id: int
    comments: List[Comment] = Field(default_factory=list)

# ─────────────────────────────────────────────────────────
# Replies
class ReplyCreate(BaseModel):
    body: str
    comment_id: int

class Reply(OrmBase, ReplyCreate):
    id: int
    created_at: date
    votes: int
    user_id: int

# ─────────────────────────────────────────────────────────
# Auth / Tokens
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

# ─────────────────────────────────────────────────────────
# Password flows
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)  # o 12 si subes política

# Logout
class LogoutResponse(BaseModel):
    detail: str = "Logged out"

# Forgot password
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    detail: str = "If the email exists, reset instructions were sent"

# Reset password
class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Token de reseteo recibido por email")
    new_password: str = Field(..., min_length=12, max_length=128)

class ResetPasswordResponse(BaseModel):
    detail: str = "Password updated"
