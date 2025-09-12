# app/routers/users.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.schemas import User, UserCreate, UserUpdate
from app.deps import get_current_user
from fastapi import Security
from app.deps import oauth2_scheme

from app.services import (
    get_users,
    get_user,
    create_user as service_create_user,
    update_user as service_update_user,
    delete_user as service_delete_user,
    get_posts,
)
from app.utils.security import hash_password
from app.utils.banned_words import has_banned_words  # ← añadido

router = APIRouter(prefix="/users", tags=["Users"])

# Helper local (evita imports cruzados)
def enforce_clean_text(*texts: str, lang: str = "es") -> None:
    for text in texts:
        if text and has_banned_words(text, lang_hint=lang):
            raise HTTPException(status_code=400, detail="Texto con palabras no permitidas.")


@router.get("/me", response_model=User)
def read_me(token: str = Security(oauth2_scheme), current_user: dict = Depends(get_current_user)):
    return current_user

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

    # Moderación en campos de texto (si existen en tu esquema)
    enforce_clean_text(
        user_dict.get("username"),
        user_dict.get("display_name"),
        user_dict.get("bio"),
    )

    user_dict["password"] = hash_password(user.password)
    user_dict["posts"] = []
    return service_create_user(user_dict)

@router.put("/update-user/{user_id}", response_model=User)
def update_user(user_id: int, updates: UserUpdate):
    updates_dict = updates.dict(exclude_unset=True)

    # Moderación solo en campos presentes en el payload
    enforce_clean_text(
        updates_dict.get("username"),
        updates_dict.get("display_name"),
        updates_dict.get("bio"),
    )

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
