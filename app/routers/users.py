from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from app.schemas import User, UserCreate, UserUpdate
from app.services import get_users, get_user, create_user, update_user, delete_user

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#  helper
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# GET all users
@router.get("/", response_model=list[User])
def read_users():
    return get_users()

# GET single user
@router.get("/{user_id}", response_model=User)
def read_user(user_id: int):
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="usuario no existe")
    return user

# CREATE user
@router.post("/", response_model=User)
def create_new_user(user: UserCreate):
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)  # 🔐 bcrypt
    new_user = create_user(user_dict)
    return new_user

# UPDATE user
@router.put("/{user_id}", response_model=User)
def update_existing_user(user_id: int, updates: UserUpdate):
    updates_dict = updates.dict(exclude_unset=True)  # solo campos enviados
    if "password" in updates_dict and updates_dict["password"] is not None:
        updates_dict["password"] = hash_password(updates_dict["password"])
    updated = update_user(user_id, updates_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="usuario no existe")
    return updated

# DELETE user
@router.delete("/{user_id}")
def delete_existing_user(user_id: int):
    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="usuario no existe")
    return {"status": "success", "message": f"Usuario {user_id} eliminado"}
