from fastapi import APIRouter, HTTPException
from typing import List
from passlib.context import CryptContext
from app.schemas import User, UserCreate, UserUpdate
from app.services import (
    get_users,
    get_user,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user,
    get_posts,
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)



@router.get("/get-users", response_model=List[User])
def get_users_list():
    return get_users()


@router.get("/get-user/", response_model=User)
def get_user_by_id(user_id: int):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    all_posts = get_posts()
    user["posts"] = [p["id"] for p in all_posts if p["user_id"] == user_id]
    return user


@router.post("/create-user", response_model=User)
def create_new_user(user: UserCreate):
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["posts"] = []
    return service_create_user(user_dict)


@router.put("/update-user/{user_id}", response_model=User)
def update_user(user_id: int, updates: UserUpdate):

    updates_dict = updates.dict(exclude_unset=True)

    if "password" in updates_dict and updates_dict["password"] is not None:
        updates_dict["password"] = hash_password(updates_dict["password"])

    updated = service_update_user(user_id, updates_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuario no existe")

    all_posts = get_posts()
    updated["posts"] = [p["id"] for p in all_posts if p["user_id"] == user_id]
    return updated


@router.delete("/delete-user/")
def delete_existing_user(user_id: int):
    success = service_delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no existe")
    return {"status": "success", "message": f"Usuario {user_id} eliminado"}
