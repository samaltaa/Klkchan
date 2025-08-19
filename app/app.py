from fastapi import FastAPI, HTTPException
from app.schemas import *
from app.routers import users
import json
from pathlib import Path

"""
I have created relative file paths because what works on my 
machine might not work on yours, when creating docker images later
this will be the best practice since it keeps the folder 
structure consistent 
"""

BASE_DIR = Path(__file__).resolve().parent.parent #defining parent directory 

DATA_FILE = Path(__file__).resolve().parent / "data" / "data.json" #pointing to the data file and directory 
DATA_FILE.parent.mkdir(exist_ok=True)

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["Users"])


#function for getting the data from the json file 
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
        return {"boards":[], "users": [], "posts": [], "comments": [], "replies": []}

#function for saving data in the json file
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.on_event("startup")
async def startup():
    # Initialize JSON file if it doesn't exist
    if not DATA_FILE.exists():
        initial_data = {"boards":[], "users": [], "posts": [], "comments": [], "replies": []}
        save_data(initial_data)

@app.get("/health")
async def health():
    return {"status": "ok"}

"""


FOR SAMIRA:

# - Implementé servicios CRUD para Users y Posts.
# - En create_post() actualizo automáticamente la lista de posts del usuario (relación bidireccional).
# - En delete_post() limpio la relación en los usuarios.
# - Todos los cambios persisten en data.json.
# - Todos los endpoints de Users listos (CRUD).
# - Implementé bcrypt para hashear contraseñas al crear usuario.
# - También en UPDATE: si el password cambia, vuelve a guardarse hasheado.
# - Los responses no exponen la contraseña (solo datos públicos)


FOR MELVIN:
Hey twin :~), make sure your endpoints are defined 
below this line and above the green dashes below so we 
all know who worked on what. I understand my coding style 
is a bit rudimentary but that's because this is a prototype 
I am keeping my code and yours divided by borders so that
we can discuss integrating our code blocks over a google meet. So far I only have post 
and get endpoints but thats because I had to start from scratch again after an oversight.

Your tasks:
[]create endpoints for creating, editing, deleting, and fetching users
[]for user account creation use passlib.context and 
import CryptContext to use bcrypt to hash passwords before they are stored
[]create a biderectional relationship between users and the posts
each post already has a "user_id" field

--Tata
"""



"""
Tata's endpoints below
--------------------------------------------------------
"""

#endpoints related to boards
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

#endpoints for posts  
@app.get("/getposts")
async def get_posts():
    data = load_data()

    for post in data["posts"]:
        post_comments = [c for c in data["comments"] if c["post_id"] == post["id"]]
        post["comments"] = post_comments

    return {"posts": data["posts"]}

@app.post("/posts", response_model=Post)
async def create_post(payload: PostCreate):
    data = load_data()

    next_id = max([p["id"] for p in data["posts"]], default=0) + 1

    new_post = {
        "id": next_id,
        "title": payload.title,
        "body": payload.body,
        "board_id": 2, #logic will be added later
        "created_at": str(date.today()),
        "votes": 0,
        "user_id": 1, #place holder
        "comments":[]
    }

    data["posts"].append(new_post)

    
    save_data(data)
    return new_post

#endpoints for comments 
@app.post("/comments", response_model=Comment)
async def create_comment(payload: CommentCreate):
    data = load_data()

    next_comment_id = max([c["id"] for c in data["comments"]], default=0) + 1
    new_comment = {
            "id": next_comment_id,
            "body": payload.body,
            "post_id": 1, #placeholder
            "created_at": str(date.today()),
            "votes": 0,
            "user_id": 1
            }
    data["comments"].append(new_comment)
    save_data(data)

    return new_comment

"""
TODO for Tata:
[]create a bidirectional relationship between comments and replies
"""
