# app/schemas.py
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

# Base para modelos que reciben datos desde objetos/ORM
class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# ─────────────────────────────────────────────────────────
# Users
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=24)

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class User(OrmBase):
    id: int
    username: str
    email: EmailStr
    posts: List[int] = Field(default_factory=list)

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
    # El user_id lo inyecta el endpoint desde el token; dejarlo opcional evita 422
    user_id: Optional[int] = None
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
# Password reset
class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)

class LogoutResponse(BaseModel):
    detail: str = "Logged out"

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    detail: str = "Si el correo existe, reset instrucciones enviadas"

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Token de reseteo recibido por email")
    new_password: str = Field(..., min_length=12, max_length=128)

class ResetPasswordResponse(BaseModel):
    detail: str = "Password updated"

# ─────────────────────────────────────────────────────────
# Email verification (MODEL-32)
class VerifyEmailRequest(BaseModel):
    """
    Token de verificación enviado por email (ej. JWT).
    """
    token: str = Field(..., min_length=16, max_length=4096, description="Token de verificación (ej. JWT)")
    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("token")
    @classmethod
    def no_spaces_and_basic_shape(cls, v: str) -> str:
        if any(ch.isspace() for ch in v):
            raise ValueError("El token no debe contener espacios.")
        parts = v.split(".")
        # Permitimos token simple o estilo JWT (3 segmentos)
        if len(parts) not in (1, 3):
            raise ValueError("Formato de token inválido.")
        return v

class ResendVerificationRequest(BaseModel):
    """
    Solicitud de reenvío de verificación.
    """
    email: EmailStr
