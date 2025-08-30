# app/app.py
from fastapi import FastAPI, HTTPException, Depends
from app.schemas import *
from app.routers import users
from app.routers import Auth
from app.deps import get_current_user
from datetime import date
import json
from pathlib import Path


"""
I have created relative file paths because what works on my 
machine might not work on yours, when creating docker images later
this will be the best practice since it keeps the folder 
structure consistent 
"""

BASE_DIR = Path(__file__).resolve().parent.parent  # defining parent directory

DATA_FILE = Path(__file__).resolve().parent / "data" / "data.json"  # pointing to the data file and directory
DATA_FILE.parent.mkdir(exist_ok=True)

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(Auth.router, prefix="/Auth", tags=["Auth"])


# function for getting the data from the json file
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    # fallback initial data if file not found
    return {"boards": [], "users": [], "posts": [], "comments": [], "replies": []}


# function for saving data in the json file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.on_event("startup")
async def startup():
    # Initialize JSON file if it doesn't exist
    if not DATA_FILE.exists():
        initial_data = {"boards": [], "users": [], "posts": [], "comments": [], "replies": []}
        save_data(initial_data)


@app.get("/health")
async def health():
    return {"status": "ok"}


"""
Tata's endpoints below
--------------------------------------------------------
"""


# endpoints related to boards
@app.get("/")
async def get_data():
    data = load_data()
    return data


@app.post("/postboard")
async def post_board(payload: BoardCreate):
    data = load_data()

    next_id = max([b["id"] for b in data["boards"]], default=0) + 1
    new_board = {
        "id": next_id,
        "name": payload.name,
        "description": payload.description,
    }
    data["boards"].append(new_board)

    save_data(data)
    return data


@app.get("/getboards")
async def get_boards():
    data = load_data()

    for board in data["boards"]:
        board_posts = [p for p in data["posts"] if p["board_id"] == board["id"]]
        board["posts"] = board_posts

    return {"boards": data["boards"]}


# endpoints for posts
@app.get("/getposts")
async def get_posts():
    data = load_data()

    for post in data["posts"]:
        post_comments = [c for c in data["comments"] if c["post_id"] == post["id"]]
        post["comments"] = post_comments

    return {"posts": data["posts"]}


@app.post("/posts", response_model=Post)
async def create_post(payload: PostCreate, current_user: dict = Depends(get_current_user)):
    """
    Crea un post con el user_id tomado del token (current_user).
    Mantiene la relación bidireccional user -> posts en data.json.
    """
    data = load_data()

    next_id = max([p["id"] for p in data["posts"]], default=0) + 1

    new_post = {
        "id": next_id,
        "title": payload.title,
        "body": payload.body,
        "board_id": payload.board_id,
        "created_at": str(date.today()),
        "votes": 0,
        "user_id": current_user["id"],  # ✅ sale del token
        "comments": [],
    }

    data["posts"].append(new_post)

    # ✅ mantener relación bidireccional: user -> posts
    for u in data["users"]:
        if u["id"] == current_user["id"]:
            u.setdefault("posts", [])
            u["posts"].append(next_id)
            break

    save_data(data)
    return new_post


# endpoints for comments
@app.post("/comments", response_model=Comment)
async def create_comment(payload: CommentCreate, current_user: dict = Depends(get_current_user)):
    """
    Crea un comentario con el user_id del token.
    Usa el post_id que llega en el payload (tu CommentCreate ya lo trae).
    """
    data = load_data()

    next_comment_id = max([c["id"] for c in data["comments"]], default=0) + 1
    new_comment = {
        "id": next_comment_id,
        "body": payload.body,
        "post_id": payload.post_id,  # ✅ del body
        "created_at": str(date.today()),
        "votes": 0,
        "user_id": current_user["id"],  # ✅ del token
    }
    data["comments"].append(new_comment)
    save_data(data)

    return new_comment


"""
TODO for Tata:
[] create a bidirectional relationship between comments and replies
"""
