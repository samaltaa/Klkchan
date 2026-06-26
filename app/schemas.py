from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional


# User schemas
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

    class Config:
        from_attributes = True


# Board schemas
class BoardCreate(BaseModel):
    name: str
    description: str

class Board(BoardCreate):
    id: int

    class Config:
        from_attributes = True


# Comment schemas
class CommentBase(BaseModel):
    body: str

class CommentCreate(CommentBase):
    post_id: int

class Comment(CommentBase):
    id: int
    created_at: date
    votes: int
    user_id: Optional[int] = None   # None = anonymous
    post_id: int
    image_url: Optional[str] = None
    replies: List["Reply"] = []

    class Config:
        from_attributes = True


# Post schemas
class PostCreate(BaseModel):
    title: str
    body: str
    board_id: int
    user_id: Optional[int] = None   # None = anonymous

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
    user_id: Optional[int] = None
    image_url: Optional[str] = None
    comments: List[Comment] = []

    class Config:
        from_attributes = True


# Reply schemas
class ReplyCreate(BaseModel):
    body: str
    comment_id: int

class Reply(BaseModel):
    id: int
    body: str
    comment_id: int
    created_at: date
    votes: int
    user_id: Optional[int] = None   # None = anonymous
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


# Required for forward reference in Comment.replies
Comment.model_rebuild()