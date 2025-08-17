from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional 

# Board schemas
class BoardCreate(BaseModel):
    name: str
    description: str

class Board(BoardCreate):
    id: int
    
    class Config:
        from_attributes = True

# User schemas  
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    
    class Config:
        from_attributes = True

# Comment schemas - Define CommentBase first
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
    title: str | None = None
    body: str
    board_id: int
    comments: List[CommentBase] = []  # Changed from CommentCreate to CommentBase

class Post(BaseModel):
    id: int
    title: str
    body: str
    board_id: int
    created_at: date
    votes: int
    user_id: int
    comments: List[Comment] = []

    class Config:
        from_attributes = True

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
        from_attributes = True