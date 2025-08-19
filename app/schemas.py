from pydantic import BaseModel, EmailStr
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
    posts: List[int] = []   # IDs de los posts que le pertenecen

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
    title: str
    body: str
    board_id: int
    user_id: int 
    comments: List[CommentBase] = []  # Changed from CommentCreate to CommentBase

    
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
    comments: List[Comment] = []


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