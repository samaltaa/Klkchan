from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import List, Optional

# User Schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    posts: List[int] = Field(default_factory=list)  # ✅ evitar mutable default

    class Config:
        from_attributes = True

# Board schemas
class BoardCreate(BaseModel):
    name: str
    description: str

class Board(BoardCreate):
    id: int

    class Config:
        from_attributes = True  # ✅ deja solo uno

# Comment schemas
class CommentBase(BaseModel):
    body: str

class CommentCreate(CommentBase):
    post_id: int

class Comment(CommentBase):
    id: int
    created_at: date
    votes: int
    user_id: int
    post_id: int

    class Config:
        from_attributes = True

# Post schemas
class PostCreate(BaseModel):
    title: str
    body: str
    board_id: int
    user_id: int
    comments: List[CommentBase] = Field(default_factory=list)  # ✅

class PostUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    board_id: Optional[int] = None

class Post(BaseModel):
    id: int
    title: str
    body: str
    board_id: int
    created_at: date
    votes: int
    user_id: int
    comments: List[Comment] = Field(default_factory=list)  # ✅

# Reply schemas
class ReplyCreate(BaseModel):
    body: str
    comment_id: int

class Reply(ReplyCreate):
    id: int
    created_at: date
    votes: int
    user_id: int

    class Config:
        from_attributes = True  # ✅ vuelve a ponerlo

# Auth schemas  ✅ nuevos
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    posts: List[int] = Field(default_factory=list)

    class Config:
        from_attributes = True
