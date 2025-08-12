from pydantic import BaseModel, EmailStr
from datetime import date

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

# Post schemas
class PostCreate(BaseModel):
    title: str | None = None
    body: str
    board_id: int

class Post(PostCreate):
    id: int
    created_at: date
    votes: int
    user_id: int
    
    class Config:
        from_attributes = True

# Comment schemas
class CommentCreate(BaseModel):
    body: str
    post_id: int

class Comment(CommentCreate):
    id: int
    created_at: date
    votes: int
    user_id: int
    
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