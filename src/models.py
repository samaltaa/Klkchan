from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator

class statusType(str, Enum):
    Done = "Done"
    Pending = "Pending"

class myBaseModel(BaseModel):
    id: int = Field(ge=1, le=100)

class Test(BaseModel):
    id: int
    name: str
    user:str
    description: str
    status: statusType

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Test Name",
                "user": "test_user",
                "description": "test ejemplo para validar",
                "status": "Pending"
            }
        },
        "orm_mode": True
    }

    @field_validator('id')
    def greater_than_zero(cls, v):
        if v <= 0:
            raise ValueError('ID must be greater than zero')
        return v

    @field_validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if not v.replace(" ", "").isalnum():
            raise ValueError('Name must be alphanumeric')
        return v

class Users(myBaseModel):
    username: str = Field(..., min_length=3, max_length=15, pattern="^[a-zA-Z0-9_]+$")
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=25)
    password: str = Field(min_length=8, max_length=16)

class Comment(BaseModel):
    content: str = Field(min_length=2, max_length=500)
    post_id: int
    author_id: int

    @field_validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Comment cannot be empty')
        return v
