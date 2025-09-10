# app/app.py
from fastapi import FastAPI, Depends
from datetime import date

from app.schemas import BoardCreate, PostCreate, CommentCreate, Post, Comment
from app.deps import get_current_user
from app.routers import users, auth ,admin, moderation  
from app.services import load_data, save_data  


"""
I have created relative file paths because what works on my 
machine might not work on yours, when creating docker images later
this will be the best practice since it keeps the folder 
structure consistent 
"""

app = FastAPI(
    title="KLKCHAN API",
    openapi_tags=[
        {"name": "Auth",     "description": "Registro, login, cambio de contraseña."},
        {"name": "Users",    "description": "Gestión de usuarios."},
        {"name": "Boards",   "description": "Tableros / categorías."},
        {"name": "Posts",    "description": "Publicaciones."},
        {"name": "Comments", "description": "Comentarios."},
        {"name": "System",   "description": "Salud y utilidades del sistema."},
        {"name": "Admin",        "description": "Operaciones administrativas."},
        {"name": "Moderation",   "description": "Cola y acciones de moderación."},
    ],
)


# ⚠️ auth ya tiene prefix="/auth" dentro del router; users puede traer su prefix desde su archivo.
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(moderation.router)


@app.on_event("startup")
async def startup():
    """
    Fuerza la creación de app/data/data.json si no existe,
    usando la lógica robusta de services.
    """
    _ = load_data()


# ------------------- System -------------------
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}


@app.get("/", tags=["System"])
async def get_data():
    data = load_data()
    return data


"""
Tata's endpoints below
--------------------------------------------------------
"""

# ------------------- Boards -------------------
@app.post("/postboard", tags=["Boards"])
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


@app.get("/getboards", tags=["Boards"])
async def get_boards():
    data = load_data()

    for board in data["boards"]:
        board_posts = [p for p in data["posts"] if p["board_id"] == board["id"]]
        board["posts"] = board_posts

    return {"boards": data["boards"]}


# ------------------- Posts -------------------
@app.get("/getposts", tags=["Posts"])
async def get_posts():
    data = load_data()

    for post in data["posts"]:
        post_comments = [c for c in data["comments"] if c["post_id"] == post["id"]]
        post["comments"] = post_comments

    return {"posts": data["posts"]}


@app.post("/posts", response_model=Post, tags=["Posts"])
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


# ------------------- Comments -------------------
@app.post("/comments", response_model=Comment, tags=["Comments"])
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
