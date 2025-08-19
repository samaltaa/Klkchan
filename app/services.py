from app.schemas import User, UserCreate, UserUpdate, Post, PostCreate, PostUpdate
import json
from pathlib import Path
from datetime import date

DATA_PATH = Path("app/data/data.json")

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# USERS SERVICES
def get_users():
    data = load_data()
    return data["users"]

def get_user(user_id: int):
    data = load_data()
    for u in data["users"]:
        if u["id"] == user_id:
            return u
    return None

def create_user(user: dict):
    data = load_data()
    user["id"] = len(data["users"]) + 1
    user["posts"] = []  # importante
    data["users"].append(user)
    save_data(data)
    return user

def update_user(user_id: int, updates: dict):
    data = load_data()
    for u in data["users"]:
        if u["id"] == user_id:
            u.update({k: v for k, v in updates.items() if v is not None})
            save_data(data)
            return u
    return None

def delete_user(user_id: int):
    data = load_data()
    data["users"] = [u for u in data["users"] if u["id"] != user_id]
    save_data(data)
    return True

# POSTS SERVICES
def get_posts():
    data = load_data()
    return data["posts"]

def get_post(post_id: int):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            return p
    return None

def create_post(post: dict):
    data = load_data()
    post["id"] = len(data["posts"]) + 1
    post["created_at"] = str(date.today())
    post["votes"] = 0
    post["comments"] = []

    data["posts"].append(post)

    # 🚀 aquí actualizamos al usuario con el nuevo post
    for u in data["users"]:
        if u["id"] == post["user_id"]:
            u["posts"].append(post["id"])

    save_data(data)
    return post

def update_post(post_id: int, updates: dict):
    data = load_data()
    for p in data["posts"]:
        if p["id"] == post_id:
            p.update({k: v for k, v in updates.items() if v is not None})
            save_data(data)
            return p
    return None

def delete_post(post_id: int):
    data = load_data()
    data["posts"] = [p for p in data["posts"] if p["id"] != post_id]

    # 🚀 limpiar relación en los usuarios
    for u in data["users"]:
        if post_id in u["posts"]:
            u["posts"].remove(post_id)

    save_data(data)
    return True
