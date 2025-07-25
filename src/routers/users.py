from fastapi import APIRouter, HTTPException,Body
from ..schemas import User, UserCreate

users: list[User] = []

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.get("/", response_model=list[User])
def read_users():
    return users

@users_router.post("/", response_model=User, status_code=201)
def create_user(user: UserCreate):
    new_id = len(users) + 1
    new_user = User(id=new_id, **user.dict())
    users.append(new_user)
    return new_user

@users_router.get("/{user_id}", response_model=User)
def get_user(user_id: int):
    for u in users:
        if u.id == user_id:
            return u
    raise HTTPException(404, "Usuario no encontrado")

@users_router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user: UserCreate):
    for idx, u in enumerate(users):
        if u.id == user_id:
            updated = User(id=user_id, **user.dict())
            users[idx] = updated
            return updated
    raise HTTPException(404, "Usuario no encontrado")

@users_router.delete("/{user_id}", response_model=User)
def delete_user(user_id: int):
    for idx, u in enumerate(users):
        if u.id == user_id:
            return users.pop(idx)
    raise HTTPException(404, "Usuario no encontrado")
